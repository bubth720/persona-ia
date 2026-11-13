extends Node3D
## PERSONA LIVE — scène interactive : décor, personnage contrôlable, caméra, interaction, import, capture, réglages.

const SETTINGS_PATH := "user://persona_live.cfg"
const LOCK_PATH := "user://persona_live.lock"

var decor_root := Node3D.new()
var player := PersonaPlayer.new()
var cam := PersonaCameraRig.new()
var hud := CanvasLayer.new()
var info_label := Label.new()
var status_label := Label.new()
var help_label := Label.new()
var file_dialog: FileDialog
var settings := ConfigFile.new()
var hw := {}
var profile := "standard"
var decor_index := 0
var decor := {}
var character := {}
var _status_t := 0.0


func _ready() -> void:
	PersonaInput.register()
	settings.load(SETTINGS_PATH)
	_write_lock()
	hw = PersonaHardware.detect()
	profile = str(settings.get_value("video", "profile", hw["profile"]))
	decor_index = int(settings.get_value("scene", "decor", 0))
	add_child(decor_root)
	add_child(player)
	add_child(cam)
	cam.target = player
	cam.sensitivity = float(settings.get_value("controls", "mouse_sensitivity", 0.006))
	_build_hud()
	load_decor(decor_index)
	var last := str(settings.get_value("character", "last", ""))
	if last != "" and not load_character_path(last):
		load_demo()
	elif last == "":
		load_demo()
	if OS.get_cmdline_user_args().has("--selftest"):
		var t := preload("res://scripts/selftest.gd").new()
		t.name = "SelfTest"
		add_child(t)


# ---------------------------------------------------------------- décors / personnages
func load_decor(i: int) -> void:
	decor_index = i % PersonaDecors.count()
	decor = PersonaDecors.build(decor_index, decor_root, profile)
	player.global_position = decor["spawn"]
	player.velocity = Vector3.ZERO
	PersonaHardware.apply(profile, get_viewport(), decor.get("light"))
	settings.set_value("scene", "decor", decor_index)
	show_status("Décor : %s (%d/%d)" % [decor["name"], decor_index + 1, PersonaDecors.count()])


func load_demo() -> void:
	_use_character(PersonaCharacterLoader.load_demo(), "")


## Accepte un fichier .glb/.gltf ou un dossier PERSONA (contenant persona_character.json).
func load_character_path(path: String) -> bool:
	var res: Dictionary
	if DirAccess.dir_exists_absolute(path) or path.get_file() == "persona_character.json":
		res = PersonaCharacterLoader.load_persona_folder(path if DirAccess.dir_exists_absolute(path) else path.get_base_dir())
	else:
		res = PersonaCharacterLoader.load_gltf(path)
	if res.has("error"):
		show_status("Import impossible : " + str(res["error"]))
		return false
	_use_character(res, path)
	return true


func _use_character(res: Dictionary, path: String) -> void:
	character = res
	var info := player.set_model(res["node"])
	character["info"] = info
	settings.set_value("character", "last", path)
	var anims: Dictionary = info.get("animation_map", {})
	var msg := "Personnage : %s — squelette %s — animations %s" % [res.get("name", "?"),
		"oui" if info.get("skeleton", false) else "non", ", ".join(PackedStringArray(anims.keys())) if not anims.is_empty() else "aucune (balancement procédural)"]
	if res.has("warning"):
		msg += "\n" + str(res["warning"])
	show_status(msg)


# ---------------------------------------------------------------- entrées
func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("interact"):
		try_interact()
	elif event.is_action_pressed("screenshot"):
		screenshot("")
	elif event.is_action_pressed("next_decor"):
		load_decor(decor_index + 1)
	elif event.is_action_pressed("next_profile"):
		profile = PersonaHardware.PROFILES[(PersonaHardware.PROFILES.find(profile) + 1) % 3]
		settings.set_value("video", "profile", profile)
		PersonaHardware.apply(profile, get_viewport(), decor.get("light"))
		show_status("Profil graphique : " + profile)
	elif event.is_action_pressed("free_camera"):
		cam.toggle_free()
		player.input_enabled = not cam.free_mode
		show_status("Caméra libre" if cam.free_mode else "Caméra de suivi")
	elif event.is_action_pressed("import_character"):
		_open_import()
	elif event.is_action_pressed("toggle_help"):
		help_label.visible = not help_label.visible


func try_interact() -> String:
	var best := {}
	var best_d := 1.8
	for it in decor.get("interactables", []):
		var d := player.global_position.distance_to(PersonaDecors.position_of(it))
		if d < best_d:
			best_d = d
			best = it
	if best.is_empty():
		show_status("Rien à portée (approchez-vous d'un objet)")
		return ""
	var msg := PersonaDecors.interact(best, player.global_position)
	show_status(msg)
	return msg


func screenshot(path: String) -> String:
	if DisplayServer.get_name() == "headless":
		show_status("Capture indisponible en mode sans affichage")
		return ""
	var img := get_viewport().get_texture().get_image()
	if path == "":
		DirAccess.make_dir_recursive_absolute("user://screenshots")
		path = "user://screenshots/persona_%s.png" % Time.get_datetime_string_from_system().replace(":", "-")
	img.save_png(path)
	show_status("Capture : " + ProjectSettings.globalize_path(path))
	return path


func _open_import() -> void:
	if file_dialog == null:
		file_dialog = FileDialog.new()
		file_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
		file_dialog.access = FileDialog.ACCESS_FILESYSTEM
		file_dialog.use_native_dialog = true
		file_dialog.filters = PackedStringArray(["*.glb, *.gltf ; Modèle 3D glTF", "persona_character.json ; Dossier PERSONA"])
		file_dialog.file_selected.connect(func(p: String) -> void: load_character_path(p))
		add_child(file_dialog)
	file_dialog.popup_centered_ratio(0.7)


# ---------------------------------------------------------------- HUD, réglages
func _build_hud() -> void:
	add_child(hud)
	for l in [info_label, status_label, help_label]:
		l.add_theme_color_override("font_color", Color.WHITE)
		l.add_theme_color_override("font_shadow_color", Color.BLACK)
		l.add_theme_constant_override("shadow_offset_x", 1)
		l.add_theme_constant_override("shadow_offset_y", 1)
		hud.add_child(l)
	info_label.position = Vector2(12, 8)
	status_label.position = Vector2(12, 680)
	help_label.position = Vector2(12, 120)
	help_label.text = "ZQSD / WASD / flèches : se déplacer · Maj : courir · E : interagir\n" + \
		"Clic droit + souris ou J/L/I/K : tourner la caméra · molette ou +/- : zoom · C : caméra libre\n" + \
		"N : décor suivant · F2 : importer un personnage (GLB ou dossier PERSONA) · F3 : profil graphique\n" + \
		"F12 ou P : capture d'écran · F1/H : aide"


func _process(delta: float) -> void:
	player.camera_yaw = cam.yaw
	info_label.text = "PERSONA LIVE — %s · état %s (%s) · %d img/s · profil %s\n%s · %d cœurs · RAM %s Go · %s" % [
		character.get("name", "?"), player.state, player.current_animation(), Engine.get_frames_per_second(), profile,
		str(hw.get("cpu", "?")), int(hw.get("cores", 0)), str(hw.get("ram_gb", "?")), str(hw.get("gpu", "?"))]
	if _status_t > 0.0:
		_status_t -= delta
		if _status_t <= 0.0:
			status_label.text = ""


func show_status(msg: String) -> void:
	status_label.text = msg
	_status_t = 6.0
	print("[PERSONA LIVE] ", msg)


func save_settings() -> int:
	settings.set_value("video", "profile", profile)
	settings.set_value("controls", "mouse_sensitivity", cam.sensitivity)
	return settings.save(SETTINGS_PATH)


func _write_lock() -> void:
	var f := FileAccess.open(LOCK_PATH, FileAccess.WRITE)
	if f:
		f.store_string(str(OS.get_process_id()))
		f.close()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_PREDELETE:
		save_settings()
		DirAccess.remove_absolute(ProjectSettings.globalize_path(LOCK_PATH))

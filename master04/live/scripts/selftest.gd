extends Node
## Test automatisé exécuté DANS l'application (y compris l'exécutable Windows exporté) :
##   PERSONA_LIVE.exe [--headless] -- --selftest [--report=chemin.json] [--screenshot=chemin.png] [--character=chemin]
## Simule les touches, vérifie déplacement, course, arrêt, rotation, interaction, décors, import, réglages.

var main: Node
var results := []
var report := {}


func _ready() -> void:
	main = get_parent()
	_run.call_deferred()


func _arg(key: String) -> String:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--%s=" % key):
			return a.substr(key.length() + 3)
	return ""


func _check(name: String, ok: bool, detail := "") -> void:
	results.append({"test": name, "ok": ok, "detail": detail})
	print("[SELFTEST] %s %s %s" % ["PASS" if ok else "FAIL", name, detail])


func _frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _hold(action: String, frames: int) -> void:
	Input.action_press(action)
	await _frames(frames)
	Input.action_release(action)


func _run() -> void:
	var p: PersonaPlayer = main.player
	await _frames(20)
	_check("scene_loaded", main.decor.has("spawn") and p.is_inside_tree(), str(main.decor.get("name", "")))
	var info: Dictionary = main.character.get("info", {})
	_check("character_skeleton", info.get("skeleton", false), str(main.character.get("name", "")))
	_check("character_animations", not info.get("procedural_fallback", true), str(info.get("animation_map", {})))

	# Marche
	var start := p.global_position
	Input.action_press("move_forward")
	await _frames(40)
	var walk_state: String = p.state
	var walk_anim: String = p.current_animation()
	Input.action_release("move_forward")
	var walked := start.distance_to(p.global_position)
	_check("walk_moves", walked > 0.5, "%.2f m, état %s, anim %s" % [walked, walk_state, walk_anim])
	_check("walk_state", walk_state == "walk")

	# Course
	start = p.global_position
	Input.action_press("move_forward")
	Input.action_press("run")
	await _frames(60)
	var run_state: String = p.state
	var run_speed := Vector2(p.velocity.x, p.velocity.z).length()
	Input.action_release("run")
	Input.action_release("move_forward")
	_check("run_faster", run_speed > 3.0 and run_state == "run", "vitesse %.2f m/s, anim %s" % [run_speed, p.current_animation()])

	# Arrêt
	await _frames(60)
	_check("stop_idle", p.state == "idle" and Vector2(p.velocity.x, p.velocity.z).length() < 0.2, p.current_animation())

	# Rotation : se déplacer à droite doit faire tourner le modèle
	var rot0: float = p.model_root.rotation.y
	await _hold("move_right", 45)
	var rot1: float = p.model_root.rotation.y
	_check("turns_towards_motion", absf(wrapf(rot1 - rot0, -PI, PI)) > 0.8, "%.2f -> %.2f rad" % [rot0, rot1])
	await _frames(30)

	# Caméra : rotation et zoom
	var yaw0: float = main.cam.yaw
	var d0: float = main.cam.distance
	await _hold("cam_left", 30)
	await _hold("zoom_in", 20)
	_check("camera_orbit_zoom", main.cam.yaw != yaw0 and main.cam.distance < d0)

	# Interaction : se placer près de la lampe et appuyer sur E
	var lamp := {}
	for it in main.decor["interactables"]:
		if it["kind"] == "lamp":
			lamp = it
	p.global_position = PersonaDecors.position_of(lamp) + Vector3(0.8, 0.1, 0)
	await _frames(5)
	var before: bool = (lamp["light"] as OmniLight3D).visible
	var msg: String = main.try_interact()
	_check("interaction_lamp", (lamp["light"] as OmniLight3D).visible != before, msg)

	# Décors (registre jusqu'à 5)
	var d_before: String = main.decor["id"]
	main.load_decor(main.decor_index + 1)
	await _frames(10)
	_check("decor_switch", main.decor["id"] != d_before and PersonaDecors.count() <= PersonaDecors.MAX_DECORS, "%s -> %s" % [d_before, main.decor["id"]])
	main.load_decor(0)
	await _frames(10)

	# Import d'un personnage personnalisé (GLB ou dossier PERSONA) au moment de l'exécution
	var custom := _arg("character")
	if custom == "":
		# 1) dossier characters/ livré à côté de l'exécutable (import depuis le disque, comme un utilisateur)
		var beside := OS.get_executable_path().get_base_dir().path_join("characters/persona_demo.glb")
		if FileAccess.file_exists(beside):
			custom = beside
	if custom == "":
		# 2) projet lancé depuis l'éditeur : copie le GLB source hors du paquet
		var src := "res://characters/demo/persona_demo.glb"
		if FileAccess.file_exists(src):
			custom = OS.get_user_data_dir().path_join("selftest_import.glb")
			var f := FileAccess.open(custom, FileAccess.WRITE)
			f.store_buffer(FileAccess.get_file_as_bytes(src))
			f.close()
	if custom != "":
		var ok: bool = main.load_character_path(custom)
		await _frames(10)
		var ci: Dictionary = main.character.get("info", {})
		_check("custom_import", ok and ci.get("skeleton", false), "%s · anims %s" % [custom.get_file(), str(ci.get("animation_map", {}).keys())])
		start = p.global_position
		await _hold("move_forward", 40)
		_check("custom_character_moves", start.distance_to(p.global_position) > 0.5)
	else:
		_check("custom_import", false, "aucun GLB disponible pour le test")

	# Réglages
	main.profile = "leger"
	var err: int = main.save_settings()
	var cfg := ConfigFile.new()
	cfg.load(main.SETTINGS_PATH)
	_check("settings_saved", err == OK and str(cfg.get_value("video", "profile", "")) == "leger")

	# Capture d'écran (uniquement avec affichage)
	var shot := _arg("screenshot")
	if DisplayServer.get_name() != "headless":
		var path: String = main.screenshot(shot)
		_check("screenshot", path != "" and FileAccess.file_exists(path), ProjectSettings.globalize_path(path))
	else:
		results.append({"test": "screenshot", "ok": null, "detail": "non testé : mode sans affichage"})

	var failed := results.filter(func(r): return r["ok"] == false)
	report = {"app": "PERSONA LIVE", "version": ProjectSettings.get_setting("application/config/version"),
		"display": DisplayServer.get_name(), "hardware": main.hw, "character": main.character.get("name", ""),
		"results": results, "passed": results.size() - failed.size(), "failed": failed.size(),
		"time": Time.get_datetime_string_from_system()}
	var rp := _arg("report")
	if rp == "":
		rp = "user://selftest_report.json"
	var rf := FileAccess.open(rp, FileAccess.WRITE)
	if rf:
		rf.store_string(JSON.stringify(report, "  "))
		rf.close()
	print("[SELFTEST] %d réussis, %d échecs — rapport %s" % [report["passed"], report["failed"], ProjectSettings.globalize_path(rp)])
	get_tree().quit(1 if failed.size() > 0 else 0)

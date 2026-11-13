extends CharacterBody3D
## Contrôleur 3e personne : marche, course, arrêt, rotation vers la direction ; transitions d'animations.
class_name PersonaPlayer

const WALK_SPEED := 1.6
const RUN_SPEED := 4.2
const ACCEL := 10.0
const TURN_SPEED := 10.0
const BLEND := 0.25

var camera_yaw := 0.0            # fourni par la caméra (déplacement relatif à la vue)
var input_enabled := true
var state := "idle"              # idle | walk | run
var turning := false
var anim_player: AnimationPlayer
var anim_map := {}               # état -> nom d'animation réel
var model_root := Node3D.new()
var model_info := {}
var _bob_t := 0.0
var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity", 9.8)


func _ready() -> void:
	var shape := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.3
	cap.height = 1.75
	shape.shape = cap
	shape.position = Vector3(0, 0.875, 0)
	add_child(shape)
	model_root.name = "Model"
	add_child(model_root)


func set_model(node: Node3D) -> Dictionary:
	for c in model_root.get_children():
		c.queue_free()
	model_root.add_child(node)
	model_info = PersonaCharacterLoader.normalize(node)
	anim_player = PersonaCharacterLoader._find(node, "AnimationPlayer") as AnimationPlayer
	anim_map.clear()
	if anim_player:
		var names: PackedStringArray = anim_player.get_animation_list()
		for st in ["idle", "walk", "run"]:
			for n in names:
				if n.to_lower().contains(st):
					anim_map[st] = n
					break
		for n in anim_map.values():
			var a: Animation = anim_player.get_animation(n)
			if a:
				a.loop_mode = Animation.LOOP_LINEAR
		if anim_map.has("walk") and not anim_map.has("run"):
			anim_map["run"] = anim_map["walk"]
		if not anim_map.is_empty():
			_play("idle" if anim_map.has("idle") else anim_map.keys()[0])
	model_info["animation_map"] = anim_map
	model_info["procedural_fallback"] = anim_map.is_empty()
	return model_info


func _physics_process(delta: float) -> void:
	var dir := Vector3.ZERO
	var running := false
	if input_enabled:
		var v := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
		dir = Vector3(v.x, 0, v.y).rotated(Vector3.UP, camera_yaw)
		running = Input.is_action_pressed("run")
	var target_speed := (RUN_SPEED if running else WALK_SPEED) * minf(dir.length(), 1.0)
	var horiz := Vector3(velocity.x, 0, velocity.z)
	var target := dir.normalized() * target_speed if dir.length() > 0.05 else Vector3.ZERO
	horiz = horiz.lerp(target, clampf(ACCEL * delta, 0.0, 1.0))
	velocity.x = horiz.x
	velocity.z = horiz.z
	if not is_on_floor():
		velocity.y -= _gravity * delta
	else:
		velocity.y = 0.0
	move_and_slide()

	# Rotation du personnage vers la direction de déplacement (le modèle glTF regarde +Z).
	turning = false
	if horiz.length() > 0.1:
		var want := atan2(horiz.x, horiz.z)
		var diff := wrapf(want - model_root.rotation.y, -PI, PI)
		turning = absf(diff) > 0.35
		model_root.rotation.y = lerp_angle(model_root.rotation.y, want, clampf(TURN_SPEED * delta, 0.0, 1.0))

	var speed := horiz.length()
	var new_state := "idle"
	if speed > 2.6:
		new_state = "run"
	elif speed > 0.15:
		new_state = "walk"
	if new_state != state:
		state = new_state
		_play(state)
	if anim_map.is_empty():
		_procedural(delta, speed)


func _play(st: String) -> void:
	if anim_player and anim_map.has(st):
		anim_player.play(anim_map[st], BLEND, (1.3 if st == "run" and anim_map["run"] == anim_map.get("walk", "") else 1.0))


func current_animation() -> String:
	return anim_player.current_animation if anim_player else "(procédural)"


## Personnage sans animations : léger balancement pour visualiser l'état.
func _procedural(delta: float, speed: float) -> void:
	_bob_t += delta * (2.0 + speed * 3.0)
	for c in model_root.get_children():
		if c is Node3D:
			(c as Node3D).rotation.z = sin(_bob_t) * 0.04 * minf(speed, 3.0)

extends Node3D
## Caméra orbitale qui suit le personnage ; rotation (souris clic droit ou J/L/I/K), zoom (molette, +/-),
## mode caméra libre (C) : les touches de déplacement déplacent alors la caméra au lieu du personnage.
class_name PersonaCameraRig

var target: Node3D
var yaw := 0.0
var pitch := -0.35
var distance := 4.5
var free_mode := false
var free_pos := Vector3.ZERO
var sensitivity := 0.006
var camera := Camera3D.new()


func _ready() -> void:
	camera.fov = 60.0
	camera.near = 0.05
	add_child(camera)
	camera.make_current()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		var m := event as InputEventMouseMotion
		yaw -= m.relative.x * sensitivity
		pitch = clampf(pitch - m.relative.y * sensitivity, -1.3, 0.4)
	elif event is InputEventMouseButton:
		var b := event as InputEventMouseButton
		if not b.pressed:
			return
		if b.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = clampf(distance - 0.4, 1.5, 14.0)
		elif b.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = clampf(distance + 0.4, 1.5, 14.0)


func toggle_free() -> void:
	free_mode = not free_mode
	free_pos = camera.global_position


func _process(delta: float) -> void:
	yaw += (Input.get_action_strength("cam_left") - Input.get_action_strength("cam_right")) * 1.8 * delta
	pitch = clampf(pitch + (Input.get_action_strength("cam_up") - Input.get_action_strength("cam_down")) * 1.2 * delta, -1.3, 0.4)
	distance = clampf(distance + (Input.get_action_strength("zoom_out") - Input.get_action_strength("zoom_in")) * 4.0 * delta, 1.5, 14.0)
	var rot := Basis(Vector3.UP, yaw) * Basis(Vector3.RIGHT, pitch)
	if free_mode:
		var v := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
		var up := Input.get_action_strength("run")
		free_pos += (rot * Vector3(v.x, 0, v.y) + Vector3.UP * up) * 4.0 * delta
		camera.global_transform = Transform3D(rot, free_pos)
		return
	if target == null:
		return
	var focus := target.global_position + Vector3(0, 1.45, 0)
	var pos := focus + rot * Vector3(0, 0, distance)
	camera.global_transform = Transform3D(rot, pos)

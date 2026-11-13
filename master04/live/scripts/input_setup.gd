extends RefCounted
## Actions clavier par code. Touches PHYSIQUES : WASD QWERTY = ZQSD sur clavier AZERTY.
class_name PersonaInput

const BINDINGS := {
	"move_forward": [KEY_W, KEY_UP],
	"move_back": [KEY_S, KEY_DOWN],
	"move_left": [KEY_A, KEY_LEFT],
	"move_right": [KEY_D, KEY_RIGHT],
	"run": [KEY_SHIFT],
	"interact": [KEY_E],
	"cam_left": [KEY_J],
	"cam_right": [KEY_L],
	"cam_up": [KEY_I],
	"cam_down": [KEY_K],
	"zoom_in": [KEY_EQUAL, KEY_KP_ADD],
	"zoom_out": [KEY_MINUS, KEY_KP_SUBTRACT],
	"free_camera": [KEY_C],
	"screenshot": [KEY_F12, KEY_P],
	"import_character": [KEY_F2],
	"next_decor": [KEY_N],
	"next_profile": [KEY_F3],
	"toggle_help": [KEY_F1, KEY_H],
}


static func register() -> void:
	for action in BINDINGS.keys():
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key in BINDINGS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)

extends RefCounted
## Registre de décors (maximum 5). Chaque décor est construit par code (aucun asset externe, licence libre).
## Ajouter un décor : une entrée dans LIST + une fonction _build_<id>.
class_name PersonaDecors

const MAX_DECORS := 5
const LIST := [
	{"id": "studio", "name": "Studio (intérieur)"},
	{"id": "jardin", "name": "Jardin (extérieur)"},
]


static func count() -> int:
	return mini(LIST.size(), MAX_DECORS)


## Construit le décor dans `parent` ; renvoie {spawn, interactables, light}.
static func build(index: int, parent: Node3D, profile: String) -> Dictionary:
	for c in parent.get_children():
		c.queue_free()
	var id: String = LIST[index % count()]["id"]
	var res: Dictionary
	match id:
		"jardin":
			res = _build_jardin(parent, profile)
		_:
			res = _build_studio(parent, profile)
	res["id"] = id
	res["name"] = LIST[index % count()]["name"]
	return res


static func _mat(color: Color, rough := 0.85, emission := Color.BLACK) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = rough
	if emission != Color.BLACK:
		m.emission_enabled = true
		m.emission = emission
	return m


static func _box(parent: Node3D, size: Vector3, pos: Vector3, color: Color, solid := true) -> Node3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = _mat(color)
	if solid:
		var body := StaticBody3D.new()
		body.position = pos
		var cs := CollisionShape3D.new()
		var sh := BoxShape3D.new()
		sh.size = size
		cs.shape = sh
		body.add_child(cs)
		body.add_child(mi)
		parent.add_child(body)
		return body
	mi.position = pos
	parent.add_child(mi)
	return mi


static func _light(parent: Node3D, profile: String, energy := 1.0) -> DirectionalLight3D:
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 35, 0)
	sun.light_energy = energy
	sun.shadow_enabled = profile != "leger"
	parent.add_child(sun)
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.62, 0.72, 0.85)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.55, 0.55, 0.6)
	e.ambient_light_energy = 0.7
	env.environment = e
	parent.add_child(env)
	return sun


static func _lamp(parent: Node3D, pos: Vector3) -> Dictionary:
	var lamp := _box(parent, Vector3(0.3, 1.4, 0.3), pos + Vector3(0, 0.7, 0), Color(0.25, 0.25, 0.28))
	var bulb := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.2
	sm.height = 0.4
	bulb.mesh = sm
	var off := _mat(Color(0.9, 0.9, 0.8))
	var on := _mat(Color(1, 0.95, 0.7), 0.5, Color(1.0, 0.85, 0.4))
	bulb.material_override = off
	bulb.position = pos + Vector3(0, 1.55, 0)
	parent.add_child(bulb)
	var light := OmniLight3D.new()
	light.position = pos + Vector3(0, 1.6, 0)
	light.omni_range = 6.0
	light.light_energy = 2.0
	light.light_color = Color(1, 0.85, 0.55)
	light.visible = false
	parent.add_child(light)
	return {"kind": "lamp", "label": "lampe (allumer / éteindre)", "position": pos, "light": light, "bulb": bulb,
		"on_mat": on, "off_mat": off, "node": lamp}


static func _ball(parent: Node3D, pos: Vector3) -> Dictionary:
	var rb := RigidBody3D.new()
	rb.position = pos
	rb.mass = 0.6
	var cs := CollisionShape3D.new()
	var sh := SphereShape3D.new()
	sh.radius = 0.22
	cs.shape = sh
	rb.add_child(cs)
	var mi := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.22
	sm.height = 0.44
	mi.mesh = sm
	mi.material_override = _mat(Color(0.85, 0.2, 0.15), 0.4)
	rb.add_child(mi)
	parent.add_child(rb)
	return {"kind": "ball", "label": "ballon (pousser)", "body": rb}


static func _build_studio(parent: Node3D, profile: String) -> Dictionary:
	var sun := _light(parent, profile, 0.9)
	_box(parent, Vector3(24, 0.2, 24), Vector3(0, -0.1, 0), Color(0.55, 0.5, 0.45))
	_box(parent, Vector3(24, 3, 0.3), Vector3(0, 1.5, -12), Color(0.8, 0.78, 0.74))
	_box(parent, Vector3(24, 3, 0.3), Vector3(0, 1.5, 12), Color(0.8, 0.78, 0.74))
	_box(parent, Vector3(0.3, 3, 24), Vector3(-12, 1.5, 0), Color(0.78, 0.76, 0.72))
	_box(parent, Vector3(0.3, 3, 24), Vector3(12, 1.5, 0), Color(0.78, 0.76, 0.72))
	for p in [Vector3(4, 0.5, -3), Vector3(-5, 0.5, 4), Vector3(6, 0.5, 6)]:
		_box(parent, Vector3(1, 1, 1), p, Color(0.6, 0.42, 0.25))
	_box(parent, Vector3(3, 0.8, 1.2), Vector3(-6, 0.4, -6), Color(0.3, 0.35, 0.5))
	return {"spawn": Vector3(0, 0.1, 2), "interactables": [_lamp(parent, Vector3(2.5, 0, -1)), _ball(parent, Vector3(-1.5, 0.3, -1.5))], "light": sun}


static func _build_jardin(parent: Node3D, profile: String) -> Dictionary:
	var sun := _light(parent, profile, 1.2)
	_box(parent, Vector3(60, 0.2, 60), Vector3(0, -0.1, 0), Color(0.3, 0.55, 0.25))
	var trees := 6 if profile == "leger" else 14
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in trees:
		var p := Vector3(rng.randf_range(-22, 22), 0, rng.randf_range(-22, 22))
		if p.length() < 5:
			continue
		_box(parent, Vector3(0.4, 2.5, 0.4), p + Vector3(0, 1.25, 0), Color(0.4, 0.27, 0.15))
		var crown := MeshInstance3D.new()
		var sm := SphereMesh.new()
		sm.radius = 1.4
		sm.height = 2.4
		crown.mesh = sm
		crown.material_override = _mat(Color(0.18, 0.42, 0.18))
		crown.position = p + Vector3(0, 3.2, 0)
		parent.add_child(crown)
	_box(parent, Vector3(2.0, 0.5, 0.6), Vector3(-3, 0.25, -3), Color(0.5, 0.35, 0.2))
	return {"spawn": Vector3(0, 0.1, 0), "interactables": [_lamp(parent, Vector3(3, 0, -2)), _ball(parent, Vector3(1.5, 0.3, 2.5))], "light": sun}


## Interaction : renvoie un message.
static func interact(it: Dictionary, player_pos: Vector3) -> String:
	match str(it.get("kind", "")):
		"lamp":
			var l: OmniLight3D = it["light"]
			l.visible = not l.visible
			(it["bulb"] as MeshInstance3D).material_override = it["on_mat"] if l.visible else it["off_mat"]
			return "Lampe " + ("allumée" if l.visible else "éteinte")
		"ball":
			var rb: RigidBody3D = it["body"]
			var d := rb.global_position - player_pos
			d.y = 0
			rb.apply_central_impulse(d.normalized() * 3.0 + Vector3.UP * 1.2)
			return "Ballon poussé"
	return ""


static func position_of(it: Dictionary) -> Vector3:
	if it.get("kind", "") == "ball":
		return (it["body"] as RigidBody3D).global_position
	return it.get("position", Vector3.ZERO)

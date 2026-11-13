extends RefCounted
## Chargement des personnages : démo intégrée, fichier GLB/glTF, ou dossier PERSONA (persona_character.json).
class_name PersonaCharacterLoader

const DEMO_PATH := "res://characters/demo/persona_demo.glb"
const TARGET_HEIGHT := 1.75


## Personnage de démonstration (généré par master04/pipeline/blender/make_demo_character.py, CC0).
static func load_demo() -> Dictionary:
	if ResourceLoader.exists(DEMO_PATH):
		var packed: PackedScene = load(DEMO_PATH)
		if packed:
			return {"node": packed.instantiate(), "source": "demo", "name": "Démo PERSONA (générique)", "level": "demo"}
	return {"node": _fallback_mannequin(), "source": "fallback", "name": "Mannequin de secours (sans squelette)", "level": "demo",
		"warning": "Personnage de démonstration absent : mannequin de secours sans animation."}


## GLB/glTF au moment de l'exécution (personnage personnalisé).
static func load_gltf(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {"error": "fichier introuvable : %s" % path}
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	var err := doc.append_from_file(path, state)
	if err != OK:
		return {"error": "glTF illisible (erreur %d)" % err}
	var scene: Node = doc.generate_scene(state)
	if scene == null:
		return {"error": "impossible de construire la scène"}
	return {"node": scene, "source": path, "name": path.get_file().get_basename(), "level": "custom"}


## Dossier de personnage PERSONA : persona_character.json -> model (GLB) + métadonnées.
static func load_persona_folder(dir: String) -> Dictionary:
	var manifest_path := dir.path_join("persona_character.json")
	if not FileAccess.file_exists(manifest_path):
		return {"error": "persona_character.json absent de %s" % dir}
	var data = JSON.parse_string(FileAccess.get_file_as_string(manifest_path))
	if typeof(data) != TYPE_DICTIONARY:
		return {"error": "persona_character.json invalide"}
	var model: String = str(data.get("model", {}).get("file", ""))
	if model == "":
		return {"error": "aucun modèle 3D déclaré dans le dossier"}
	var res := load_gltf(dir.path_join(model))
	if res.has("error"):
		return res
	res["name"] = str(data.get("display_name", res["name"]))
	res["level"] = "persona_folder"
	res["identity_status"] = str(data.get("model", {}).get("identity_status", "non évaluée"))
	res["manifest"] = data
	return res


## Met à l'échelle (taille cible), pose les pieds au sol, renvoie infos squelette / animations.
static func normalize(node: Node3D) -> Dictionary:
	var aabb := _merged_aabb(node, Transform3D.IDENTITY)
	var info := {"height_raw": aabb.size.y, "skeleton": _find(node, "Skeleton3D") != null}
	if aabb.size.y > 0.01:
		var s := TARGET_HEIGHT / aabb.size.y
		node.scale = Vector3.ONE * s
		node.position = Vector3(-(aabb.position.x + aabb.size.x * 0.5) * s, -aabb.position.y * s, -(aabb.position.z + aabb.size.z * 0.5) * s)
	var player := _find(node, "AnimationPlayer") as AnimationPlayer
	info["animations"] = player.get_animation_list() if player else PackedStringArray()
	return info


static func _merged_aabb(n: Node, xf: Transform3D) -> AABB:
	var out := AABB()
	var first := true
	var t := xf
	if n is Node3D:
		t = xf * (n as Node3D).transform
	if n is MeshInstance3D and (n as MeshInstance3D).mesh:
		var a: AABB = t * (n as MeshInstance3D).mesh.get_aabb()
		out = a
		first = false
	for c in n.get_children():
		var ca := _merged_aabb(c, t)
		if ca.size != Vector3.ZERO:
			out = ca if first else out.merge(ca)
			first = false
	return out


static func _find(n: Node, cls: String) -> Node:
	if n.is_class(cls):
		return n
	for c in n.get_children():
		var r := _find(c, cls)
		if r:
			return r
	return null


static func _fallback_mannequin() -> Node3D:
	var root := Node3D.new()
	var body := MeshInstance3D.new()
	var cap := CapsuleMesh.new()
	cap.radius = 0.25
	cap.height = 1.4
	body.mesh = cap
	body.position = Vector3(0, 0.7, 0)
	root.add_child(body)
	var head := MeshInstance3D.new()
	var sph := SphereMesh.new()
	sph.radius = 0.13
	sph.height = 0.26
	head.mesh = sph
	head.position = Vector3(0, 1.58, 0)
	root.add_child(head)
	return root

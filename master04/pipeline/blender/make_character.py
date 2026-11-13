"""PERSONA 3D — génère un personnage humanoïde RIGGÉ et animé dans Blender (headless), exporte GLB + FBX.

Usage :
  blender -b --factory-startup --python make_character.py -- --out DIR [--params proportions.json] [--name NOM]

* Sans --params : personnage de DÉMONSTRATION générique (mannequin, licence CC0, aucune ressemblance).
* Avec --params : mêmes géométrie et squelette, mais proportions ajustées aux ESTIMATIONS RELATIVES
  de la phase 2 (taille, largeur d'épaules et de hanches, longueur des jambes). Ce n'est PAS une
  reconstruction du visage ni du corps : seules les proportions globales sont approchées.

Squelette (18 os) : root, hips, spine, chest, neck, head, upper_arm/forearm/hand .L/.R, thigh/shin/foot .L/.R
Animations (glTF) : idle, walk, run (cycles bouclables), wave (interaction).
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

DEFAULT = {"height": 1.75, "shoulder_ratio": 0.245, "hip_ratio": 0.19, "leg_ratio": 0.47, "head_ratio": 0.13,
           "skin": [0.80, 0.62, 0.50], "shirt": [0.20, 0.35, 0.62], "pants": [0.15, 0.15, 0.18], "shoes": [0.08, 0.08, 0.08]}


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--params", default="")
    ap.add_argument("--name", default="persona_demo")
    return ap.parse_args(argv)


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def joints(p):
    """Positions des articulations (Blender : Z vers le haut, personnage regardant -Y)."""
    H = p["height"]
    leg = H * p["leg_ratio"]
    hip_w = H * p["hip_ratio"] / 2
    sh_w = H * p["shoulder_ratio"] / 2
    head = H * p["head_ratio"]
    hip_z = leg + 0.04 * H
    j = {
        "root": Vector((0, 0, 0)), "hips": Vector((0, 0, hip_z)),
        "spine": Vector((0, 0, hip_z + 0.10 * H)), "chest": Vector((0, 0, hip_z + 0.20 * H)),
        "neck": Vector((0, 0, H - head - 0.035 * H)), "head": Vector((0, 0, H - head)), "head_top": Vector((0, 0, H)),
    }
    sh_z = j["neck"].z - 0.02 * H
    for s, sx in (("L", 1), ("R", -1)):
        j[f"shoulder.{s}"] = Vector((sx * sh_w, 0, sh_z))
        j[f"elbow.{s}"] = Vector((sx * (sh_w + 0.02 * H), 0, sh_z - 0.17 * H))
        j[f"wrist.{s}"] = Vector((sx * (sh_w + 0.03 * H), 0, sh_z - 0.33 * H))
        j[f"fingers.{s}"] = Vector((sx * (sh_w + 0.035 * H), 0, sh_z - 0.40 * H))
        j[f"hip.{s}"] = Vector((sx * hip_w * 0.75, 0, hip_z))
        j[f"knee.{s}"] = Vector((sx * hip_w * 0.72, -0.01, hip_z - leg * 0.52))
        j[f"ankle.{s}"] = Vector((sx * hip_w * 0.70, 0, 0.06 * H))
        j[f"toe.{s}"] = Vector((sx * hip_w * 0.70, -0.13 * H / 1.75, 0.02))
    return j


BONES = [  # nom, tête, queue, parent
    ("root", "root", "hips", None), ("hips", "hips", "spine", "root"), ("spine", "spine", "chest", "hips"),
    ("chest", "chest", "neck", "spine"), ("neck", "neck", "head", "chest"), ("head", "head", "head_top", "neck"),
]
for _s in ("L", "R"):
    BONES += [(f"upper_arm.{_s}", f"shoulder.{_s}", f"elbow.{_s}", "chest"), (f"forearm.{_s}", f"elbow.{_s}", f"wrist.{_s}", f"upper_arm.{_s}"),
              (f"hand.{_s}", f"wrist.{_s}", f"fingers.{_s}", f"forearm.{_s}"), (f"thigh.{_s}", f"hip.{_s}", f"knee.{_s}", "hips"),
              (f"shin.{_s}", f"knee.{_s}", f"ankle.{_s}", f"thigh.{_s}"), (f"foot.{_s}", f"ankle.{_s}", f"toe.{_s}", f"shin.{_s}")]


def make_armature(j):
    arm_data = bpy.data.armatures.new("PersonaRig")
    arm = bpy.data.objects.new("PersonaRig", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for name, h, t, parent in BONES:
        b = arm_data.edit_bones.new(name)
        b.head, b.tail = j[h], j[t]
        if (b.tail - b.head).length < 1e-3:
            b.tail = b.head + Vector((0, 0, 0.05))
        b.roll = 0
        if parent:
            b.parent = eb[parent]
        eb[name] = b
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def material(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7
    return m


def limb(bm, a, b, r1, r2, group_layer, group, mat_index, segs=12):
    """Cylindre conique entre a et b, tous les sommets pondérés 1.0 sur `group`."""
    d = b - a
    length = d.length
    geom = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=length)
    verts = geom["verts"]
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    mat = Matrix.Translation((a + b) / 2) @ rot
    bmesh.ops.transform(bm, matrix=mat, verts=verts)
    for v in verts:
        v[group_layer][group] = 1.0
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = mat_index
        f.smooth = True


def ball(bm, c, r, group_layer, group, mat_index, scale=(1, 1, 1)):
    geom = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=r)
    verts = geom["verts"]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c) @ Matrix.Diagonal((*scale, 1)), verts=verts)
    for v in verts:
        v[group_layer][group] = 1.0
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = mat_index
        f.smooth = True


def make_body(j, p, arm):
    H = p["height"]
    mesh = bpy.data.meshes.new("PersonaBody")
    obj = bpy.data.objects.new("PersonaBody", mesh)
    bpy.context.scene.collection.objects.link(obj)
    names = [b[0] for b in BONES]
    for n in names:
        obj.vertex_groups.new(name=n)
    for key in ("skin", "shirt", "pants", "shoes"):
        obj.data.materials.append(material(key, p[key]))
    SKIN, SHIRT, PANTS, SHOES = 0, 1, 2, 3
    bm = bmesh.new()
    dl = bm.verts.layers.deform.verify()
    gi = {n: i for i, n in enumerate(names)}
    sh_w = H * p["shoulder_ratio"] / 2
    hip_w = H * p["hip_ratio"] / 2
    # torse et bassin
    limb(bm, j["hips"] - Vector((0, 0, 0.03 * H)), j["spine"], hip_w * 1.05, hip_w * 0.95, dl, gi["hips"], PANTS)
    limb(bm, j["spine"], j["chest"], hip_w * 0.95, sh_w * 0.80, dl, gi["spine"], SHIRT)
    limb(bm, j["chest"], j["neck"], sh_w * 0.80, sh_w * 0.55, dl, gi["chest"], SHIRT)
    limb(bm, j["neck"], j["head"] + Vector((0, 0, 0.01)), 0.03 * H, 0.028 * H, dl, gi["neck"], SKIN)
    ball(bm, (j["head"] + j["head_top"]) / 2, H * p["head_ratio"] / 2, dl, gi["head"], SKIN, scale=(0.82, 0.95, 1.0))
    for s in ("L", "R"):
        ball(bm, j[f"shoulder.{s}"], 0.032 * H, dl, gi[f"upper_arm.{s}"], SHIRT)
        limb(bm, j[f"shoulder.{s}"], j[f"elbow.{s}"], 0.028 * H, 0.023 * H, dl, gi[f"upper_arm.{s}"], SHIRT)
        limb(bm, j[f"elbow.{s}"], j[f"wrist.{s}"], 0.022 * H, 0.017 * H, dl, gi[f"forearm.{s}"], SKIN)
        ball(bm, (j[f"wrist.{s}"] + j[f"fingers.{s}"]) / 2, 0.026 * H, dl, gi[f"hand.{s}"], SKIN, scale=(0.6, 0.9, 1.4))
        limb(bm, j[f"hip.{s}"], j[f"knee.{s}"], 0.05 * H, 0.035 * H, dl, gi[f"thigh.{s}"], PANTS)
        limb(bm, j[f"knee.{s}"], j[f"ankle.{s}"], 0.034 * H, 0.024 * H, dl, gi[f"shin.{s}"], PANTS)
        ball(bm, (j[f"ankle.{s}"] + j[f"toe.{s}"]) / 2 + Vector((0, 0, -0.02 * H)), 0.04 * H, dl, gi[f"foot.{s}"], SHOES,
             scale=(0.7, 1.6, 0.55))
    bm.to_mesh(mesh)
    bm.free()
    obj.parent = arm
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    return obj


def key_pose(arm, frame, pose):
    for name, (x, y, z) in pose.items():
        pb = arm.pose.bones[name]
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (math.radians(x), math.radians(y), math.radians(z))
        pb.keyframe_insert("rotation_euler", frame=frame)


def cycle(arm, name, length, fn, steps=8):
    """Action bouclable : dernière clé = première."""
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    for i in range(steps + 1):
        t = (i % steps) / steps
        key_pose(arm, 1 + round(i * length / steps), fn(t))
    for fc in act.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = "BEZIER"
    track = arm.animation_data.nla_tracks.new()
    track.name = name
    track.strips.new(name, 1, act)
    arm.animation_data.action = None
    return act


def all_bones(extra):
    base = {b[0]: (0, 0, 0) for b in BONES if b[0] != "root"}
    base.update(extra)
    return base


def walk_pose(amp, lean, arm_amp, bounce_knee):
    def fn(t):
        s = math.sin(2 * math.pi * t)
        c = math.cos(2 * math.pi * t)
        return all_bones({
            "spine": (lean, 0, 0), "chest": (lean * 0.5, 4 * s, 0),
            "thigh.L": (amp * s, 0, 0), "thigh.R": (-amp * s, 0, 0),
            "shin.L": (-bounce_knee * max(0.0, c), 0, 0), "shin.R": (-bounce_knee * max(0.0, -c), 0, 0),
            "upper_arm.L": (-arm_amp * s, 0, -5), "upper_arm.R": (arm_amp * s, 0, 5),
            "forearm.L": (-15 - 10 * max(0.0, -s), 0, 0), "forearm.R": (-15 - 10 * max(0.0, s), 0, 0),
        })
    return fn


def idle_fn(t):
    b = math.sin(2 * math.pi * t)
    return all_bones({"chest": (1.5 * b, 0, 0), "head": (-1.0 * b, 2 * math.sin(math.pi * t), 0),
                      "upper_arm.L": (0, 0, -6 - 1.5 * b), "upper_arm.R": (0, 0, 6 + 1.5 * b),
                      "forearm.L": (-8, 0, 0), "forearm.R": (-8, 0, 0)})


def wave_fn(t):
    w = math.sin(4 * math.pi * t)
    return all_bones({"upper_arm.R": (0, 0, 150), "forearm.R": (0, 0, 25 * w), "upper_arm.L": (0, 0, -6),
                      "head": (0, 0, 5 * w)})


def main():
    a = args()
    p = dict(DEFAULT)
    source = "demo"
    if a.params:
        data = json.loads(Path(a.params).read_text(encoding="utf-8"))
        prop = data.get("proportions", data)
        for k in ("height", "shoulder_ratio", "hip_ratio", "leg_ratio", "head_ratio"):
            if prop.get(k) is not None:
                p[k] = float(prop[k])
        source = "proportions_estimees"
    clear()
    j = joints(p)
    arm = make_armature(j)
    make_body(j, p, arm)
    bpy.context.scene.render.fps = 30
    cycle(arm, "idle", 60, idle_fn)
    cycle(arm, "walk", 32, walk_pose(28, 4, 22, 45))
    cycle(arm, "run", 20, walk_pose(45, 12, 45, 85), steps=10)
    cycle(arm, "wave", 40, wave_fn)
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    glb = out / f"{a.name}.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", export_animation_mode="NLA_TRACKS",
                              export_skins=True, export_yup=True, export_apply=False, export_force_sampling=True)
    fbx = out / f"{a.name}.fbx"
    bpy.ops.export_scene.fbx(filepath=str(fbx), add_leaf_bones=False, bake_anim=True, bake_anim_use_nla_strips=True,
                             bake_anim_use_all_actions=False, object_types={"ARMATURE", "MESH"})
    info = {"name": a.name, "source": source, "params": p, "bones": [b[0] for b in BONES],
            "animations": ["idle", "walk", "run", "wave"], "glb": glb.name, "fbx": fbx.name,
            "glb_bytes": glb.stat().st_size, "fbx_bytes": fbx.stat().st_size, "blender": bpy.app.version_string,
            "licence": "CC0 1.0 (généré par script, aucun asset tiers)",
            "identity_status": "aucune ressemblance (démonstration)" if source == "demo"
            else "proportions globales approchées ; visage et morphologie NON reconstruits"}
    (out / f"{a.name}.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print("PERSONA_CHARACTER_OK", json.dumps(info, ensure_ascii=False))


main()

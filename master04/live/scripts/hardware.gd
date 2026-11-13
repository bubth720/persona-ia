extends RefCounted
## Détection matérielle et profils (léger / standard / avancé). La VRAM n'est pas exposée par Godot en rendu
## Compatibility : elle est lue dans user://hardware_report.json écrit par l'outil PC (persona_engine.hardware).
class_name PersonaHardware

const PROFILES := ["leger", "standard", "avance"]


static func detect() -> Dictionary:
	var info := {
		"os": OS.get_name(),
		"cpu": OS.get_processor_name(),
		"cores": OS.get_processor_count(),
		"gpu": RenderingServer.get_video_adapter_name(),
		"gpu_vendor": RenderingServer.get_video_adapter_vendor(),
		"renderer": str(ProjectSettings.get_setting("rendering/renderer/rendering_method", "")),
		"ram_gb": -1.0,
		"vram_gb": -1.0,
		"source": "godot",
	}
	var mem: Dictionary = {}
	if OS.has_method("get_memory_info"):
		mem = OS.call("get_memory_info")
	if mem.has("physical") and int(mem["physical"]) > 0:
		info["ram_gb"] = snappedf(float(mem["physical"]) / 1073741824.0, 0.1)
	var report_path := "user://hardware_report.json"
	if FileAccess.file_exists(report_path):
		var rep = JSON.parse_string(FileAccess.get_file_as_string(report_path))
		if typeof(rep) == TYPE_DICTIONARY:
			info["vram_gb"] = float(rep.get("gpu", {}).get("vram_gb", -1.0))
			info["source"] = "godot + hardware_report.json"
	info["profile"] = choose(info)
	return info


static func choose(info: Dictionary) -> String:
	var ram: float = info.get("ram_gb", -1.0)
	var vram: float = info.get("vram_gb", -1.0)
	var gpu := str(info.get("gpu", "")).to_lower()
	if (ram > 0 and ram < 12.0) or (vram > 0 and vram < 5.0) or gpu.contains("llvmpipe") or gpu.contains("intel") or gpu.contains("1650"):
		return "leger"
	if (ram >= 28.0) and (vram >= 10.0):
		return "avance"
	return "standard"


## Applique le profil : résolution de rendu, ombres, anticrénelage, limite d'images.
static func apply(profile: String, vp: Viewport, sun: DirectionalLight3D) -> Dictionary:
	var s: Dictionary = {"leger": {"scale": 0.75, "msaa": Viewport.MSAA_DISABLED, "shadows": false, "fps": 60},
		"standard": {"scale": 1.0, "msaa": Viewport.MSAA_2X, "shadows": true, "fps": 60},
		"avance": {"scale": 1.0, "msaa": Viewport.MSAA_4X, "shadows": true, "fps": 0}}[profile]
	vp.scaling_3d_scale = s["scale"]
	vp.msaa_3d = s["msaa"]
	if sun:
		sun.shadow_enabled = s["shadows"]
	Engine.max_fps = s["fps"]
	return s

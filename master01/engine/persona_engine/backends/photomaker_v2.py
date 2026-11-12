"""PhotoMaker V2 + SDXL backend (Phase B first candidate).

NOT EXECUTED in the authoring environment (no GPU, no HuggingFace access). It must be
qualified on a GPU with ``colab/PERSONA_MASTER01_GEN.ipynb``; until a real image and
its log exist, Gate B stays BLOCKED.

Requires the locked environment ``requirements-gpu.lock`` (Python 3.11) and a clone of
https://github.com/TencentARC/PhotoMaker on PYTHONPATH (record its commit SHA).
"""
from __future__ import annotations

import os
import platform
import time
from pathlib import Path

from ..pose import pose_map, VIEW_YAW
from .base import Backend, GenerationResult

BASE_MODEL = os.environ.get("PERSONA_BASE_MODEL", "SG161222/RealVisXL_V4.0")
PM_REPO, PM_FILE = "TencentARC/PhotoMaker-V2", "photomaker-v2.bin"
POSE_CONTROLNET = os.environ.get("PERSONA_POSE_CONTROLNET", "xinsir/controlnet-openpose-sdxl-1.0")

VIEW_PROMPTS = {
    "face": "head and shoulders portrait, looking straight at the camera, frontal view",
    "profil_gauche": "head and shoulders portrait, strict left side profile view, face turned 90 degrees to the left",
    "profil_droit": "head and shoulders portrait, strict right side profile view, face turned 90 degrees to the right",
    "trois_quarts_gauche": "head and shoulders portrait, three-quarter view facing left",
    "trois_quarts_droit": "head and shoulders portrait, three-quarter view facing right",
    "expression": "head and shoulders portrait, frontal view, broad natural smile",
    "pied_face": "full body shot, standing, neutral pose, facing the camera, feet and hands visible",
    "pied_profil": "full body shot, standing, neutral pose, side view, feet and hands visible",
    "pied_trois_quarts": "full body shot, standing, neutral pose, three-quarter view, feet and hands visible",
    "pied_dos": "full body shot, standing, neutral pose, seen from behind, back view",
    "pied_profil_oppose": "full body shot, standing, neutral pose, opposite side view, feet and hands visible",
}
STYLE = ("photograph, natural skin texture, soft studio lighting, plain light grey background, "
         "85mm lens, sharp focus, high detail")
NEGATIVE = ("cartoon, painting, illustration, 3d render, anime, deformed hands, extra fingers, missing fingers, "
            "extra limbs, distorted face, asymmetrical eyes, blurry, lowres, watermark, text, cropped feet, "
            "nsfw, nude")


class PhotoMakerV2Backend(Backend):
    name = "photomaker_v2"
    is_generation = True

    def __init__(self, steps: int = 40, guidance: float = 5.0, start_merge_step: int = 10,
                 cpu_offload: bool = True, face_size=(1024, 1024), body_size=(768, 1344),
                 pose_scale: float = 0.75):
        import torch  # noqa: F401  (fails fast outside the GPU env)
        self.steps, self.guidance, self.start_merge_step = steps, guidance, start_merge_step
        self.cpu_offload, self.face_size, self.body_size, self.pose_scale = cpu_offload, face_size, body_size, pose_scale
        self._pipe = None
        self._pipe_kind = None
        self._detector = None
        self.pm_commit = os.environ.get("PHOTOMAKER_COMMIT", "inconnu")

    # ------------------------------------------------------------ loading
    def _load_detector(self):
        if self._detector is None:
            from photomaker import FaceAnalysis2
            self._detector = FaceAnalysis2(providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
                                           allowed_modules=["detection", "recognition"])
            self._detector.prepare(ctx_id=0, det_size=(640, 640))
        return self._detector

    def _load_pipe(self, with_pose: bool):
        wanted = "pose" if with_pose else "plain"
        if self._pipe is not None and self._pipe_kind == wanted:
            return self._pipe
        import torch
        from huggingface_hub import hf_hub_download
        from diffusers import EulerDiscreteScheduler
        self.close()                                   # never two heavy pipelines on a 15 GB T4
        ckpt = hf_hub_download(repo_id=PM_REPO, filename=PM_FILE, repo_type="model")
        kw = dict(torch_dtype=torch.float16, use_safetensors=True, variant="fp16")
        if with_pose:
            from diffusers import ControlNetModel
            from photomaker import PhotoMakerStableDiffusionXLControlNetPipeline
            cn = ControlNetModel.from_pretrained(POSE_CONTROLNET, torch_dtype=torch.float16)
            pipe = PhotoMakerStableDiffusionXLControlNetPipeline.from_pretrained(BASE_MODEL, controlnet=cn, **kw)
        else:
            from photomaker import PhotoMakerStableDiffusionXLPipeline
            pipe = PhotoMakerStableDiffusionXLPipeline.from_pretrained(BASE_MODEL, **kw)
        pipe.load_photomaker_adapter(os.path.dirname(ckpt), subfolder="", weight_name=os.path.basename(ckpt),
                                     trigger_word="img", pm_version="v2")
        pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
        pipe.fuse_lora()
        if self.cpu_offload:
            pipe.enable_model_cpu_offload()
        else:
            pipe.to("cuda")
        pipe.enable_vae_tiling()
        self._pipe, self._pipe_kind, self._ckpt = pipe, wanted, ckpt
        return pipe

    def close(self) -> None:
        if self._pipe is not None:
            import gc
            import torch
            self._pipe = None
            gc.collect()
            torch.cuda.empty_cache()

    # --------------------------------------------------------- generation
    def _id_embeds(self, images):
        import numpy as np
        import torch
        from photomaker import analyze_faces
        det = self._load_detector()
        embeds, used = [], []
        for img in images:
            faces = analyze_faces(det, np.array(img)[:, :, ::-1])
            if faces:
                embeds.append(torch.from_numpy(faces[0]["embedding"]))
                used.append(img)
        if not embeds:
            raise RuntimeError("Aucun visage détecté dans les références sélectionnées.")
        return used, torch.stack(embeds)

    def generate(self, *, kind, view, references, seed, params, out_path: Path) -> GenerationResult:
        import torch
        from PIL import Image, ImageOps
        if not references:
            raise RuntimeError("Aucune référence autorisée fournie.")
        t0 = time.time()
        torch.cuda.reset_peak_memory_stats()
        refs = [ImageOps.exif_transpose(Image.open(p)).convert("RGB") for p in references[:4]]
        refs, id_embeds = self._id_embeds(refs)
        subject = params.get("subject_class", "person")          # "man" / "woman" / "person"
        appearance = params.get("appearance", "")                 # tenue, coiffure verrouillées
        prompt = f"a photo of a {subject} img, {VIEW_PROMPTS[view]}, {appearance}, {STYLE}".replace(", ,", ",")
        negative = params.get("negative_prompt", NEGATIVE)
        warnings = []
        with_pose = kind == "body" and view in VIEW_YAW and params.get("pose_control", True)
        w, h = self.face_size if kind == "face" else self.body_size
        w, h = int(params.get("width", w)), int(params.get("height", h))
        call = dict(prompt=prompt, negative_prompt=negative, input_id_images=refs, id_embeds=id_embeds,
                    num_images_per_prompt=1, num_inference_steps=int(params.get("steps", self.steps)),
                    guidance_scale=float(params.get("guidance", self.guidance)),
                    start_merge_step=int(params.get("start_merge_step", self.start_merge_step)),
                    generator=torch.Generator(device="cuda").manual_seed(seed), width=w, height=h)
        try:
            pipe = self._load_pipe(with_pose)
            if with_pose:
                call["image"] = pose_map(view, w, h)
                call["controlnet_conditioning_scale"] = float(params.get("pose_scale", self.pose_scale))
        except ImportError as exc:
            warnings.append(f"Contrôle de pose indisponible ({exc}); génération sans ControlNet.")
            pipe, with_pose = self._load_pipe(False), False
        image = pipe(**call).images[0]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(out_path, "PNG")
        if view == "pied_dos":
            warnings.append("Vue de dos : estimation du modèle, non documentée par les références.")
        if kind == "body":
            warnings.append("Le module d'identité est facial : morphologie du corps non garantie.")
        gpu = torch.cuda.get_device_name(0)
        return GenerationResult(
            path=out_path, engine=self.name, model=f"{BASE_MODEL} + {PM_REPO}/{PM_FILE}"
            + (f" + {POSE_CONTROLNET}" if with_pose else ""),
            model_version=f"photomaker@{self.pm_commit}", licence="voir MOTEUR_GPU.md (code Apache-2.0; poids: licences respectives)",
            is_generation=True, seed=seed, prompt=prompt, negative_prompt=negative,
            params={k: v for k, v in call.items() if k in ("num_inference_steps", "guidance_scale", "start_merge_step",
                                                         "width", "height", "controlnet_conditioning_scale")}
            | {"pose_control": with_pose, "n_references": len(refs), "cpu_offload": self.cpu_offload},
            duration_s=round(time.time() - t0, 2), peak_vram_mb=round(torch.cuda.max_memory_allocated() / 2**20, 1),
            hardware=f"{gpu} / {platform.python_version()} / torch {torch.__version__}", warnings=warnings)

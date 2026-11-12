"""Prompts par vue, partagés par tous les backends (PhotoMaker diffusers, stable-diffusion.cpp)."""

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

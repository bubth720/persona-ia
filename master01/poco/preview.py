"""Imprime une miniature JPEG en base64 dans le journal CI (relecture du rendu sans télécharger l'artefact)."""
import base64
import io
import sys

from PIL import Image

for path in sys.argv[1:]:
    im = Image.open(path).convert("RGB")
    im.thumbnail((560, 560))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=62)
    b = base64.b64encode(buf.getvalue()).decode()
    print(f"PREVIEW-BEGIN {path} {len(b)}")
    for i in range(0, len(b), 3000):
        print("PREVIEW " + b[i:i + 3000])
    print("PREVIEW-END")

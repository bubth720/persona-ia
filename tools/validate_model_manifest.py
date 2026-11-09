"""Offline-safe model manifest validation for PERSONA IA M4.

No network access, no model download, no modification of Android assets.
Run: python3 tools/validate_model_manifest.py path/to/manifest.json
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
MODEL_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/-]{1,127}$")
REQUIRED = ("id", "version", "source_url", "license", "sha256", "size_bytes", "runtime", "architecture")


def validate(data):
    errors = []
    if not isinstance(data, dict):
        return ["manifest must be a JSON object"]
    for key in REQUIRED:
        if key not in data:
            errors.append(f"missing {key}")
    if errors:
        return errors
    if not isinstance(data["id"], str) or not MODEL_ID.fullmatch(data["id"]) or ".." in data["id"]:
        errors.append("invalid id")
    for key in ("version", "license", "runtime"):
        if not isinstance(data[key], str) or not data[key].strip():
            errors.append(f"invalid {key}")
    url = data["source_url"]
    if not isinstance(url, str):
        errors.append("invalid source_url")
    else:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            errors.append("source_url must be a clean HTTPS URL")
    if not isinstance(data["sha256"], str) or not SHA256.fullmatch(data["sha256"]):
        errors.append("sha256 must contain 64 hex characters")
    if type(data["size_bytes"]) is not int or data["size_bytes"] <= 0:
        errors.append("size_bytes must be a positive integer")
    if data["architecture"] != "arm64-v8a":
        errors.append("architecture must be arm64-v8a")
    return errors


def verify_file(path, expected_hash, expected_size):
    file = Path(path)
    if not file.is_file() or file.stat().st_size != expected_size:
        return False
    digest = hashlib.sha256()
    with file.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().lower() == expected_hash.lower()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--verify-file", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        errors = validate(data)
        if errors:
            parser.exit(2, "\n".join(errors) + "\n")
        if args.verify_file and not verify_file(args.verify_file, data["sha256"], data["size_bytes"]):
            parser.exit(3, "file hash or size mismatch\n")
        print("VALID manifest" + (" and file" if args.verify_file else ""))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"validation error: {exc}\n")


if __name__ == "__main__":
    main()

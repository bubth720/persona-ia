import hashlib
import tempfile
import unittest
from pathlib import Path
from tools.validate_model_manifest import validate, verify_file


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "id": "example/model", "version": "1", "source_url": "https://example.org/model.bin",
            "license": "example-license", "sha256": "0" * 64, "size_bytes": 42,
            "runtime": "example-runtime", "architecture": "arm64-v8a"
        }

    def test_valid_structure(self):
        self.assertEqual(validate(self.manifest), [])

    def test_reject_http(self):
        self.manifest["source_url"] = "http://example.org/model"
        self.assertTrue(validate(self.manifest))

    def test_reject_boolean_size(self):
        self.manifest["size_bytes"] = True
        self.assertTrue(validate(self.manifest))

    def test_reject_bad_hash(self):
        self.manifest["sha256"] = "abc"
        self.assertTrue(validate(self.manifest))

    def test_verify_integrity(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "model.bin"
            file.write_bytes(b"test")
            self.assertTrue(verify_file(file, hashlib.sha256(b"test").hexdigest(), 4))
            self.assertFalse(verify_file(file, "0" * 64, 4))


if __name__ == "__main__":
    unittest.main()

import importlib.util
import os
import pathlib
import unittest
from unittest.mock import patch


ROOT = pathlib.Path(__file__).resolve().parents[1]
os.environ.setdefault("GITHUB_REPOSITORY", "xenomit-do/xenomit-deployments")
os.environ.setdefault("APP_TOKEN", "unit-test-token")
SPEC = importlib.util.spec_from_file_location(
    "promote_image", ROOT / "scripts" / "promote_image.py"
)
promote_image = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(promote_image)


class PromoteImageTests(unittest.TestCase):
    def test_kustomize_digest_update_preserves_other_fields(self):
        source = (ROOT / "apps" / "panel" / "kustomization.yaml").read_text()
        digest = "sha256:" + "a" * 64

        updated = promote_image.update_kustomize(source, digest)

        self.assertEqual(updated.count(digest), 1)
        self.assertIn("name: xenomit-web-panel", updated)
        self.assertIn("newName: ghcr.io/xenomit-do/xenomit-web-panel", updated)

    def test_botd_record_keeps_image_reference_contract(self):
        digest = "sha256:" + "b" * 64
        source_sha = "c" * 40

        updated = promote_image.update_botd_json("", digest, source_sha)

        self.assertIn(
            f'"image": "ghcr.io/xenomit-do/xenomit-botd@{digest}"', updated
        )
        self.assertIn(f'"sourceSha": "{source_sha}"', updated)
        self.assertNotIn('"digest":', updated)

    def test_invalid_digest_is_rejected_before_api_calls(self):
        env = {
            "PAYLOAD_IMAGE": "botd",
            "PAYLOAD_DIGEST": "latest",
            "PAYLOAD_SOURCE_REPOSITORY": "xenomit-do/xenomit-botd",
            "PAYLOAD_SOURCE_SHA": "c" * 40,
        }
        with patch.dict(os.environ, env):
            with self.assertRaises(SystemExit):
                promote_image.main()


if __name__ == "__main__":
    unittest.main()

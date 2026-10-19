"""Regression: cloud Hermes must not die when no TTY exists on Railway."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = (ROOT / "cloud/hermes-railway/Dockerfile").read_text(encoding="utf-8")


class HermesRailwayContainerTests(unittest.TestCase):
    def test_based_on_existing_versioned_hermes_runtime(self):
        self.assertIn("FROM nousresearch/hermes-agent:v2026.9.14", DOCKERFILE)
        self.assertNotIn(":latest", DOCKERFILE)

    def test_noninteractive_process_avoids_the_default_tui(self):
        self.assertIn('ENTRYPOINT ["/bin/sh", "-c", "exec sleep infinity"]', DOCKERFILE)
        self.assertIn("HEALTHCHECK NONE", DOCKERFILE)
        self.assertNotIn("hermes auth add", [line for line in DOCKERFILE.splitlines() if not line.lstrip().startswith("#")])
        self.assertNotIn("OPENAI_API_KEY", DOCKERFILE)

    def test_does_not_copy_auth_or_secrets_into_image(self):
        for forbidden in ("COPY ", "ADD ", "ENV OPENAI_", "EXPOSE ", "RUN hermes"):
            self.assertNotIn(forbidden, "\n".join(
                line for line in DOCKERFILE.splitlines() if not line.lstrip().startswith("#")
            ))


if __name__ == "__main__":
    unittest.main()

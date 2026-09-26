"""Local regression checks for GUI agent failures (no Claude account needed)."""

import io
import json
import os
import tempfile
import time
import unittest
from unittest import mock

from gui import server


class AgentFailureTests(unittest.TestCase):
    def test_agent_result_error_surfaces_instead_of_generic_missing_report(self):
        with tempfile.TemporaryDirectory() as root:
            skills = os.path.join(root, "skills")
            os.makedirs(skills)
            with open(os.path.join(skills, "SKILL.md"), "w", encoding="utf-8") as fh:
                fh.write("test skill")
            output = json.dumps({"type": "result", "is_error": True,
                                 "result": "Authentication failed. Run claude auth login."}) + "\n"

            class FakeProcess:
                stdout = io.StringIO(output)
                returncode = 1

                def wait(self):
                    return self.returncode

            meta = {"id": "test-agent", "url": "https://example.com/", "model": "sonnet",
                    "status": "running", "stage": "queued", "log": [], "_t0": time.time()}
            with mock.patch.object(server, "RUNS", root), mock.patch.object(
                    server, "popen", return_value=FakeProcess()):
                with self.assertRaisesRegex(RuntimeError, "Authentication failed"):
                    server.run_agent(meta, {"skills": skills}, "claude")
            self.assertTrue(any("Authentication failed" in line["text"]
                                for line in meta["log"]))


if __name__ == "__main__":
    unittest.main()

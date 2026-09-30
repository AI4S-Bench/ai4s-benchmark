"""Offline two-pass smoke test using the real SDK and locked runner dependencies."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ROOT = Path(__file__).resolve().parents[1]


class SDKTests(unittest.TestCase):
    def test_two_pass_runner_with_real_sdk(self):
        requests = []
        replies = [
            "## Problem Statement\nSynthetic physics task.\n"
            "## Scientific Domain\nDomain: Natural Sciences\nField: Physics\n"
            "## Final Analysis\nThe evaluation needs a stronger baseline.\n"
            "Decision: Uncertain\nDecision-Reason: Baseline missing.",
            "Author-Fit: Direct\nFit-Reason: Relevant physics background.\n"
            "COI: None\nCOI-Reason: No disclosure.",
        ]

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(request)
                response = {"id": "offline-review", "object": "chat.completion", "created": 1,
                            "model": request["model"], "choices": [{"index": 0,
                            "message": {"role": "assistant", "content": replies[len(requests) - 1]},
                            "finish_reason": "stop"}]}
                body = json.dumps(response).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                proposal = Path(directory) / "proposal.md"
                proposal.write_text("# Synthetic physics proposal\nMeasure a particle trajectory.\n"
                                    "## Author Information\nAuthor: Synthetic Author\n"
                                    "Relevant Experience: Physics research.\n", encoding="utf-8")
                environment = {key: value for key, value in os.environ.items()
                               if not any(part in key.upper() for part in ("KEY", "TOKEN", "SECRET"))}
                environment.update(OPENAI_API_KEY="offline-test-key",
                                   OPENAI_BASE_URL=f"http://127.0.0.1:{server.server_port}/v1",
                                   RUBRIC_MAX_TOKENS_PARAMETER="max_tokens",
                                   PYTHONUTF8="1", NO_PROXY="127.0.0.1,localhost")
                model = json.loads((ROOT / ".github/llm-config.json").read_text())["proposal_review"]["model"]
                completed = subprocess.run(
                    ["uv", "run", "--locked", "--script", str(ROOT / "ci_checks/rubric_review.py"),
                     "--model", f"openai/{model}", "--author-fit", str(proposal)],
                    cwd=ROOT, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=120,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                result = json.loads(completed.stdout)
                self.assertEqual(result["decision"], "Uncertain")
                self.assertEqual(result["author_fit"], "Direct")
                self.assertEqual(result["coi"], "None")
                self.assertEqual(len(requests), 2)
                for request in requests:
                    self.assertEqual(request["model"], model)
                    self.assertEqual(request["max_tokens"], 4096)
                    self.assertNotIn("tools", request)
                self.assertNotIn("Synthetic Author", requests[0]["messages"][1]["content"])
                self.assertIn("Synthetic Author", requests[1]["messages"][1]["content"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()

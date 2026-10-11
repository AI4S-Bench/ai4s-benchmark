"""The author-blind task review must not receive the portal's Contributor section."""
import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location("rubric_review", Path(__file__).with_name("rubric_review.py"))
rubric_review = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"anthropic": MagicMock(), "httpx": MagicMock()}):
    spec.loader.exec_module(rubric_review)

# Section layout of portal proposals (Discussions #1-#31, e.g. #31); synthetic values.
PORTAL_PROPOSAL = """# Inverse diffusion coefficient

## Scientific Domain

Applied Mathematics > Inverse Problems

## Scientific Problem
Infer a one-dimensional spatially varying diffusion coefficient from sparse, noisy temperature observations.

## Solvability
A regularized least-squares inversion can recover the held-out field with the provided solver.

## References & Resources
A. Tarantola, Inverse Problem Theory and Methods for Model Parameter Estimation, SIAM, 2005.

## Environment

### Software and tools
Python 3.12, NumPy, SciPy, and pytest in a pinned container image.

### Expected workflow & outputs
Write a CSV file with one coefficient value per grid cell.

## Evaluation

### How will this task be evaluated?
The verifier computes relative L2 error against the hidden coefficient.

### Is there risk of cheating and leakage?
The reference coefficient is kept outside the agent workspace.

## Contributor

Name: Ada Example
Institution / affiliation: Example Institute of Technology
GitHub: https://github.com/ada-example

## Task Metadata
Proposed task slug: `inverse-diffusion-coefficient`

---
Submitted via ai4sbench contribution form
"""
CONTRIBUTOR = ("## Contributor", "Ada Example", "Example Institute of Technology", "ada-example")


class AuthorBlindTests(unittest.TestCase):
    def test_strip_removes_portal_contributor_section(self):
        stripped = rubric_review.strip_author_info(PORTAL_PROPOSAL)
        for text in CONTRIBUTOR:
            self.assertNotIn(text, stripped)
        self.assertIn("### Is there risk of cheating and leakage?", stripped)
        self.assertIn("## Task Metadata\nProposed task slug: `inverse-diffusion-coefficient`", stripped)

    def test_task_review_prompt_has_no_contributor(self):
        review = "## Final Analysis\nSound.\n\n**Decision-Reason:** Sound.\n**Decision:** Accept\n"
        with tempfile.TemporaryDirectory() as directory:
            proposal = Path(directory) / "proposal.md"
            proposal.write_text(PORTAL_PROPOSAL, encoding="utf-8")
            with (patch.object(sys, "argv", ["rubric_review.py", str(proposal)]),
                  patch.object(rubric_review, "call_llm", return_value=review) as call_llm,
                  redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO())):
                rubric_review.main()
        self.assertEqual(call_llm.call_count, 1)
        prompt = call_llm.call_args.args[1]
        for text in CONTRIBUTOR:
            self.assertNotIn(text, prompt)
        self.assertIn("Infer a one-dimensional spatially varying diffusion coefficient", prompt)


if __name__ == "__main__":
    unittest.main()

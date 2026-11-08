"""extract_decision() must return the final Decision line, as rubrics/task-proposal.md requires."""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location("rubric_review", Path(__file__).with_name("rubric_review.py"))
rubric_review = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"anthropic": MagicMock(), "httpx": MagicMock()}):
    spec.loader.exec_module(rubric_review)


class ReviewDecisionTests(unittest.TestCase):
    def test_final_decision_line_wins_over_per_criterion_lines(self):
        review = ("## Verifiable\nThe verifier is exact.\n**Decision:** Reject\n\n"
                  "## Final Analysis\nOn balance the task is sound.\n\n"
                  "**Decision-Reason:** Sound task.\n**Decision:** Accept\n")
        self.assertEqual(rubric_review.extract_decision(review), "Accept")


if __name__ == "__main__":
    unittest.main()

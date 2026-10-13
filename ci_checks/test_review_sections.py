"""Section extraction must stop before the rubric's Decision-Reason / Decision lines."""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location("rubric_review", Path(__file__).with_name("rubric_review.py"))
rubric_review = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"anthropic": MagicMock(), "httpx": MagicMock()}):
    spec.loader.exec_module(rubric_review)

ANALYSIS = "The task proposal satisfies all seven criteria. There is a direct path to acceptance."
# Tail of the AI review published on Discussion #31, in the rubric template's format.
BOLD_REVIEW = f"""## Outcome-Verified
**Negative aspects:** None.
**Judgement:** Strong Accept

## Final Analysis
{ANALYSIS}

**Decision-Reason:** The task is a well-posed, verifiable inverse problem.
**Decision:** Strong Accept
"""


class ReviewSectionTests(unittest.TestCase):
    def test_justification_excludes_decision_lines(self):
        plain = BOLD_REVIEW.replace("**", "")
        for review in (BOLD_REVIEW, plain):
            with self.subTest(bold=review is BOLD_REVIEW):
                self.assertEqual(rubric_review.extract_justification(review), ANALYSIS)
                self.assertEqual(rubric_review._extract_labeled_line(review, "Decision-Reason"),
                                 "The task is a well-posed, verifiable inverse problem.")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch
import urllib.error

from jevscout.scoring.models import (
    ChoiceAnswer,
    NoulAnswer,
    ScoreAnswer,
)
from jevscout.scoring.client import LocalHeuristicDecisionClient, OpenRouterDecisionClient


class DecisionClientTests(unittest.TestCase):
    def test_missing_api_key_raises_value_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                OpenRouterDecisionClient(api_key=None)

    def test_evaluate_parses_noul_choice_and_score_answers(self):
        client = OpenRouterDecisionClient(
            api_key="sk-or-test-key",
            model="respan/span-01-lite:free",
        )

        mock_response_body = {
            "model": "respan/span-01-lite:free",
            "answers": {
                "is_remote_eligible": {
                    "type": "noul",
                    "noul": 0.85,
                },
                "seniority": {
                    "type": "choice",
                    "choice": "mid_level",
                    "probabilities": {
                        "junior": 0.1,
                        "mid_level": 0.8,
                        "senior": 0.1,
                    },
                },
                "skill_fit": {
                    "type": "score",
                    "score": 2.0,
                    "probabilities": [0.05, 0.25, 0.70],
                },
            },
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_response_body).encode("utf-8")
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            questions = {
                "is_remote_eligible": {
                    "type": "noul",
                    "instructions": "Is this job remote eligible in India?",
                    "criteria": {"true": "Remote in India", "false": "Onsite only"},
                }
            }
            answers = client.evaluate(
                state={"job": "Python Engineer", "profile": "Backend Developer"},
                questions=questions,
            )

            # Check HTTP call was made properly
            self.assertEqual(mock_urlopen.call_count, 1)
            req = mock_urlopen.call_args[0][0]
            self.assertEqual(req.full_url, "https://openrouter.ai/api/alpha/decisions")
            self.assertEqual(req.headers["Authorization"], "Bearer sk-or-test-key")
            self.assertEqual(req.headers["Content-type"], "application/json")
            
            body = json.loads(req.data.decode("utf-8"))
            self.assertEqual(body["model"], "respan/span-01-lite:free")
            self.assertEqual(body["questions"], questions)

            # Verify typed answers
            self.assertEqual(answers["is_remote_eligible"], NoulAnswer(type="noul", noul=0.85))
            self.assertEqual(
                answers["seniority"],
                ChoiceAnswer(
                    type="choice",
                    choice="mid_level",
                    probabilities={"junior": 0.1, "mid_level": 0.8, "senior": 0.1},
                ),
            )
            self.assertEqual(
                answers["skill_fit"],
                ScoreAnswer(
                    type="score",
                    score=2.0,
                    probabilities=[0.05, 0.25, 0.70],
                ),
            )

    def test_evaluate_handles_http_errors_gracefully(self):
        client = OpenRouterDecisionClient(api_key="sk-test")
        
        mock_http_error = urllib.error.HTTPError(
            url="https://openrouter.ai/api/alpha/decisions",
            code=402,
            msg="Payment Required",
            hdrs=MagicMock(),
            fp=MagicMock(read=lambda: b'{"error": {"message": "Insufficient credits"}}'),
        )

        with patch("urllib.request.urlopen", side_effect=mock_http_error):
            with self.assertRaises(RuntimeError) as ctx:
                client.evaluate(state="sample", questions={})
            self.assertIn("402", str(ctx.exception))
            self.assertIn("Insufficient credits", str(ctx.exception))

    def test_local_heuristic_decision_client_scores_offline(self):
        client = LocalHeuristicDecisionClient()
        state = {
            "candidate": {
                "role_target": "Senior Backend Developer",
                "primary_skills": ["Python", "FastAPI", "PostgreSQL"],
                "experience_years": 4.0,
                "preferred_locations": ["Bengaluru"],
                "remote_only": False,
            },
            "job": {
                "title": "Senior Python Backend Engineer",
                "location": "Bengaluru, India",
                "company": "TechCorp",
                "description_summary": "Looking for a Python and FastAPI engineer with PostgreSQL experience.",
            },
        }
        questions = {
            "location_compatibility": {"type": "noul"},
            "seniority_fit": {"type": "choice"},
            "stack_alignment": {"type": "score"},
        }
        answers = client.evaluate(state, questions)

        self.assertIn("location_compatibility", answers)
        self.assertIsInstance(answers["location_compatibility"], NoulAnswer)
        self.assertGreaterEqual(answers["location_compatibility"].noul, 0.8)

        self.assertIn("seniority_fit", answers)
        self.assertIsInstance(answers["seniority_fit"], ChoiceAnswer)
        self.assertEqual(answers["seniority_fit"].choice, "matched")

        self.assertIn("stack_alignment", answers)
        self.assertIsInstance(answers["stack_alignment"], ScoreAnswer)
        self.assertEqual(answers["stack_alignment"].score, 2.0)


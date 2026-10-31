import unittest
from jevscout.application.classification import classify_job
from jevscout.modules.jobs.scoring.models import NoulAnswer

class FakeDecisionClient:
    model = 'fixture'
    def evaluate(self, state, questions):
        assert isinstance(state, str)
        assert 'FastAPI' in state
        return {name: NoulAnswer(type='noul', noul=0.7) for name in questions}

class ClassificationTests(unittest.TestCase):
    def test_includes_user_context_and_exposes_separate_dimensions(self):
        result = classify_job({'title':'Backend Engineer','description':'Build AI APIs'}, {'freeform_context':'FastAPI experience and AI goal'}, FakeDecisionClient())
        self.assertEqual(result['model'], 'fixture')
        self.assertEqual(result['dimensions']['career_direction'], 0.7)
        self.assertEqual(result['dimensions']['qualification'], 0.7)
        self.assertNotIn('FastAPI experience', str(result))

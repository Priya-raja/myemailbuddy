"""Offline scope evaluation using fictional fixtures; makes zero provider calls."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from safety.scope import classify_scope

cases = json.loads((Path(__file__).resolve().parents[1] / 'tests/fixtures/scope_cases.json').read_text())
results = [(case['expected'], classify_scope(case['text'])['decision']) for case in cases]
print(json.dumps({
    'fictional_cases': len(results),
    'correct_decisions': sum(expected == actual for expected, actual in results),
    'false_rejections': sum(expected == 'allow' and actual == 'reject' for expected, actual in results),
    'false_clarifications': sum(expected == 'allow' and actual == 'clarify' for expected, actual in results),
    'missed_rejections': sum(expected == 'reject' and actual != 'reject' for expected, actual in results),
    'avoided_generation_requests': sum(actual != 'allow' for _, actual in results),
    'classification_model_calls': 0,
    'classification_tokens': 0,
    'note': 'Actual generation tokens saved require a measured baseline; request counts are not token estimates.',
}, indent=2))

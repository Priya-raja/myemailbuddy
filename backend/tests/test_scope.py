import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from langchain_core.outputs import LLMResult
import main
from safety.scope import classify_scope, OUTSIDE_SCOPE, CLARIFICATION
from safety.telemetry import record_scope, UsageTrace
from safety.limits import _buckets

CASES = json.loads((Path(__file__).parent / 'fixtures/scope_cases.json').read_text())

class ScopeTests(unittest.TestCase):
    def setUp(self):
        _buckets.clear()
        self.client = TestClient(main.app)

    def test_fictional_false_rejection_corpus(self):
        for case in CASES:
            with self.subTest(text=case['text']):
                self.assertEqual(classify_scope(case['text'])['decision'], case['expected'])

    def test_reject_and_clarify_never_call_model_or_spend_quota(self):
        for endpoint in ['/api/draft', '/api/improve', '/api/translate', '/api/workflow/run']:
            for text, status, message in [
                ('Research this topic and email me the findings', 'outside_scope', OUTSIDE_SCOPE),
                ('Improve this.', 'needs_details', CLARIFICATION),
            ]:
                with self.subTest(endpoint=endpoint, text=text), patch.object(main, 'build_draft_chain') as chain, patch.object(main.ChatGroq, 'bind') as bind, patch.object(main, 'enforce_quota') as quota:
                    result = self.client.post(endpoint, json={'text': text, 'language': 'ta-IN', 'thread_id': 'fictional'})
                    self.assertEqual(result.status_code, 422)
                    self.assertEqual(result.json()['detail']['status'], status)
                    self.assertEqual(result.json()['detail']['message'], message)
                    chain.assert_not_called(); bind.assert_not_called(); quota.assert_not_called()

    def test_improve_route_accepts_existing_draft_without_writing_keywords(self):
        chain = AsyncMock()
        chain.ainvoke.return_value = {'subject': 'Arrival', 'body': 'I will arrive tomorrow morning.', 'translation': 'நாளை காலை வருவேன்.'}
        with patch.dict(main.os.environ, {'GROQ_API_KEY': 'test'}), patch.object(main, 'build_draft_chain', return_value=chain):
            result = self.client.post('/api/improve', json={'text': 'I will arrive tomorrow morning.'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(chain.ainvoke.await_args.args[0]['mode'], 'improve')

    def test_guided_purpose_is_not_a_research_bypass(self):
        self.assertEqual(classify_scope('Naalaiku leave venum.', purpose='leave')['decision'], 'allow')
        self.assertEqual(classify_scope('I need tomorrow off.', purpose='leave')['decision'], 'allow')
        self.assertEqual(classify_scope('Research this and email me', purpose='status_update')['decision'], 'reject')

    def test_quota_prevents_second_model_call(self):
        chain = AsyncMock()
        chain.ainvoke.return_value = {'subject': 'Update', 'body': 'The installation is complete.', 'translation': 'முடிந்தது.'}
        with patch.dict(main.os.environ, {'GROQ_API_KEY':'test', 'WRITING_REQUESTS_PER_HOUR':'1'}), patch.object(main, 'build_draft_chain', return_value=chain):
            self.assertEqual(self.client.post('/api/draft', json={'text':'The installation is complete.'}).status_code, 200)
            self.assertEqual(self.client.post('/api/draft', json={'text':'The installation is complete.'}).status_code, 429)
        chain.ainvoke.assert_awaited_once()

    def test_trace_fields_exclude_text_and_identifiers(self):
        with self.assertLogs('emailbuddy.scope', level='INFO') as logs:
            record_scope('reject', 'ta-IN', reason='research_or_qa')
            UsageTrace('ar').on_llm_end(LLMResult(generations=[], llm_output={'token_usage': {'prompt_tokens': 12, 'completion_tokens': 8, 'total_tokens': 20}, 'private_prompt':'DO NOT LOG'}))
        first = json.loads(logs.records[0].message)
        second = json.loads(logs.records[1].message)
        self.assertEqual(set(first), {'scope_decision','language','token_usage','rejection_reason_category'})
        self.assertEqual(first['token_usage']['total_tokens'], 0)
        self.assertEqual(second['token_usage']['total_tokens'], 20)
        self.assertNotIn('DO NOT LOG', str(logs.output))

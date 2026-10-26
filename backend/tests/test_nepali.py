import json
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
import main
from safety.limits import _buckets

class NepaliTests(unittest.TestCase):
    def setUp(self):
        _buckets.clear()
        self.client=TestClient(main.app)

    def test_native_nepali_draft_and_improve_accept_language_and_preserve_input(self):
        text='मलाई भोलि व्यक्तिगत कामको लागि एक दिन बिदा चाहिन्छ। म्यानेजरलाई इमेल लेखिदिनुहोस्।'
        chain=AsyncMock()
        chain.ainvoke.return_value={'subject':'Leave request','body':'Dear [Name],\n\nI would like to request one day of leave tomorrow for personal work.\n\nThank you.', 'translation':'व्यक्तिगत कामको लागि भोलि एक दिन बिदा चाहिन्छ।'}
        with patch.dict(main.os.environ,{'GROQ_API_KEY':'test'}), patch.object(main,'build_draft_chain',return_value=chain) as build:
            for route in ['/api/draft','/api/improve']:
                result=self.client.post(route,json={'text':text,'language':'ne-IN'})
                self.assertEqual(result.status_code,200)
                self.assertEqual(result.json()['translation'],chain.ainvoke.return_value['translation'])
        self.assertEqual(build.call_args.args[-1],'ne-IN')
        self.assertEqual(chain.ainvoke.await_args.args[0]['text'],text)

    def test_translation_prompt_requests_nepali(self):
        def translate(prompt):
            self.assertIn('Nepali native script',prompt.to_messages()[0].content)
            return AIMessage(content=json.dumps({'translation':'म भोलि बिदा लिन चाहन्छु।'}))
        with patch.object(main.ChatGroq,'bind',return_value=RunnableLambda(translate)):
            result=self.client.post('/api/translate',json={'text':'I would like to request leave tomorrow.','language':'ne-IN'})
        self.assertEqual(result.status_code,200)
        self.assertIn('बिदा',result.json()['translation'])

    def test_nepali_recording_uses_sarvam_code_and_codemix(self):
        response=unittest.mock.Mock()
        response.json.return_value={'transcript':'मलाई भोलि बिदा चाहिन्छ।'}
        client=AsyncMock();client.post.return_value=response
        context=AsyncMock();context.__aenter__.return_value=client
        with patch.dict(main.os.environ,{'SARVAM_API_KEY':'test'}), patch.object(main.httpx,'AsyncClient',return_value=context):
            result=self.client.post('/api/transcribe',data={'language':'ne-IN'},files={'audio':('clip.wav',b'audio','audio/wav')})
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['transcript'],'मलाई भोलि बिदा चाहिन्छ।')
        self.assertEqual(client.post.call_args.args[0],'https://api.sarvam.ai/speech-to-text')
        self.assertEqual(client.post.call_args.kwargs['data'],{'model':'saaras:v3','mode':'codemix','language_code':'ne-IN'})

    def test_nepali_qa_is_rejected_before_quota_or_model(self):
        with patch.object(main,'enforce_daily_quota',new_callable=AsyncMock) as quota, patch.object(main,'build_draft_chain') as model:
            result=self.client.post('/api/draft',json={'text':'कृपया व्याख्या गर्नुहोस्: गुरुत्वाकर्षण।','language':'ne-IN'})
        self.assertEqual(result.status_code,422)
        quota.assert_not_called();model.assert_not_called()

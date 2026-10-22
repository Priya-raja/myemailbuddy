import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import main

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_invalid_choices_and_empty_text(self):
        for payload in ({'text': 'hi', 'language': 'fr'}, {'text': 'hi', 'tone': 'rude'}, {'text': '   '}):
            self.assertEqual(self.client.post('/api/draft', json=payload).status_code, 422)

    def test_draft_passes_selected_context_and_validates_result(self):
        chain = AsyncMock()
        chain.ainvoke.return_value = {'subject': '', 'body': 'Can we meet tomorrow?', 'translation': 'هل يمكننا اللقاء غدًا؟'}
        with patch.dict(main.os.environ, {'GROQ_API_KEY': 'test'}), patch.object(main, 'build_draft_chain', return_value=chain) as build:
            result = self.client.post('/api/draft', json={'text': 'أريد اجتماع مع زميلي غدا', 'language': 'ar', 'persona': 'colleague', 'target': 'whatsapp', 'tone': 'friendly'})
        self.assertEqual(result.status_code, 200)
        build.assert_called_once_with('colleague', 'whatsapp', 'friendly', 'ar')
        self.assertTrue(result.json()['translation'])

    def test_invalid_provider_result_is_not_returned(self):
        chain = AsyncMock()
        chain.ainvoke.return_value = {'body': 'Hi'}
        with patch.dict(main.os.environ, {'GROQ_API_KEY': 'test'}), patch.object(main, 'build_draft_chain', return_value=chain):
            self.assertEqual(self.client.post('/api/draft', json={'text': 'Ask my manager for leave'}).status_code, 502)

    def test_arabic_speech_uses_groq(self):
        response = unittest.mock.Mock()
        response.json.return_value = {'text': 'مرحبا'}
        client = AsyncMock()
        client.post.return_value = response
        context = AsyncMock()
        context.__aenter__.return_value = client
        with patch.dict(main.os.environ, {'GROQ_API_KEY': 'test'}), patch.object(main.httpx, 'AsyncClient', return_value=context):
            result = self.client.post('/api/transcribe', data={'language': 'ar'}, files={'audio': ('clip.webm', b'audio', 'audio/webm')})
        self.assertEqual(result.json(), {'transcript': 'مرحبا'})
        self.assertEqual(client.post.call_args.args[0], 'https://api.groq.com/openai/v1/audio/transcriptions')

    def test_indic_speech_uses_sarvam(self):
        response = unittest.mock.Mock()
        response.json.return_value = {'transcript': 'வணக்கம்'}
        client = AsyncMock()
        client.post.return_value = response
        context = AsyncMock()
        context.__aenter__.return_value = client
        with patch.dict(main.os.environ, {'SARVAM_API_KEY': 'test'}), patch.object(main.httpx, 'AsyncClient', return_value=context):
            result = self.client.post('/api/transcribe', data={'language': 'ta-IN'}, files={'audio': ('clip.webm', b'audio', 'audio/webm')})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(client.post.call_args.kwargs['data']['mode'], 'codemix')

    def test_speech_provider_errors_are_actionable(self):
        import httpx
        for status, expected in [(403, "credentials"), (429, "quota"), (422, "short message"), (500, "temporarily unavailable")]:
            response = httpx.Response(status, request=httpx.Request("POST", "https://api.sarvam.ai/speech-to-text"))
            client = AsyncMock()
            client.post.return_value = response
            context = AsyncMock()
            context.__aenter__.return_value = client
            with patch.dict(main.os.environ, {"SARVAM_API_KEY": "test"}), patch.object(main.httpx, "AsyncClient", return_value=context):
                result = self.client.post('/api/transcribe', data={'language': 'ta-IN'}, files={'audio': ('clip.wav', b'audio', 'audio/wav')})
            self.assertIn(expected, result.json()['detail'])

    def test_empty_transcription_is_reported(self):
        response = unittest.mock.Mock()
        response.json.return_value = {'transcript': ''}
        client = AsyncMock()
        client.post.return_value = response
        context = AsyncMock()
        context.__aenter__.return_value = client
        with patch.dict(main.os.environ, {"SARVAM_API_KEY": "test"}), patch.object(main.httpx, "AsyncClient", return_value=context):
            result = self.client.post('/api/transcribe', data={'language': 'ta-IN'}, files={'audio': ('clip.wav', b'audio', 'audio/wav')})
        self.assertEqual(result.status_code, 422)
        self.assertIn('No speech', result.json()['detail'])

    def test_missing_groq_model_has_configuration_error(self):
        import httpx
        from groq import NotFoundError
        response = httpx.Response(404, request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"))
        chain = AsyncMock()
        chain.ainvoke.side_effect = NotFoundError("model not found", response=response, body={})
        with patch.dict(main.os.environ, {"GROQ_API_KEY": "test"}), patch.object(main, "build_draft_chain", return_value=chain):
            result = self.client.post('/api/draft', json={'text': 'Ask my manager for leave'})
        self.assertEqual(result.status_code, 503)
        self.assertIn('GROQ_MODEL', result.json()['detail'])

    def test_draft_requests_json_mode(self):
        with patch.object(main.ChatGroq, 'bind', return_value=main.llm) as bind:
            main.build_draft_chain('manager', 'email')
        bind.assert_called_once_with(response_format={"type": "json_object"})

    def test_polite_email_gets_subject_when_model_omits_it(self):
        chain = AsyncMock()
        chain.ainvoke.return_value = {'body': 'Dear Manager,\n\nThe software installation is complete. It is ready to use.', 'translation': 'நிறுவல் முடிந்தது.'}
        with patch.dict(main.os.environ, {'GROQ_API_KEY': 'test'}), patch.object(main, 'build_draft_chain', return_value=chain):
            result = self.client.post('/api/draft', json={'text': 'The installation is complete', 'target': 'email', 'tone': 'polite'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['subject'], 'The software installation is complete')
        chain.ainvoke.assert_awaited_once()

    def test_subject_is_preserved_for_email_and_removed_for_whatsapp(self):
        payload = {'subject': '  Installation complete  ', 'body': 'It is complete.', 'translation': 'முடிந்தது.'}
        self.assertEqual(main.normalize_draft(payload, 'email').subject, 'Installation complete')
        self.assertEqual(main.normalize_draft(payload, 'whatsapp').subject, '')

    def test_truncated_model_output_is_not_returned_as_partial_draft(self):
        from langchain_core.messages import AIMessage
        from fastapi import HTTPException
        truncated = AIMessage(content='{"subject":"Meeting", "body":"Can we meet', response_metadata={'finish_reason': 'length'})
        with self.assertRaises(HTTPException) as caught:
            main.require_complete_output(truncated)
        self.assertEqual(caught.exception.detail['code'], 'response_limit')
        complete = AIMessage(content='{}', response_metadata={'finish_reason': 'stop'})
        self.assertIs(main.require_complete_output(complete), complete)

if __name__ == '__main__':
    unittest.main()

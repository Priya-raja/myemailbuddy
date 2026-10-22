import asyncio
import io
import json
import unittest
import wave
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from langchain_core.outputs import LLMResult
import main
from safety import usage
from safety.telemetry import UsageTrace

DEVICE = '12345678-1234-4234-8234-123456789abc'

class UsageTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(main.os.environ, {'APP_ENV':'production', 'PILOT_ACCESS_REQUIRED':'false', 'GROQ_API_KEY':'test', 'UPSTASH_REDIS_REST_URL':'https://example.invalid','UPSTASH_REDIS_REST_TOKEN':'test'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = TestClient(main.app)

    def test_request_identity_tokens_and_name_are_aggregated_without_content(self):
        async def generate(*args, **kwargs):
            UsageTrace('ta-IN').on_llm_end(LLMResult(generations=[], llm_output={'token_usage': {'prompt_tokens':21,'completion_tokens':10,'total_tokens':31}}))
            return {'subject':'Status','body':'Dear Manager, done. Thank you','translation':'முடிந்தது'}
        chain = AsyncMock()
        chain.ainvoke.side_effect = generate
        with patch('safety.pilot.redis_command', new_callable=AsyncMock,return_value=1), patch.object(usage,'redis_command',new_callable=AsyncMock,return_value=1) as store, patch.object(main,'build_draft_chain',return_value=chain):
            result = self.client.post('/api/draft',headers={'X-Device-ID':DEVICE,'X-Usage-Name':'Priya%0A%3Ctest%3E'}, json={'text':'The installation is complete.'})
        self.assertEqual(result.status_code,200)
        command = store.await_args.args[0]
        self.assertTrue(command[4].startswith('device-'))
        self.assertNotIn(DEVICE,str(command))
        self.assertEqual(command[5],'Priyatest')
        counts=dict(zip(command[6::2],command[7::2]))
        self.assertEqual(counts['admitted'],1)
        self.assertEqual(counts['successes'],1)
        self.assertEqual(counts['total_tokens'],31)
        self.assertEqual(counts['token_reports'],1)
        self.assertNotIn('installation',str(command))
        self.assertIsNone(usage.current_usage.get())

    def test_scope_rejection_records_zero_admission_and_no_tokens(self):
        with patch.object(usage,'redis_command',new_callable=AsyncMock,return_value=1) as store, patch.object(main,'build_draft_chain') as chain:
            result=self.client.post('/api/draft',json={'text':'Explain gravity.'})
        self.assertEqual(result.status_code,422)
        command=store.await_args.args[0]
        self.assertEqual(command[4],'unattributed')
        counts=dict(zip(command[6::2],command[7::2]))
        self.assertEqual(counts['admitted'],0)
        self.assertEqual(counts['blocked'],1)
        self.assertEqual(counts['token_reports'],0)
        chain.assert_not_called()

    def test_reporting_failure_does_not_hide_completed_draft(self):
        chain=AsyncMock()
        chain.ainvoke.return_value={'subject':'Update','body':'Done','translation':'முடிந்தது'}
        with patch('safety.pilot.redis_command',new_callable=AsyncMock,return_value=1), patch.object(usage,'redis_command',new_callable=AsyncMock,side_effect=RuntimeError('unavailable')), patch.object(main,'build_draft_chain',return_value=chain):
            self.assertEqual(self.client.post('/api/draft',json={'text':'The installation is complete.'}).status_code,200)

    def test_duration_is_measured_from_wav(self):
        audio=io.BytesIO()
        with wave.open(audio,'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(b'\0'*32000)
        token=usage.current_usage.set({})
        try:
            usage.add_audio_duration(audio.getvalue())
            self.assertEqual(usage.current_usage.get()['audio_ms'],1000)
            self.assertEqual(usage.current_usage.get()['audio_duration_reports'],1)
        finally:
            usage.current_usage.reset(token)

    def test_concurrent_request_usage_does_not_mix(self):
        async def one(count):
            token=usage.current_usage.set({})
            try:
                await asyncio.sleep(0)
                usage.add_tokens({'total_tokens':count})
                return usage.current_usage.get()['total_tokens']
            finally:
                usage.current_usage.reset(token)
        async def run():
            return await asyncio.gather(one(7),one(19))
        self.assertEqual(asyncio.run(run()),[7,19])

    def test_native_script_names_keep_combining_vowels(self):
        from starlette.requests import Request
        from urllib.parse import quote
        request=Request({'type':'http','path':'/api/draft','headers':[(b'x-device-id',DEVICE.encode()),(b'x-usage-name',quote('பிரியா').encode())]})
        token=usage.start_usage(request)
        try:
            self.assertEqual(usage.current_usage.get()['name'],'பிரியா')
        finally:
            usage.current_usage.reset(token)

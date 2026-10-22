import hashlib
import json
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import main
from safety import pilot

class PilotTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_production_blocks_anonymous_access_and_legacy_sending(self):
        with patch.dict(main.os.environ, {'APP_ENV':'production','PILOT_ACCESS_REQUIRED':'true'}):
            self.assertEqual(self.client.post('/api/draft',json={'text':'The installation is complete.'}).status_code,401)
            self.assertEqual(self.client.post('/api/send-email',json={}).status_code,404)
            self.assertEqual(self.client.post('/api/workflow/run',json={}).status_code,404)

    def test_invite_is_checked_in_external_store_without_saving_raw_code(self):
        code='fictional-pilot-code-for-tests'
        with patch.dict(main.os.environ, {'APP_ENV':'production','PILOT_ACCESS_REQUIRED':'true'}), patch.object(pilot,'redis_command',new_callable=AsyncMock) as store:
            store.return_value=json.dumps({'active':True,'daily_limit':5})
            result=self.client.post('/api/access',headers={'Authorization':'Bearer '+code})
        self.assertEqual(result.status_code,200)
        self.assertEqual(store.await_args.args[0],['GET','buddy:invite:'+hashlib.sha256(code.encode()).hexdigest()])

    def test_revoked_invite_is_rejected(self):
        with patch.dict(main.os.environ, {'APP_ENV':'production','PILOT_ACCESS_REQUIRED':'true'}), patch.object(pilot,'redis_command',new_callable=AsyncMock,return_value=None):
            self.assertEqual(self.client.post('/api/access',headers={'Authorization':'Bearer fictional-pilot-code'}).status_code,401)

    def test_daily_quota_exhaustion_prevents_model_call(self):
        with patch.dict(main.os.environ, {'APP_ENV':'production','PILOT_ACCESS_REQUIRED':'true'}), patch.object(pilot,'redis_command',new_callable=AsyncMock) as store, patch.object(main,'build_draft_chain') as chain:
            store.side_effect=[json.dumps({'active':True,'daily_limit':1}),0]
            result=self.client.post('/api/draft',headers={'Authorization':'Bearer fictional-pilot-code'},json={'text':'The installation is complete.'})
        self.assertEqual(result.status_code,429)
        chain.assert_not_called()
        self.assertEqual(store.await_args.args[0][0],'EVAL')

    def test_public_access_needs_no_invite(self):
        with patch.dict(main.os.environ, {'APP_ENV':'production','PILOT_ACCESS_REQUIRED':'false'}), patch.object(pilot,'redis_command',new_callable=AsyncMock) as store:
            self.assertEqual(self.client.post('/api/access').status_code, 200)
            store.assert_not_called()
            self.assertEqual(self.client.post('/api/send-email',json={}).status_code,404)
            self.assertEqual(self.client.post('/api/workflow/run',json={}).status_code,404)

    def test_public_draft_succeeds_without_token_and_uses_shared_quota(self):
        chain = AsyncMock()
        chain.ainvoke.return_value = {'subject':'Update','body':'The installation is complete.','translation':'நிறுவல் முடிந்தது.'}
        with patch.dict(main.os.environ, {'APP_ENV':'production','PILOT_ACCESS_REQUIRED':'false','PUBLIC_REQUESTS_PER_DAY':'100','GROQ_API_KEY':'test'}), patch.object(pilot,'redis_command',new_callable=AsyncMock,return_value=1) as store, patch.object(main,'build_draft_chain',return_value=chain):
            result=self.client.post('/api/draft',json={'text':'The installation is complete.'})
        self.assertEqual(result.status_code,200)
        command=store.await_args.args[0]
        self.assertEqual(command[0],'EVAL')
        self.assertTrue(command[3].startswith('buddy:quota:public:'))
        self.assertEqual(command[4],100)
        chain.ainvoke.assert_awaited_once()

    def test_public_quota_exhaustion_blocks_before_model(self):
        with patch.dict(main.os.environ, {'APP_ENV':'production','PILOT_ACCESS_REQUIRED':'false'}), patch.object(pilot,'redis_command',new_callable=AsyncMock,return_value=0), patch.object(main,'build_draft_chain') as chain:
            result=self.client.post('/api/draft',json={'text':'The installation is complete.'})
        self.assertEqual(result.status_code,429)
        self.assertIn('Retry-After',result.headers)
        chain.assert_not_called()

    def test_public_production_fails_closed_without_store(self):
        with patch.dict(main.os.environ, {'APP_ENV':'production','PILOT_ACCESS_REQUIRED':'false','UPSTASH_REDIS_REST_URL':'','UPSTASH_REDIS_REST_TOKEN':''}), patch.object(main,'build_draft_chain') as chain:
            self.assertEqual(self.client.get('/health').status_code,503)
            result=self.client.post('/api/draft',json={'text':'The installation is complete.'})
            self.assertEqual(result.status_code,503)
            chain.assert_not_called()

    def test_public_ready_health_reports_no_access_requirement(self):
        with patch.dict(main.os.environ, {'APP_ENV':'production','PILOT_ACCESS_REQUIRED':'false','UPSTASH_REDIS_REST_URL':'https://example.invalid','UPSTASH_REDIS_REST_TOKEN':'test'}):
            result=self.client.get('/health')
        self.assertEqual(result.status_code,200)
        self.assertFalse(result.json()['access_required'])

    def test_public_invalid_budget_fails_closed(self):
        for limit in ['0','-1','oops','10001']:
            with self.subTest(limit=limit), patch.dict(main.os.environ, {'APP_ENV':'production','PILOT_ACCESS_REQUIRED':'false','PUBLIC_REQUESTS_PER_DAY':limit}), patch.object(pilot,'redis_command',new_callable=AsyncMock) as store, patch.object(main,'build_draft_chain') as chain:
                result=self.client.post('/api/draft',json={'text':'The installation is complete.'})
                self.assertEqual(result.status_code,503)
                store.assert_not_called()
                chain.assert_not_called()

    def test_health_does_not_call_any_provider(self):
        with patch.dict(main.os.environ, {'APP_ENV':'development','PILOT_ACCESS_REQUIRED':'false'}), patch.object(pilot,'redis_command',new_callable=AsyncMock) as store:
            self.assertEqual(self.client.get('/health').json()['status'],'ok')
            store.assert_not_called()

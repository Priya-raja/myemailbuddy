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
        with patch.dict(main.os.environ, {'APP_ENV':'production'}):
            self.assertEqual(self.client.post('/api/draft',json={'text':'The installation is complete.'}).status_code,401)
            self.assertEqual(self.client.post('/api/send-email',json={}).status_code,404)
            self.assertEqual(self.client.post('/api/workflow/run',json={}).status_code,404)

    def test_invite_is_checked_in_external_store_without_saving_raw_code(self):
        code='fictional-pilot-code-for-tests'
        with patch.dict(main.os.environ, {'APP_ENV':'production'}), patch.object(pilot,'redis_command',new_callable=AsyncMock) as store:
            store.return_value=json.dumps({'active':True,'daily_limit':5})
            result=self.client.post('/api/access',headers={'Authorization':'Bearer '+code})
        self.assertEqual(result.status_code,200)
        self.assertEqual(store.await_args.args[0],['GET','buddy:invite:'+hashlib.sha256(code.encode()).hexdigest()])

    def test_revoked_invite_is_rejected(self):
        with patch.dict(main.os.environ, {'APP_ENV':'production'}), patch.object(pilot,'redis_command',new_callable=AsyncMock,return_value=None):
            self.assertEqual(self.client.post('/api/access',headers={'Authorization':'Bearer fictional-pilot-code'}).status_code,401)

    def test_daily_quota_exhaustion_prevents_model_call(self):
        with patch.dict(main.os.environ, {'APP_ENV':'production'}), patch.object(pilot,'redis_command',new_callable=AsyncMock) as store, patch.object(main,'build_draft_chain') as chain:
            store.side_effect=[json.dumps({'active':True,'daily_limit':1}),0]
            result=self.client.post('/api/draft',headers={'Authorization':'Bearer fictional-pilot-code'},json={'text':'The installation is complete.'})
        self.assertEqual(result.status_code,429)
        chain.assert_not_called()
        self.assertEqual(store.await_args.args[0][0],'EVAL')

    def test_health_does_not_call_any_provider(self):
        with patch.dict(main.os.environ, {'APP_ENV':'development','PILOT_ACCESS_REQUIRED':'false'}), patch.object(pilot,'redis_command',new_callable=AsyncMock) as store:
            self.assertEqual(self.client.get('/health').json()['status'],'ok')
            store.assert_not_called()

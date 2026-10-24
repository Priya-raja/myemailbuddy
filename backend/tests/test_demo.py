import hashlib
import json
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import main
from safety import pilot
from safety.limits import _buckets

DEVICE='12345678-1234-4234-8234-123456789abc'

class DemoTests(unittest.TestCase):
    def setUp(self):
        _buckets.clear()
        env=patch.dict(main.os.environ,{'APP_ENV':'production','PILOT_ACCESS_REQUIRED':'false','DEMO_LIMIT_ENABLED':'true','GROQ_API_KEY':'test','UPSTASH_REDIS_REST_URL':'https://example.invalid','UPSTASH_REDIS_REST_TOKEN':'test'})
        env.start();self.addCleanup(env.stop)
        report=patch('safety.usage.finish_usage',new_callable=AsyncMock)
        report.start();self.addCleanup(report.stop)
        self.client=TestClient(main.app)
        self.chain=AsyncMock()
        self.chain.ainvoke.return_value={'subject':'Update','body':'The installation is complete.','translation':'முடிந்தது.'}

    def test_fourth_attempt_blocks_before_model_across_draft_and_improve(self):
        with patch.object(pilot,'redis_command',new_callable=AsyncMock,side_effect=[1,1,1,-1]) as store, patch.object(main,'build_draft_chain',return_value=self.chain):
            for path in ['/api/draft','/api/improve','/api/draft']:
                self.assertEqual(self.client.post(path,headers={'X-Device-ID':DEVICE},json={'text':'The installation is complete.'}).status_code,200)
            response=self.client.post('/api/improve',headers={'X-Device-ID':DEVICE},json={'text':'The installation is complete.'})
        self.assertEqual(response.status_code,403)
        self.assertEqual(response.json()['detail']['message'],pilot.DEMO_MESSAGE)
        self.assertEqual(self.chain.ainvoke.await_count,3)
        command=store.await_args.args[0]
        self.assertEqual(command[2],2)
        self.assertEqual(command[4],'buddy:demo:'+hashlib.sha256(DEVICE.encode()).hexdigest())
        self.assertEqual(command[-1],3)
        self.assertNotIn(DEVICE,str(command))

    def test_missing_or_invalid_id_cannot_bypass_demo_cap(self):
        with patch.object(pilot,'redis_command',new_callable=AsyncMock) as store, patch.object(main,'build_draft_chain') as model:
            for identity in ['', 'my-fake-id', 'x'*1000]:
                response=self.client.post('/api/draft',headers={'X-Device-ID':identity},json={'text':'The installation is complete.'})
                self.assertEqual(response.status_code,403)
            store.assert_not_called();model.assert_not_called()

    def test_body_demo_id_supports_api_clients(self):
        with patch.object(pilot,'redis_command',new_callable=AsyncMock,return_value=1), patch.object(main,'build_draft_chain',return_value=self.chain):
            self.assertEqual(self.client.post('/api/draft',json={'text':'The installation is complete.','demo_id':DEVICE}).status_code,200)

    def test_scope_rejection_does_not_use_demo_or_shared_quota(self):
        with patch.object(pilot,'redis_command',new_callable=AsyncMock) as store:
            self.assertEqual(self.client.post('/api/draft',headers={'X-Device-ID':DEVICE},json={'text':'Explain gravity.'}).status_code,422)
            store.assert_not_called()

    def test_verified_private_code_bypasses_demo_but_keeps_invite_quota(self):
        with patch.object(pilot,'redis_command',new_callable=AsyncMock,side_effect=[json.dumps({'active':True,'daily_limit':20}),1]) as store, patch.object(main,'build_draft_chain',return_value=self.chain):
            response=self.client.post('/api/draft',headers={'Authorization':'Bearer fictional-valid-code'},json={'text':'The installation is complete.'})
        self.assertEqual(response.status_code,200)
        command=store.await_args.args[0]
        self.assertEqual(command[2],1)
        self.assertNotIn('buddy:demo:',str(command))
        self.assertEqual(command[4],20)

    def test_invalid_private_code_never_bypasses_demo(self):
        with patch.object(pilot,'redis_command',new_callable=AsyncMock,return_value=None), patch.object(main,'build_draft_chain') as model:
            self.assertEqual(self.client.post('/api/draft',headers={'Authorization':'Bearer fictional-invalid-code'},json={'text':'The installation is complete.'}).status_code,401)
            model.assert_not_called()

    def test_daily_exhaustion_does_not_proceed_to_model(self):
        with patch.object(pilot,'redis_command',new_callable=AsyncMock,return_value=0), patch.object(main,'build_draft_chain') as model:
            self.assertEqual(self.client.post('/api/draft',headers={'X-Device-ID':DEVICE},json={'text':'The installation is complete.'}).status_code,429)
            model.assert_not_called()

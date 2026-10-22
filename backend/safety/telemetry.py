"""Content-free scope/usage tracing. Never store prompts, responses or identities."""
import json
import logging
from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger('emailbuddy.scope')
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

def record_scope(decision: str, language: str, token_usage: dict | None = None, reason: str = 'none') -> None:
    counts = token_usage or {}
    safe = {key: max(0, int(counts.get(key, 0) or 0)) for key in ('input_tokens', 'output_tokens', 'total_tokens')}
    logger.info(json.dumps({'scope_decision': decision, 'language': language, 'token_usage': safe, 'rejection_reason_category': reason}))

class UsageTrace(BaseCallbackHandler):
    def __init__(self, language: str):
        self.language = language

    def on_llm_end(self, response, **kwargs):
        usage = (response.llm_output or {}).get('token_usage', {})
        record_scope('allow', self.language, {
            'input_tokens': usage.get('prompt_tokens', 0),
            'output_tokens': usage.get('completion_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0),
        })

    def on_llm_error(self, error, **kwargs):
        record_scope('allow', self.language, reason='provider_error')

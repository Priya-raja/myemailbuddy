"""Private, content-free daily usage aggregates in Redis, retained for 90 days.

Device IDs are self-asserted analytics labels, never authentication or quotas.
"""
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import logging
import re
from urllib.parse import unquote
from .pilot import redis_command, store_configured

OPERATIONS = {'/api/draft': 'draft', '/api/improve': 'improve',
              '/api/translate': 'translate', '/api/transcribe': 'transcribe'}
current_usage: ContextVar[dict | None] = ContextVar('current_usage', default=None)
RETENTION_SECONDS = 90 * 86400
FIELDS = ('requests', 'admitted', 'successes', 'failures', 'blocked', 'draft',
          'improve', 'translate', 'transcribe', 'input_tokens', 'output_tokens',
          'total_tokens', 'token_reports', 'audio_ms', 'audio_duration_reports')


def start_usage(request):
    device = request.headers.get('x-device-id', '')
    invite = getattr(request.state, 'invite_id', None)
    if invite:
        identity = 'invite-' + invite
    elif re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}', device):
        identity = 'device-' + hashlib.sha256(device.lower().encode()).hexdigest()
    else:
        identity = 'unattributed'
    raw_name = unquote(request.headers.get('x-usage-name', '')[:720])
    name = re.sub(r"[^\w .'-]", '', raw_name, flags=re.UNICODE).strip()[:60]
    return current_usage.set({'identity': identity, 'name': name, 'day': datetime.now(timezone.utc).date().isoformat(),
                              'operation': OPERATIONS[request.url.path]})


def admitted():
    usage = current_usage.get()
    if usage is not None:
        usage['admitted'] = 1


def add_tokens(counts):
    usage = current_usage.get()
    if usage is not None:
        for field in ('input_tokens', 'output_tokens', 'total_tokens'):
            usage[field] = usage.get(field, 0) + max(0, int(counts.get(field, 0) or 0))
        usage['token_reports'] = usage.get('token_reports', 0) + 1


def add_audio_duration(audio):
    # Our recorder uploads WAV. Unknown/other formats are not guessed.
    import io
    import wave
    try:
        with wave.open(io.BytesIO(audio), 'rb') as recording:
            milliseconds = round(recording.getnframes() * 1000 / recording.getframerate())
        usage = current_usage.get()
        if usage is not None:
            usage.update(audio_ms=milliseconds, audio_duration_reports=1)
    except (wave.Error, EOFError, ValueError, ZeroDivisionError):
        pass


AGGREGATE = """
if ARGV[2] ~= '' then redis.call('HSET', KEYS[1], ARGV[1] .. ':name', ARGV[2]) end
for i = 3, #ARGV, 2 do
  redis.call('HINCRBY', KEYS[1], ARGV[1] .. ':' .. ARGV[i], ARGV[i+1])
end
redis.call('EXPIRE', KEYS[1], 7776000)
return 1
"""


async def finish_usage(status):
    usage = current_usage.get()
    if usage is None or not store_configured():
        return
    counts = {field: usage.get(field, 0) for field in FIELDS}
    counts.update(requests=1, successes=int(status < 400), failures=int(status >= 400),
                  blocked=int(status in (401, 403, 422, 429)))
    counts[usage['operation']] = 1
    command = ['EVAL', AGGREGATE, 1, 'buddy:usage:' + usage['day'], usage['identity'], usage['name']]
    for field, value in counts.items():
        command.extend([field, value])
    try:
        await redis_command(command)
    except Exception:
        # Reporting must not replay a provider request or turn a completed draft into an error.
        logging.getLogger(__name__).warning('Usage aggregation unavailable; counters may be incomplete.')

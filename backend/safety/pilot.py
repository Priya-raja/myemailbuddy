"""Pilot access and persistent daily quotas through an external Redis REST store."""
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
import httpx
from fastapi import HTTPException, Request


def production() -> bool:
    return os.getenv('APP_ENV', 'development') == 'production'

def access_required() -> bool:
    return os.getenv('PILOT_ACCESS_REQUIRED', 'false').lower() == 'true'

def store_configured() -> bool:
    return bool(os.getenv('UPSTASH_REDIS_REST_URL', '').startswith('https://') and os.getenv('UPSTASH_REDIS_REST_TOKEN'))

async def redis_command(command: list):
    if not store_configured():
        raise HTTPException(503, 'Pilot access storage is not configured.')
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(os.environ['UPSTASH_REDIS_REST_URL'].rstrip('/'),
                headers={'Authorization': 'Bearer ' + os.environ['UPSTASH_REDIS_REST_TOKEN']}, json=command)
        response.raise_for_status()
        data = response.json()
        if 'error' in data:
            raise ValueError('store error')
        return data.get('result')
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, 'Pilot access is temporarily unavailable. Please try again later.') from None

async def authenticate(request: Request) -> None:
    authorization = request.headers.get('authorization', '')
    if not access_required() and not authorization:
        return
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not 16 <= len(token.strip()) <= 256:
        raise HTTPException(401, {'code': 'invite_required', 'message': 'Enter your pilot access code to continue.'})
    invite_id = hashlib.sha256(token.strip().encode()).hexdigest()
    value = await redis_command(['GET', 'buddy:invite:' + invite_id])
    try:
        invite = json.loads(value) if value else {}
        active = invite.get('active') is True
        limit = max(1, min(100, int(invite.get('daily_limit', 20))))
    except (ValueError, TypeError, AttributeError):
        active, limit = False, 20
    if not active:
        raise HTTPException(401, {'code': 'invite_required', 'message': 'This pilot access code is invalid or expired.'})
    request.state.invite_id = invite_id
    request.state.daily_limit = limit

# Atomically check/increment with expiry: concurrent calls cannot exceed the limit.
DAILY_QUOTA = """
if #KEYS == 2 and tonumber(redis.call('GET', KEYS[2]) or '0') >= tonumber(ARGV[3]) then return -1 end
local count = tonumber(redis.call('GET', KEYS[1]) or '0')
if count >= tonumber(ARGV[1]) then return 0 end
if #KEYS == 2 then redis.call('INCR', KEYS[2]) end
redis.call('INCR', KEYS[1])
redis.call('EXPIRE', KEYS[1], ARGV[2])
return 1
"""
DEMO_LIMIT = 3
DEMO_MESSAGE = 'Demo limit reached. Please contact Priya for full access.'
DEMO_ROUTES = {'/api/draft', '/api/improve', '/api/workflow/run'}
DEMO_ID_PATTERN = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}'

def demo_enabled():
    return os.getenv('DEMO_LIMIT_ENABLED', 'true' if production() else 'false').lower() == 'true'

async def enforce_daily_quota(request: Request, *, demo_id: str = '') -> None:
    from .usage import admitted
    invite_id = getattr(request.state, 'invite_id', None)
    if access_required() or invite_id:
        if not invite_id:
            raise HTTPException(401, {'code':'invite_required', 'message':'Enter your pilot access code to continue.'})
        prefix = f'buddy:quota:{invite_id}'
        limit = request.state.daily_limit
        exhausted = 'Your daily pilot allowance is used. Please try again tomorrow (UTC).'
    else:
        # Public visitors need no credential. Keep a durable shared daily ceiling
        # so removing invites does not expose an unlimited provider budget.
        if not production() and not store_configured() and not demo_enabled():
            admitted()
            return
        try:
            limit = int(os.getenv('PUBLIC_REQUESTS_PER_DAY', '100'))
        except ValueError:
            raise HTTPException(503, 'Public usage limit is not configured correctly.') from None
        if not 1 <= limit <= 10000:
            raise HTTPException(503, 'Public usage limit is not configured correctly.')
        prefix = 'buddy:quota:public'
        exhausted = 'Today’s shared free allowance is used. Please try again tomorrow (UTC).'
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    ttl = max(1, int((tomorrow - now).total_seconds()))
    key = f'{prefix}:{now:%Y%m%d}'
    demo_key = None
    if demo_enabled() and request.url.path in DEMO_ROUTES and not invite_id:
        identity = request.headers.get('x-device-id') or demo_id
        if not re.fullmatch(DEMO_ID_PATTERN, identity):
            raise HTTPException(403, {'code':'demo_id_required', 'message':'Please refresh the app to start your demo.'})
        demo_key = 'buddy:demo:' + hashlib.sha256(identity.lower().encode()).hexdigest()
    command = (['EVAL', DAILY_QUOTA, 2, key, demo_key, limit, ttl, DEMO_LIMIT] if demo_key
               else ['EVAL', DAILY_QUOTA, 1, key, limit, ttl])
    allowed = await redis_command(command)
    if allowed == -1:
        raise HTTPException(403, {'code':'demo_limit', 'message':DEMO_MESSAGE})
    if allowed != 1:
        raise HTTPException(429, exhausted, headers={'Retry-After': str(ttl)})
    admitted()

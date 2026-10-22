"""Bounded in-process hourly client quotas; use shared storage for multi-worker deployments."""
import hashlib
import os
import time
from collections import OrderedDict, deque
from threading import Lock
from fastapi import HTTPException, Request

_buckets: OrderedDict[str, deque] = OrderedDict()
_lock = Lock()

def enforce_quota(request: Request) -> None:
    identity = getattr(request.state, 'invite_id', None) or (request.client.host if request.client else 'local')
    key = hashlib.sha256(identity.encode()).hexdigest()
    try:
        limit = max(1, min(100, int(os.getenv('WRITING_REQUESTS_PER_HOUR', '20'))))
    except ValueError:
        limit = 20
    now = time.monotonic()
    with _lock:
        bucket = _buckets.setdefault(key, deque())
        _buckets.move_to_end(key)
        while bucket and bucket[0] <= now - 3600:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(429, 'Writing limit reached. Please try again later.', headers={'Retry-After': '3600'})
        bucket.append(now)
        while len(_buckets) > 10000:
            _buckets.popitem(last=False)

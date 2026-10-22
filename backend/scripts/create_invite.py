"""Create a pilot invite in the external store. Displays the code once; no local records."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import secrets
import sys
from dotenv import load_dotenv
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from safety.pilot import redis_command

async def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--daily-limit', type=int, default=20)
    parser.add_argument('--days', type=int, default=30)
    options = parser.parse_args()
    if not 1 <= options.daily_limit <= 100 or not 1 <= options.days <= 365:
        parser.error('Use daily limit 1–100 and expiry 1–365 days.')
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    code = secrets.token_urlsafe(24)
    key = 'buddy:invite:' + hashlib.sha256(code.encode()).hexdigest()
    await redis_command(['SET', key, json.dumps({'active':True, 'daily_limit':options.daily_limit}), 'EX', options.days * 86400])
    print('Pilot access code (share privately): ' + code)

if __name__ == '__main__':
    asyncio.run(run())

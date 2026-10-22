"""Owner-only usage report. Uses local backend Redis credentials; no public API."""
import argparse
import asyncio
from datetime import date, datetime, timezone, timedelta
import html
import json
from pathlib import Path
import sys
from dotenv import load_dotenv
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from safety.pilot import redis_command
from safety.usage import FIELDS

async def report():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', type=date.fromisoformat, default=datetime.now(timezone.utc).date(), help='UTC date YYYY-MM-DD')
    parser.add_argument('--days', type=int, default=1)
    parser.add_argument('--html', type=Path, help='Save a private, standalone HTML report')
    args = parser.parse_args()
    if not 1 <= args.days <= 90:
        parser.error('--days must be between 1 and 90')
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    rows = []
    for offset in range(args.days):
        day = (args.date - timedelta(days=offset)).isoformat()
        raw = await redis_command(['HGETALL', 'buddy:usage:' + day]) or []
        grouped = {}
        for key, value in zip(raw[::2], raw[1::2]):
            identity, field = key.rsplit(':', 1)
            row = grouped.setdefault(identity, {'date': day, 'device': identity, 'name': '', **dict.fromkeys(FIELDS, 0)})
            if field == 'name':
                row['name'] = value
            elif field in FIELDS:
                row[field] = int(value)
        rows.extend(sorted(grouped.values(), key=lambda row: row['total_tokens'], reverse=True))
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    if args.html:
        columns = ['date','name','device','requests','admitted','successes','failures','blocked','draft','improve','translate','transcribe','input_tokens','output_tokens','total_tokens','token_reports','audio_ms','audio_duration_reports']
        heading = ''.join('<th>'+html.escape(c.replace('_',' '))+'</th>' for c in columns)
        body = ''.join('<tr>'+''.join('<td>'+html.escape(str(row[c]))+'</td>' for c in columns)+'</tr>' for row in rows)
        page = '<!doctype html><meta charset="utf-8"><title>Email Buddy usage</title><style>body{font:14px system-ui;padding:24px;background:#fafbf7;color:#213a32}table{border-collapse:collapse}td,th{padding:10px;border:1px solid #cddcc6;text-align:left}th{background:#edf4e9}td{white-space:nowrap}</style><h1>Email Buddy usage</h1><p>Private report. Dates are UTC. Names are optional and unverified. Counts are operations, not people. Audio is milliseconds; unknown duration is not guessed. Token totals include only usage reported by the provider; failures may consume unreported tokens. Sharing approval and sending are not tracked. Reporting failures may leave gaps.</p><table><thead><tr>'+heading+'</tr></thead><tbody>'+body+'</tbody></table>'
        args.html.write_text(page)
        args.html.chmod(0o600)

if __name__ == '__main__':
    asyncio.run(report())

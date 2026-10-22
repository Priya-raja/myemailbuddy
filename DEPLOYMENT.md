# Pilot deployment: Render + Vercel + Upstash

Repository: https://github.com/Priya-raja/myemailbuddy

Live pilot: https://myemailbuddy.vercel.app

Backend health: https://myemailbuddy-api.onrender.com/health

The first production frontend was deployed with the Vercel CLI from `frontend`. For later CLI releases, run `vercel deploy --prod` from that folder. For Git integration, configure the repository root directory as `frontend` instead.

## 1. Persistent pilot store

Create an Upstash Redis database on the Free plan and copy its REST URL and write token into the secret environment settings below. Optional invites and shared public daily usage are stored there; no SQLite or Render filesystem persistence is used. Keep tokens out of Git and all `NEXT_PUBLIC_*` variables.

## 2. Render backend

Import this repository as a Blueprint using the root `render.yaml`, or create a Python Web Service with these exact settings:

| Setting | Value |
| --- | --- |
| Plan | Free |
| Root directory | `backend` |
| Python version | `3.13.13` |
| Build | `pip install -r requirements.txt` |
| Start | `uvicorn main:app --host 0.0.0.0 --port $PORT --no-access-log` |
| Health check | `/health` |

Environment settings:

- `APP_ENV=production`
- `PILOT_ACCESS_REQUIRED=false`: public drafting without access codes.
- `PUBLIC_REQUESTS_PER_DAY=100`: shared daily ceiling across all public visitors.
- `PYTHON_VERSION=3.13.13`
- `GROQ_MODEL=qwen/qwen3.8-27b`
- `GROQ_API_KEY` and `SARVAM_API_KEY`: backend secrets.
- `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`: database secrets.
- `CORS_ORIGINS`: exact Vercel production origin, without a trailing slash. Comma-separate additional explicitly approved origins; do not use a wildcard.

The health endpoint returns 503 until the external pilot-store settings exist. It makes no model call. Copy the actual assigned Render HTTPS URL after provisioning; do not assume that a service name determines an available public hostname.

Production allows public drafting by default. Set `PILOT_ACCESS_REQUIRED=true` only to restore optional invite-only access. Keep Upstash configured in both modes; public requests are capped atomically across all backend processes. Legacy SMTP send and workflow routes are disabled in production. The UI still opens user-controlled mail/WhatsApp drafts. Do not add Gmail SMTP credentials to Render.

## 3. Public access and optional invites

For the existing Render service, explicitly set `PILOT_ACCESS_REQUIRED=false` and `PUBLIC_REQUESTS_PER_DAY=100` in its environment and redeploy the updated backend. Merely changing environment variables on the old code does not remove its forced production invite requirement. The frontend already handles anonymous requests; no frontend changes are needed.

The 100-operation allowance is shared by all visitors and resets at midnight UTC (4 AM Dubai). Transcription, drafting, improving, and translation each use one operation. Admitted provider failures still consume an operation. Existing hourly limits remain in place but are process-local and use the network client address for anonymous visitors; they are not a durable per-person quota. Public visitors can share the same proxy address. The global Redis quota remains authoritative.

The health check verifies storage configuration exists, not Redis reachability; storage failures block writing with 503.

For optional invite-only access, set `PILOT_ACCESS_REQUIRED=true`, then create invites:

With the Upstash REST URL/token in your local root `.env` (or shell environment), run:

```sh
cd backend
.venv/bin/python scripts/create_invite.py --daily-limit 20 --days 30
```

This displays a random access code once and stores only its hash as an external Redis key. Share it privately with one tester. To revoke, delete its `buddy:invite:<sha256>` key or set its JSON value's `active` field to false. Raw codes are never stored by the backend. The browser holds the entered code only in page memory and sends it as a Bearer header, not in a URL.

Each code has a persistent daily allowance, shared across processes and restarts. A Lua script atomically checks/increments usage, expiring counters at the next UTC midnight. Admitted drafting, improving, translation and transcription calls count toward the allowance. The local hourly limiter supplements it and groups authenticated calls by invite rather than a shared proxy IP. Scope rejection/clarification does not use a writing allowance. Successful transcription counts even if its resulting text later fails scope admission.

## 4. Vercel frontend

The `myemailbuddy` project is created under the signed-in `priyarajas-projects` scope. Import the repository, choose **Next.js**, and set **Root Directory** to `frontend`.

- Install: `npm ci`
- Build: `npm run build`
- Public environment: `NEXT_PUBLIC_API_BASE_URL=<actual Render HTTPS URL>`
- Deploy the production environment. Public variables are compiled at build time; redeploy when changing the backend URL.

The previous local `NEXT_PUBLIC_API_URL` name remains a fallback. Prefer `NEXT_PUBLIC_API_BASE_URL` for deployments. Only the backend URL is public. Never add provider, Redis or invite secrets to Vercel's public build settings.

Recordings upload directly from the browser to FastAPI. There is no Next.js upload proxy. On the first request after five minutes, the browser checks `/health`, shows “Starting the service…” and allows up to two minutes for a sleeping Render service to wake. Only health requests are retried automatically; writing/audio submissions are not replayed.

## 5. Verify before inviting testers

1. `/health` returns `status: ok` over HTTPS.
2. With public mode, anonymous valid drafting/transcription can proceed without a code; legacy send endpoints still return 404.
3. Exhaust the configured shared public allowance using mocked providers and verify 429 before any further provider calls. If optional invite mode is enabled, verify valid/revoked/expired codes.
4. A fictional short draft includes subject, greeting, body, closing and native translation.
5. Check CORS from the actual Vercel origin and reject an unapproved origin.
6. Test recording on HTTPS, copy/open-draft clearing, and PWA installation.
7. Test the cold-start notice after Render sleeps, and verify the shared daily allowance survives a service restart.

No raw audio, messages, responses, access codes or IP addresses are included in scope tracing. The configured writing model remains capped at 500 output tokens, with reasoning disabled and no automatic provider retries.

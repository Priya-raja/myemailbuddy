# My Email Buddy

An everyday English writing assistant for Tamil, Hindi, Telugu, Marathi and Arabic speakers. Type in native script, romanized text (Tanglish / Hinglish), mixed language, or record your voice. Choose Office, A colleague or A friend (Office includes formal school administration messages); email or WhatsApp; and a tone. Review and edit the English draft and check its native-language translation before opening your mail app or WhatsApp to choose a recipient and send.

## Run locally

1. Copy `.env.example` to `.env` if you don't already have one; set `GROQ_API_KEY` and `SARVAM_API_KEY`.
2. Backend: `cd backend`, `uv sync`, then `uv run uvicorn main:app --reload --port 8000`.
3. In another terminal: `cd frontend`, `npm install`, `npm run dev`.
4. Open http://localhost:3000. API docs: http://localhost:8000/docs.

The frontend defaults to `http://localhost:8000`. Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` to change it. Configure `CORS_ORIGINS` in the root `.env` for other frontend origins. Microphone access requires localhost or HTTPS. Audio uploads are limited to 25 MB. Microphone recordings stop automatically after 25 seconds and are converted to mono 16 kHz WAV before upload for consistent browser compatibility.

## Providers and review

Sarvam Saaras v3 handles Indian-language speech in code-mix mode. Groq Whisper handles Arabic speech. LangChain with Groq generates structured English drafts and native-language translations. The default model is `qwen/qwen3.8-27b` with thinking disabled; set `GROQ_MODEL` in the root `.env` to use another model available to your Groq account, then restart the backend. Model translations can make mistakes; review names, dates, numbers and intent. After editing a draft, refresh the translation and approve again. The main frontend opens an email/WhatsApp draft and never sends automatically. Transcripts and messages are sent to the configured AI providers and kept only in page memory by this frontend.

The existing LangGraph interrupt/resume SMTP workflow remains available for local experimentation (`/api/workflow/run`, `/api/workflow/resume`), along with `/api/send-email`. These legacy endpoints send using the configured Gmail account. The UI does not call them. They have no authentication: keep the backend local. Before a shared deployment, add user authentication, authorization, per-user mail credentials, request limits, durable isolated workflow storage and approval handling for edited drafts. Current MemorySaver workflow state disappears on restart.

## Checks

`cd frontend && npm run build`

`cd backend && .venv/bin/python -m unittest discover -s tests`

## Input admission

`backend/safety/policy.py` checks drafts, translation refreshes and legacy workflow input before writing-model calls. Detected PII, links, abuse and injection-like instructions are rejected. Explicit research/general-answer commands are rejected with a warning toast. Everyday messages do not require office, school or industry keywords to pass. Checks use deterministic multilingual keyword rules with no classifier tokens. These rules are approximate and conservative, not a guarantee of semantic safety. See `backend/safety/README.md` for limitations.

## Installable app (PWA)

The frontend includes a web manifest, 192/512 px icons, a maskable icon, Apple home-screen metadata and a production service worker. Use **Install app** in the app; supported Chromium browsers offer an installation prompt, and other browsers show menu instructions. iPhone/iPad users can open the HTTPS site in Safari and choose Share → Add to Home Screen.

The service worker runs only with `npm run build` followed by `npm run start`. Test on localhost or deploy over HTTPS. Configure `NEXT_PUBLIC_API_URL` to a reachable HTTPS backend for use on another device; localhost refers to that device. Include the deployed frontend origin in backend `CORS_ORIGINS`.

Offline launches show a reconnect screen. Drafting and transcription require the internet. Only the static offline page and app icons are cached; drafts, input, audio and API responses are never cached by the service worker. Existing input remains in page memory until cleared or the page closes. The **Clear** button clears entered text without deleting an existing draft; successful generation also clears the input, while failures retain it.

Frontend checks: `cd frontend && node --test tests/*.test.mjs`.

## Scope classification and improving drafts

The frontend has separate **Write a new message** and **Improve an existing draft** modes, an audience selector, an optional purpose and message details. `/api/improve` validates existing content without requiring “write” or “email” keywords. Both modes use the zero-token `backend/safety/scope.py` classifier before any drafting call. Unclear messages ask one focused question; research requests get a fixed backend response.

Scope traces contain only decision, language, usage counts and reason category. The writing output is capped at 500 tokens, automatic retries are disabled, and `WRITING_REQUESTS_PER_HOUR=20` limits admitted requests per local client. See `backend/safety/README.md` for measurement, privacy and deployment limits. Run `cd backend && .venv/bin/python scripts/evaluate_scope.py` for the fictional regression report.

## Deploy the pilot

See [DEPLOYMENT.md](DEPLOYMENT.md) for the exact Render/Vercel settings, persistent Upstash invite/daily quota setup, and production verification steps. `render.yaml` provisions the backend. The frontend uses `NEXT_PUBLIC_API_BASE_URL` (the previous local name remains supported).

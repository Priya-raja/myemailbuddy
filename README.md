# My Email Buddy

An everyday English writing assistant for Tamil, Hindi, Telugu, Marathi and Arabic speakers. Type in native script, romanized text (Tanglish / Hinglish), mixed language, or record your voice. Choose manager, colleague or friend; email or WhatsApp; and a tone. Review and edit the English draft and check its native-language translation before opening your mail app or WhatsApp to choose a recipient and send.

## Run locally

1. Copy `.env.example` to `.env` if you don't already have one; set `GROQ_API_KEY` and `SARVAM_API_KEY`.
2. Backend: `cd backend`, `uv sync`, then `uv run uvicorn main:app --reload --port 8000`.
3. In another terminal: `cd frontend`, `npm install`, `npm run dev`.
4. Open http://localhost:3000. API docs: http://localhost:8000/docs.

The frontend defaults to `http://localhost:8000`. Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` to change it. Configure `CORS_ORIGINS` in the root `.env` for other frontend origins. Microphone access requires localhost or HTTPS. Audio uploads are limited to 25 MB. Microphone recordings stop automatically after 25 seconds and are converted to mono 16 kHz WAV before upload for consistent browser compatibility.

## Providers and review

Sarvam Saaras v3 handles Indian-language speech in code-mix mode. Groq Whisper handles Arabic speech. LangChain with Groq generates structured English drafts and native-language translations. The default model is `openai/gpt-oss-120b`; set `GROQ_MODEL` in the root `.env` to use another model available to your Groq account, then restart the backend. Model translations can make mistakes; review names, dates, numbers and intent. After editing a draft, refresh the translation and approve again. The main frontend opens an email/WhatsApp draft and never sends automatically. Transcripts and messages are sent to the configured AI providers and kept only in page memory by this frontend.

The existing LangGraph interrupt/resume SMTP workflow remains available for local experimentation (`/api/workflow/run`, `/api/workflow/resume`), along with `/api/send-email`. These legacy endpoints send using the configured Gmail account. The UI does not call them. They have no authentication: keep the backend local. Before a shared deployment, add user authentication, authorization, per-user mail credentials, request limits, durable isolated workflow storage and approval handling for edited drafts. Current MemorySaver workflow state disappears on restart.

## Checks

`cd frontend && npm run build`

`cd backend && .venv/bin/python -m unittest discover -s tests`

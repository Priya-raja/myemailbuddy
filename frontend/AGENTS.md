# Frontend agent instructions

These instructions apply to files under `frontend/`. Read [SKILLS.md](./SKILLS.md) for task-specific workflows.

## Product

My Email Buddy helps nonnative English speakers turn everyday thoughts into English emails and WhatsApp messages. Support Tamil, Hindi, Telugu, Marathi, Nepali and Arabic, including native scripts, romanized input such as Tanglish and Hinglish, and mixed English.

- Let users choose Office, A colleague or A friend (Office includes formal school administration messages), message channel, and tone.
- Keep the original intent and make the draft editable.
- Show a native-language translation so users can check the meaning.
- Editing the draft must invalidate approval and mark the translation as stale. Require a refreshed translation and a new review before sharing.
- Open an email or WhatsApp draft only after review. The user chooses the recipient and sends it. Do not add automatic sending.

## Stack and boundaries

- Use Next.js App Router, React, strict TypeScript, plain CSS and Lucide icons.
- `app/page.tsx` contains the current interactive drafting flow; `app/globals.css` contains shared styles; `app/layout.tsx` contains page metadata and the root layout.
- Use client components for browser APIs and interactive state. Clean up microphone streams when recording ends or the component unmounts.
- Call FastAPI through `NEXT_PUBLIC_API_BASE_URL`, with the previous `NEXT_PUBLIC_API_URL` as a fallback, defaulting to `http://localhost:8000`. Keep Sarvam, Groq and SMTP credentials on the backend. Never put secrets in `NEXT_PUBLIC_*` variables.
- The frontend uses `/api/transcribe`, `/api/draft` and `/api/translate`. It does not call the legacy SMTP or approval/resume endpoints.
- Do not persist message content or audio, or add analytics that capture them, unless explicitly requested.

- Unsafe and off-topic responses use the warning toast; preserve entered text and do not retry blocked requests. Backend checks are authoritative and must run before model calls.

## User experience

- Use simple, reassuring language and clear labels. Keep implementation details out of the user flow.
- Preserve the original light green and cream palette: background #FAFBF7, green actions #287354, white cards and dark green text #213A32. Keep the layout responsive and easy to read.
- Support keyboard navigation, visible focus, labeled controls, loading states and useful errors.
- Use `dir="auto"` for mixed-language input and translated content; mark language-specific text with the appropriate `lang` attribute.
- Prevent duplicate requests and sharing of stale, unreviewed or empty drafts.
- Keep typed input available when a provider request fails. Never silently substitute example output for an API failure.

## Validation

Run commands from `frontend/`:

- `npm run dev`: local development server.
- `npm run build`: production compilation and TypeScript validation.
- `npm run typecheck`: TypeScript check; Next.js generated type files may require running a build first on a clean checkout.

For behavior changes, check the affected flow in the browser at desktop and mobile widths. Use mocked provider responses for repeatable checks where practical. Do not send messages or expose real credentials during verification. Documentation-only changes do not require an application build.

Preserve the generated Next.js block below when updating this file.

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## PWA and text lifecycle

- The Clear button clears entered text without removing a completed draft. Successful generation clears input; errors retain it. Successful copying and clicking an enabled email/WhatsApp link clear the completed draft, translation, input and approval; clipboard failures preserve the draft. Email drafts must have a nonempty subject for every tone.
- `app/manifest.ts`, `components/pwa.tsx` and `public/sw.js` implement installation and offline fallback. Register the worker only in production.
- Cache only the static offline page and icons. Never cache user input, draft HTML, API responses or audio. Keep service worker updates uncached.
- Drafting and transcription require a network connection; installation does not imply offline AI support.

## Deployment

- Frontend: Vercel; backend: Render; persistent pilot invite and daily quota store: Upstash Redis. Read the root `DEPLOYMENT.md`.
- Show the cold-start notice while checking backend health. Retry health checks only, never automatically replay writing or audio requests.
- Upload audio directly to FastAPI. Pilot access codes stay in page memory and travel only in Bearer headers.

- Public demo drafting and improving share three lifetime attempts per browser ID. A `demo_limit` error opens the private access-code form. Verified private codes retain their own daily quotas. Browser IDs are self-asserted and are not authentication.

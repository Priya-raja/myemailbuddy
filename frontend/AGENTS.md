# Frontend agent instructions

These instructions apply to files under `frontend/`. Read [SKILLS.md](./SKILLS.md) for task-specific workflows.

## Product

My Email Buddy helps nonnative English speakers turn everyday thoughts into English emails and WhatsApp messages. Support Tamil, Hindi, Telugu, Marathi and Arabic, including native scripts, romanized input such as Tanglish and Hinglish, and mixed English.

- Let users choose manager, colleague or friend, message channel, and tone.
- Keep the original intent and make the draft editable.
- Show a native-language translation so users can check the meaning.
- Editing the draft must invalidate approval and mark the translation as stale. Require a refreshed translation and a new review before sharing.
- Open an email or WhatsApp draft only after review. The user chooses the recipient and sends it. Do not add automatic sending.

## Stack and boundaries

- Use Next.js App Router, React, strict TypeScript, plain CSS and Lucide icons.
- `app/page.tsx` contains the current interactive drafting flow; `app/globals.css` contains shared styles; `app/layout.tsx` contains page metadata and the root layout.
- Use client components for browser APIs and interactive state. Clean up microphone streams when recording ends or the component unmounts.
- Call FastAPI through `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`. Keep Sarvam, Groq and SMTP credentials on the backend. Never put secrets in `NEXT_PUBLIC_*` variables.
- The frontend uses `/api/transcribe`, `/api/draft` and `/api/translate`. It does not call the legacy SMTP or approval/resume endpoints.
- Do not persist message content or audio, or add analytics that capture them, unless explicitly requested.

## User experience

- Use simple, reassuring language and clear labels. Keep implementation details out of the user flow.
- Preserve the existing calm green palette, responsive layout and readable spacing.
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

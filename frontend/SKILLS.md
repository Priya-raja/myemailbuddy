# Frontend task workflows

This file records project-specific working guidance. Read it alongside [AGENTS.md](./AGENTS.md). It is not an installed Codex skill package.

## Build or refine a screen

1. Inspect the existing components and styles before adding a new pattern.
2. Keep the main flow clear: explain the message → choose audience/channel/tone → generate → edit → check translation → review → share.
3. Use semantic HTML and accessible names. Handle narrow screens, keyboard focus and long native-script text.
4. Reuse the existing visual language and Lucide icons. Avoid dependencies for behavior that React or CSS can handle directly.
5. Build and inspect the changed states in the browser, including errors and loading.

## Connect an API feature

1. Confirm the request and response models in `../backend/main.py`.
2. Keep all provider calls and secrets in FastAPI; call the backend using the configured API base URL.
3. Handle non-success responses and network failures with a clear error and a way to retry.
4. Preserve user input, disable conflicting actions while a request is pending, and prevent stale responses from overwriting newer work.
5. Update setup documentation when configuration or API contracts change.

Current contracts:

| Endpoint | Request | Response |
| --- | --- | --- |
| `POST /api/transcribe` | Multipart `audio` file and `language` | `transcript` |
| `POST /api/draft` | JSON `text`, `language`, `persona`, `target`, `tone` | `subject`, `body`, `translation` |
| `POST /api/translate` | JSON `text`, `language` | `translation` |

Language codes: `ta-IN`, `hi-IN`, `te-IN`, `mr-IN`, `ar`. Audience values: `manager`, `colleague`, `friend`. Channel values: `email`, `whatsapp`. Tone values: `polite`, `professional`, `friendly`, `confident`, `brief`.

## Work on voice input

1. Use `getUserMedia` and `MediaRecorder` only after the user chooses to record.
2. Explain unsupported browsers, unavailable microphones and denied permission without losing typed input.
3. Keep the chosen recording language consistent through transcription and upload the actual recorded MIME type.
4. Stop media tracks on completion, errors and unmount. Handle empty recordings and the backend's 25 MB limit.
5. Let users correct the transcript before generating a draft. Test with synthetic audio or explicit user-provided samples.

## Work on translation and review

1. Preserve names, dates, numbers, uncertainty and the user's intended meaning.
2. Keep English output and the native-language meaning visible and distinguishable. Account for Arabic direction and mixed scripts.
3. Invalidate review whenever the draft changes. Show stale translations clearly and refresh them from the complete edited draft.
4. Enable sharing only after the current draft has a current translation and explicit review.
5. Encode email subjects, bodies and WhatsApp text correctly. Opening a draft must leave final sending to the user.

## Verify a frontend change

- Run `npm run build` for application changes; use `npm run typecheck` for focused type checks.
- Exercise empty input, successful generation, API failure, draft editing, stale translation, translation refresh and review before sharing when those paths are affected.
- Check native script, romanized input and Arabic text, plus email and WhatsApp formatting.
- Check keyboard access and mobile layout. Verify recording cleanup when voice behavior changes.
- Report what was actually tested and distinguish mocked checks from live provider verification.

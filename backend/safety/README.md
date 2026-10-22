# Safety heuristics

Deterministic detection and redaction adapted from the supplied example. Import through `safety` from the backend. This package does not call models, access links, log input, sleep, or change drafts. `policy.py` now enforces admission before drafting, translation refresh and the legacy drafting workflow. Rejected requests return HTTP 422 with `detail.code` and `detail.message`; no writing-model call is made.

```python
from safety import assess_user_input, detect_and_redact_pii

assessment = assess_user_input("Please email me at person@example.com")
assert assessment.action == "SECURE"
assert not assessment.cache_allowed
assert not assessment.link_access_allowed

redaction = detect_and_redact_pii("My passport number is A1234567")
assert redaction.redacted_text == "My passport number is [REDACTED_PASSPORT]"
```

Included signals:

- PII: email, contextual booking reference, ticket number and passport; Emirates ID, UAE/Indian/generic phone, SSN, PAN, payment-card-like digits and Aadhaar-like digits.
- English profanity and a narrow standalone-insult detector that preserves longer service requests.
- External links and suspicious hostname keywords. Link access is always disabled in the assessment.
- Injection-like instructions asking to override rules or disclose prompts/secrets.
- Tool availability, incomplete observations, model-overload detection and retry instructions. The caller owns any delay and retry budget.

Assessment precedence: injection → `BLOCK`; PII → `SECURE`; suspicious hostname → `REVIEW`; profanity or external link → `WARN`; otherwise `OK`. Only `OK` and `WARN` permit caching in the returned recommendation. These labels are signals from the supplied rules, not enforced application policy or judgments of user intent. `RETRY` is available for callers; overload helpers return a retry plan separately.

## Limits

Regex matches are approximate. Numeric patterns do not validate identifiers or payment cards with checksums. Patterns run in insertion order against progressively redacted text, so an overlapping value receives the first matching category rather than every possible category. Context labels are preserved for booking references, ticket numbers and passports.

The profanity and injection rules are English only. They do not provide Tamil, Hindi, Telugu, Marathi or Arabic moderation, or comprehensive protection against obfuscation. Hostname keywords and the limited bare-domain suffix list do not establish whether a site is safe; URLs are never fetched. Malformed matching URLs are flagged for review. PII can be missed or misclassified, and legitimate quotes can resemble injection attempts. Do not treat an `OK` result as proof that text contains no sensitive information.

Keep secrets and message text out of logs. The application uses a strict policy requested for this project: all detected PII, external links, profanity, suspicious links and injection-like instructions are rejected, rather than silently redacted. Users must remove those details before drafting. Additional multilingual rules reject common abuse and explicit research/general-answer commands. Ordinary message content no longer has to contain office, school or industry keywords. Mentions of research or inline questions in a message are allowed; direct research/answer commands remain blocked before model calls. The model is restricted to rewriting the supplied communication without answering questions. Rules are approximate and can miss unfamiliar phrasing; maintain regression examples as coverage grows. Speech transcription still uses Sarvam/Groq audio services; this gate protects the subsequent writing LLM.

Run tests from `backend/`:

```sh
.venv/bin/python -m unittest discover -s tests
```

Banking, software installation and other status updates are allowed without requiring a manager or industry keyword in the message. PII and injection checks still apply.

## Zero-token scope classifier

`scope.classify_scope` classifies untrusted submitted text without answering it. It is pure Python: no model, network or tokenizer call. Decisions are `allow`, `clarify`, and `reject`. Direct Q&A and mixed research-plus-email requests are rejected. Writing requests and supplied factual status updates are allowed. Ambiguous fragments ask one focused question. A validated selected purpose can resolve some guided-interface ambiguity; it never bypasses research or safety checks. The existing-draft route accepts supplied content without requiring writing keywords.

`POST /api/draft` and `POST /api/improve` accept `text` (details or existing content), `persona` (recipient category), optional `purpose`, channel, tone and language. `POST /api/translate` checks existing content before translation. The legacy workflow is also guarded. Rejections and clarification use HTTP 422 with `detail.status` (`outside_scope`, `needs_details`, or `unsafe_message`), `detail.code` and a fixed `detail.message`. Input remains available in the UI.

Outside scope: “I can help write or improve an email or WhatsApp message. Tell me who it’s for and what you want to say.” Missing details: “Who is this message for, and what do you want to tell them?” Missing source facts: “What facts or existing text should the message include?”

## Tracing, measurement and limits

The `emailbuddy.scope` logger emits only `scope_decision`, `language`, `token_usage` (input/output/total), and `rejection_reason_category`. Rejected/clarified input records zero tokens; provider usage is recorded via `UsageTrace`. Prompt/response tracing through LangSmith is disabled. No text, recipient, IP address, source document or model response is included in these scope traces. Avoid adding raw exception or request-body logging elsewhere.

Run `.venv/bin/python scripts/evaluate_scope.py` from `backend/`. Fictional fixtures track correctness, false rejections, false clarifications, missed rejections and avoided generation requests. Classification cost is exactly zero calls/tokens; avoided token counts are not invented. Compare observed allowed-call usage against a measured baseline if a token-savings estimate is needed. The initial 27-case fixture is a regression sample, not evidence of complete safety.

Writing calls have a 500-token output cap, no automatic provider retry, and a default 20 admitted writing requests per client per hour (`WRITING_REQUESTS_PER_HOUR`, clamped 1–100). Quotas run after admission and cover drafting, improving, translation and the legacy workflow. Local quota counters use bounded process memory and reset on restart; they use the direct client IP, not untrusted forwarding headers. A shared deployment needs authentication and a shared quota store for real per-user limits across workers.

This reduces misuse; it does not eliminate it. Regex cannot reliably distinguish every intent, especially regional spellings, quotations and mixed-language attacks. Keep safety checks, output caps and quotas even when the classifier passes.

The default Qwen 3.8 model uses `reasoning_effort="none"` so the 500-token cap is spent on the short draft and translation. GPT-OSS overrides use low reasoning effort, which can still consume the cap. Truncated outputs are rejected explicitly; there is no automatic second model call.

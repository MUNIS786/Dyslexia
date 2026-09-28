# AI Assistant — Root Cause & Fix Report

## 1. Request flow traced

```
ChatPage.jsx --sendMessage()--> api/client.js (chatAPI.send)
  --> axios.post('/api/chat', {message, history})
    --> FastAPI routers/chat.py  @router.post("/chat")
      --> [DUPLICATE LOGIC LIVED HERE] --> Gemini REST call
      --> on ANY failure --> silently returned _faq_fallback()
```

`services/ai_service.py` already contained a full, well-structured AI layer
(`chat_reply`, prompts, JSON parsing, Claude→Gemini→Emergent chain) — **but
`routers/chat.py` never called it.** It had its own separate copy of
`_call_gemini()` and its own separate `FAQ` list / `_faq_fallback()`. That is
the duplicate implementation the task asked to remove.

## 2. Root cause

In `routers/chat.py`:

```python
reply = await _call_gemini(history, system)
if reply:
    return {"reply": reply.strip(), "source": "gemini-flash"}
return {"reply": _faq_fallback(msg), "source": "faq"}
```

`_call_gemini()` swallowed **every** possible failure into a bare `return None`:
network errors, non-200 responses, empty `candidates` (safety blocks, quota
errors, malformed key, rate limiting under real concurrent frontend traffic),
and JSON-shape mismatches were all caught by a single `except Exception` and
logged with a `print()` that most process managers never surface.

Because of that, **any** transient Gemini hiccup — quota, safety filter,
timeout, or a 4xx from a bad key — caused the endpoint to return a normal
`200 OK` with an FAQ string instead of an error. Postman (a single, isolated
test call) worked; sustained frontend usage hit the same failure path more
often and always landed on the FAQ, with no visible error anywhere.

There was no explicit "offline mode" switch — the FAQ was a silent, permanent
safety net instead of a deliberate, configured fallback.

## 3. What was fixed

### `services/ai_service.py`
- Added a real `logger` (module-level, configurable via `LOG_LEVEL`).
- Added `AIServiceError` — a typed exception carrying an HTTP status code.
- Added `get_gemini_key()` — centralized API key access; raises `AIServiceError`
  (500) immediately if `GEMINI_API_KEY` is missing/empty, instead of quietly
  returning `None` later.
- Centralized model selection: `GEMINI_MODEL` (default `gemini-2.0-flash`,
  overridable via env var) and `GEMINI_API_URL` built from it in one place.
- Added `CHAT_OFFLINE_MODE` env flag (default `false`) — the **only** way the
  FAQ fallback can ever be served now.
- Rewrote the chat call as `_call_gemini_chat()`:
  - Uses proper multi-turn Gemini format (`systemInstruction` + `contents`
    with `user`/`model` roles), matching what actually worked via Postman.
  - Logs the outgoing request (model, turn count), the HTTP status, and the
    raw error body on failure.
  - Distinguishes network errors, non-200 responses, empty/blocked
    candidates, and malformed response shapes — each raises `AIServiceError`
    with a specific message instead of returning `None`.
- Rewrote `chat_reply()` — the single production entry point:
  - Builds the personalized system prompt (student name / dyslexia type /
    language) exactly as before.
  - Calls Gemini once, centrally.
  - On failure: re-raises `AIServiceError` **unless** `CHAT_OFFLINE_MODE=true`,
    in which case (and only then) it returns the offline FAQ answer tagged
    `"offline-faq"`.
- Left `simplify_with_ai`, `generate_lesson_plan`, `generate_ai_plan`,
  `generate_progress_suggestion`, `convert_notes_offline`,
  `generate_daily_tasks` untouched — out of scope for this fix, not part of
  the AI Assistant bug.

### `routers/chat.py`
- Removed the entire duplicate implementation: `GEMINI_KEY`, `_call_gemini()`,
  `SYSTEM_PROMPT`, `FAQ`, `_faq_fallback()`.
- The router now **only**:
  1. Validates the request body.
  2. Loads the optional authenticated user for personalization.
  3. Logs the incoming request.
  4. Delegates to `services.ai_service.chat_reply(...)`.
  5. Catches `AIServiceError` and converts it into a real `HTTPException`
     (500 for missing key, 502 for upstream/Gemini failures) instead of a
     disguised 200-OK FAQ answer.
  6. Logs completion with the source tag and reply length.

### Frontend (`src/pages/student/ChatPage.jsx`, `src/api/client.js`)
Traced and verified — **no changes needed**:
- `api/client.js` posts to `/api/chat` with `{ message, history }`, attaches
  the auth token via an axios interceptor, and has a global 401 handler.
- `ChatPage.jsx` sends the full prior message list as `history`, awaits the
  response, appends `res.reply` to the message list, and shows a `toast`
  error + a generic "trouble connecting" bubble (not a fake FAQ answer) if
  the request throws — which is exactly the correct behavior now that the
  backend returns a real HTTP error instead of a disguised success.

## 4. Why the frontend was getting FAQ answers instead of AI

Every real chat request from the browser went through the exact same
`_call_gemini` → silent-`None`-on-any-error → `_faq_fallback` path described
above. There was nothing frontend-specific about it; the bug was 100%
server-side. Postman "succeeding" simply means that particular manual call
didn't hit one of the failure modes (rate limit, transient network blip,
safety-filter empty candidate, etc.) that real usage patterns hit more often
— and because failures were invisible (no logs, no error status), it looked
like "the frontend" was the problem when it was actually the backend
swallowing errors.

## 5. Environment configuration checklist

- `GEMINI_API_KEY` must be set in the backend `.env` file.
- Confirm `load_dotenv()` (or equivalent) runs **before** `services/ai_service.py`
  is imported anywhere in the app (e.g., at the very top of `main.py`), since
  the key is read at module-import time.
- Optional: `GEMINI_MODEL` to override the model (defaults to
  `gemini-2.0-flash`).
- Optional: `CHAT_OFFLINE_MODE=true` to deliberately re-enable the FAQ
  fallback (e.g. for a demo with no internet/key) — **off by default**.
- If `GEMINI_API_KEY` is missing, the very first chat request now fails with
  a clear `500` and message telling you exactly what's wrong — it will not
  silently serve FAQ text.

## 6. Files modified

| File | Change |
|---|---|
| `services/ai_service.py` | Added logging, `AIServiceError`, centralized key/model config, rewrote `_call_gemini_chat` + `chat_reply` to always call real Gemini and only use FAQ when `CHAT_OFFLINE_MODE=true`. All other functions unchanged. |
| `routers/chat.py` | Removed duplicate Gemini call + FAQ logic; now a thin layer that delegates to `services.ai_service.chat_reply` and converts `AIServiceError` into proper HTTP errors. |
| Frontend files | Inspected only — no changes required. |

Full updated versions of both modified files are attached
(`ai_service.py`, `chat.py`).

## 7. Remaining items to verify on your side (not visible in the uploaded zips)

- `main.py` / app entrypoint wasn't included in the uploads — confirm it calls
  `load_dotenv()` early and does `app.include_router(chat.router, prefix="/api")`
  (or equivalent) and that CORS allows your frontend origin.
- `deps/deps.py` (imported by `routers/chat.py`) wasn't included — confirm
  `get_current_user_optional` doesn't throw on an invalid/expired token (it
  should return `None`, not raise, since the chat endpoint supports anonymous
  use).
- Vite proxy config (`vite.config.js`) wasn't included — confirm `/api` is
  proxied to the FastAPI backend in dev.

# NOVA — Groq AI Chatbot

NOVA is a polished Streamlit chatbot using Python and the official Groq API. It supports live model discovery, personas, memory controls, streaming, exports, multiple session chats, and a responsive dark UI.

## Run locally

Windows PowerShell defaults: the existing `.venv` is reused; otherwise run `python -m venv .venv` and `.venv\\Scripts\\Activate.ps1`. Install with `pip install -r requirements.txt`. Put your real key only in `.streamlit/secrets.toml` as `GROQ_API_KEY = "your-real-key"`, or type it in the sidebar. The key is never stored in exports.

Run with `streamlit run chatbot.py` (headless smoke test: `streamlit run chatbot.py --server.headless true`).

## Defaults and assumptions

- Default model: `llama-3.3-70b-versatile`; live chat-capable models replace the fallback list after connection.
- Default persona is Study Buddy; streaming and conversation memory are enabled; context is 12 recent messages.
- Seed `0` means disabled. Groq uses `max_completion_tokens`; unsupported token settings are retried once without that parameter.
- A shared secrets key is limited to 15 messages per browser session. Typed/environment keys are not subject to that shared-key limit.
- Responses are cleaned of `<think>` blocks and raw reasoning is not displayed.

## Tests

Run `python -m py_compile chatbot.py` and `pytest`.

See [DEPLOY.md](./DEPLOY.md) for publishing and Cloud deployment, and [POST_DRAFTS.md](./POST_DRAFTS.md) for social copy.

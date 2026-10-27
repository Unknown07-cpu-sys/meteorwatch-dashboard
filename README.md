# METEORWATCH v4 — Optional API / Bring Your Own Key

This patch replaces the fixed, owner-configured Gemini key flow with three options:

1. **No API — built-in briefing (free):** uses the saved fields and fixed rules. No LLM is called.
2. **OpenRouter — free-model router:** the visitor enters their own OpenRouter key; the app requests `openrouter/free` so that it routes to available free models. Free-model availability/rate limits can vary.
3. **Google Gemini API:** the visitor enters their own Gemini API key and can choose the model. `gemini-3.5-flash-lite` is the default model; Google's current pricing page lists free-tier input/output pricing for this model, but the user's project eligibility, quota, and provider terms still apply.
4. **Custom OpenAI-compatible API:** the visitor supplies an HTTPS base URL, model name, and key. This works only with providers implementing the OpenAI-compatible `/chat/completions` endpoint (for example, compatible deployments of Groq/OpenRouter), not literally every API format.

## Files to update

- Replace `app.py` with this package's `app.py`.
- Replace `requirements.txt` with this package's `requirements.txt`.
- Keep `meteorwatch_full_review_report.csv` in the repository.
- Do not add any user API key to GitHub or a file.

## Security and data handling

- The user-supplied key is displayed as a password input and the app code does not intentionally write it to disk, CSV, or repository.
- **Important:** when a user enters a key into this public Streamlit app, it passes through the Streamlit app server to make the API call. Users should only enter a key if they trust the app operator/hosting service. The selected provider receives the request payload. Do not submit personal/confidential information.
- Only a single selected event's allowlisted fields, a few fixed dataset counts/methodology details, and the question are sent to the provider; the full CSV is not sent.
- API keys should be treated as sensitive credentials. If a key is accidentally exposed, revoke it from the provider dashboard.
- No API mode keeps a rule-based briefing available regardless of API availability.
- LLM outputs may be wrong; anomaly flags are review prompts, not danger ratings or predictions.

## Free options caveats

Free tiers are subject to provider terms, per-model availability, usage/rate limits and data-handling policies. Do not promise unlimited free usage. The OpenRouter `openrouter/free` model router is intended to route to available free models; availability and rate limits may change. Gemini free-tier use has its own constraints and Google's pricing page notes free-tier content may be used to improve products. Check current terms/pricing before use.

## Deploy

Upload/commit the new `app.py` and `requirements.txt` to your existing public GitHub repository. Keep `meteorwatch_full_review_report.csv`. Streamlit Community Cloud should redeploy automatically. Test the no-API mode first; then optionally test a user's own key.

## Current docs checked on 27 October 2026

- Gemini pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini models: https://ai.google.dev/gemini-api/docs/models
- OpenRouter free-model router: https://openrouter.ai/docs/guides/routing/routers/free-router
- Groq OpenAI compatibility: https://console.groq.com/docs/openai

# Hybrid models and request-role verification

## Model selection

- Intake, grounded research and structured research use `DEFAULT_MODEL`, default
  `gemini-3.5-flash-lite`, through `atlas.models.build_model()`.
- Only the itinerary agent passes `settings.itinerary_model` to `build_model`;
  `ITINERARY_MODEL` defaults to `gemini-3.6-flash`.
- Route optimization makes no model request. Search grounding remains ON by default.
- Google verifies the stable ID and structured output support at
  https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash.

## Can a wire request end in a model turn?

Not with the installed ADK request path tested here. Model turns can exist inside
history, but the final outbound turn is user-role. No role-rewriting production fix
was needed; retaining model history is important for function calls and thought
signatures.

Evidence in installed `google/adk/` source:

1. `flows/llm_flows/contents.py`, lines 626-659: replies from another agent are
   passed through `_present_other_agent_message` before request contents are built.
2. That helper, lines 763-790, reconstructs them with `role='user'` and agent
   attribution. Thus the previous stage's model output is user context for the
   next stage, rather than an assistant prefill.
3. `models/google_llm.py`, lines 190-191: Gemini preprocessing is followed by
   `_maybe_append_user_content` before either streaming or non-streaming SDK calls.
4. `models/base_llm.py`, lines 153-194: if the final role is not user, it appends a
   user continuation instruction. Empty contents also receive a user instruction.

Offline tests replace `google.genai.models.AsyncModels.generate_content` itself,
not ADK's adapter, so they observe the actual contents after ADK preprocessing and
immediately before SDK transport. The real API, ADK stages, shared state, and route
optimizer execute against the ten-day Japan fixture. Both Search-enabled and
Search-disabled configurations are covered.

Observed outbound roles:

| Stage | Model | Roles |
| --- | --- | --- |
| Intake | gemini-3.5-flash-lite | user |
| Grounded research | gemini-3.5-flash-lite | user, user |
| Structured research | gemini-3.5-flash-lite | user, user, user |
| Itinerary | gemini-3.6-flash | user, user, user, user |

A separate regression deliberately supplies `[user, model]` to the real adapter.
The SDK receives `[user, model, user]`; the original model output is preserved and
the caller's request is unchanged. This also covers an own-agent continuation,
not just sibling messages in SequentialAgent.

Run `backend/.venv/bin/python -m pytest -q -s backend/tests/test_request_roles.py`
from the project root to reproduce. No provider calls or deployments are involved.

---
name: cerebras
description: Call openai/gpt-oss-120b on the Cerebras provider through OpenRouter, from the Next.js server - plain fetch, no SDK. Use when writing or changing the chat panel's model call (frontend/lib/chat/openrouter.ts, nextStep/chat.md layer 3), or any other server-side LLM call in this repo.
---

# Calling gpt-oss-120b on Cerebras via OpenRouter

## The architecture

```
browser -- POST /api/chat --> app/api/chat/route.ts        (Next.js server, runtime nodejs)
                                 | layers 0-2 answer?  -> done, no model call
                                 v
                              lib/chat/openrouter.ts        (the only file that calls out)
                                 | fetch, OPENROUTER_API_KEY
                                 v
                              OpenRouter  --provider pinned-->  Cerebras  (openai/gpt-oss-120b)
                                 |
                                 v
                              lib/chat/guard.ts  (ADVICE scan on the whole answer) -> browser
```

- **Model** `openai/gpt-oss-120b`. **Provider** Cerebras, and only Cerebras - it is chosen for
  speed, because the panel does not stream and generation time is the whole wait.
- **TypeScript and `fetch`.** No LiteLLM, no Python, no `openai` package. OpenRouter speaks
  OpenAI-compatible JSON; one `POST` is the whole integration.
- **Server-side only.** Never `NEXT_PUBLIC_`; the key never reaches the browser.
- **The key** is `OPENROUTER_API_KEY` in the repo-root `secrets.env`, which Compose passes to
  `nextjs-web` with `env_file` + `format: raw`. A value in `.env` does **not** reach the
  container - that file is Compose's substitution source only. `npm run dev` reads
  `frontend/.env.local`. The owner puts the key in `secrets.env`; never read, edit or commit
  that file (root `CLAUDE.md`).
- **A missing key disables layer 3 and nothing else.** Return the "not available" answer; do
  not throw. The chat panel must never be able to take the site down.

## The call

```ts
const URL = "https://openrouter.ai/api/v1/chat/completions";
const MODEL = "openai/gpt-oss-120b";
const PROVIDER = { order: ["cerebras"], allow_fallbacks: false, require_parameters: true };

type Message = { role: "system" | "user" | "assistant"; content: string };

export async function complete(messages: Message[], apiKey: string, fetchFn = fetch) {
  const res = await fetchFn(URL, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: MODEL,
      messages,
      provider: PROVIDER,
      reasoning: { effort: "low" },
      max_tokens: 300,
      temperature: 0.2,
      seed: 7,
    }),
    signal: AbortSignal.timeout(15_000),
  });
  if (!res.ok) throw new ModelUnavailable(res.status, await res.text());
  const body = await res.json();
  if (body.provider !== "Cerebras") throw new Error(`served by ${body.provider}, not Cerebras`);
  return { text: body.choices[0].message.content as string, usage: body.usage };
}
```

Why each setting is there:

| Setting | Why |
|:--|:--|
| `allow_fallbacks: false` | the default is `true`: when Cerebras is busy OpenRouter silently routes elsewhere - slower, and at another price |
| `require_parameters: true` | never route to a provider that would ignore `reasoning` or `response_format` |
| `reasoning.effort: "low"` | gpt-oss's reasoning tokens are billed as output and count against `max_tokens` |
| `max_tokens: 300` | a three-sentence answer, and the ceiling on the output half of the bill |
| `temperature: 0.2`, `seed` | the same question gets the same answer, so the response cache (layer 2) is hit |
| no `stream` | the `ADVICE` guard must see the whole answer before any of it is shown (chat.md 6) |
| `AbortSignal.timeout` | a hung upstream must not hold a request open |

The `body.provider` check is the proof the pin held. If it ever fires, the routing is wrong -
fix the request, do not relax the check.

## Errors: answer, never retry

A 429, 5xx, timeout or a non-Cerebras provider becomes `ModelUnavailable`, and the route answers
"the panel cannot answer that one right now" from layers 0-1. **No retry loop** - a retry on a
public endpoint is how one bad minute becomes a bill. Surface the status in the server log.

An empty `content` with `finish_reason: "length"` means reasoning used the whole `max_tokens`.
Keep `effort: "low"`; treat it as unavailable rather than raising the cap.

## Usage and the budget

`body.usage` is always present (`prompt_tokens`, `completion_tokens`, `cost`); the old
`usage: { include: true }` flag is deprecated and does nothing. The daily budget in
`lib/chat/budget.ts` counts from these figures, never from an estimate.

## The wording guard shares one list

The system prompt (`lib/chat/prompt.ts`) names the banned words and `lib/chat/guard.ts` blocks
them - both import `frontend/lib/advice.json`, the one copy `test/wording.test.ts` and the
Playwright scan read too. A second copy drifts. The
model is never asked to do arithmetic; it is handed the page's figures and puts them in a
sentence.

## Structured output

Cerebras supports `response_format` with a strict JSON schema:

```ts
response_format: {
  type: "json_schema",
  json_schema: {
    name: "answer",
    strict: true,
    schema: {
      type: "object",
      properties: { answer: { type: "string" }, unsure: { type: "boolean" } },
      required: ["answer", "unsure"],
      additionalProperties: false,
    },
  },
},
```

`JSON.parse(text)` and read the fields directly - a parse failure is a bug to surface, not a
default to fill in.

## Tests

No network. `complete()` takes `fetchFn`; the tests pass a fake that returns a canned body.
Cover: a non-Cerebras `provider` throws; a 429 and a 503 become `ModelUnavailable` with one
fetch call, not several; a missing key never calls the fake; the request body carries the
pinned `provider` object exactly.

## Verify a fact here before relying on it

Prices and parameters change. Check the Cerebras endpoint directly:

```bash
curl -s https://openrouter.ai/api/v1/models/openai/gpt-oss-120b/endpoints
```

On 2026-09-24 the Cerebras endpoint (`cerebras/fp16`) was $0.35/M input, $0.75/M output, no
cached-input discount, 131k context, 40,960 max output, and `response_format`,
`structured_outputs`, `reasoning` and `seed` all supported.

# LGX extension

LangGraph-based conversational agents for Renglo. The implementation lives under `package/` as the installable Python distribution **`renglo-lgx`** (import package `lgx`).

Handlers follow the same scheduler contract as other extensions (e.g. Claw `ParallelAgent`): a `run(payload)` entry point, standard payload fields (`portfolio`, `org`, `entity_type`, `entity_id`, `thread`, `data`), and a response shaped as `{success, action, input, output}`.

The [`langgraph`](https://pypi.org/project/langgraph/) library is a dependency only — the extension package itself is **`lgx`**, so there is no import namespace collision.

## Install

From `extensions/lgx/package/`:

```bash
pip install -e .
```

Python **3.12+**. Integration with sessions, scheduler, and data layers expects **`renglo`** (for example `pip install -e dev/renglo-lib` from the repo root).

## Configuration

- **`OPENAI_API_KEY`** — required for LLM calls.
- **`WEBSOCKET_CONNECTIONS`** — API Gateway management URL for streaming when `connectionId` is present on the inbound payload.
- **`DYNAMODB_SESSION_TABLE`** — required for session persistence.

## Handlers

| Handler | Module | Description |
|---------|--------|-------------|
| `demo_lgx_agent` | `lgx.handlers.demo_lgx_agent` | Simple LangGraph conversational loop (load context → LLM → respond → persist). |

## Onboarding

1. Install the Python package on the API host.
2. In the console marketplace, use **Install** on the LGX card and pick a portfolio.
   That runs `lgx/lgx_onboardings`, which registers the **LGX** tool and the `demo_lgx_agent` scheduler entry.

## UI (console chat)

The extension includes a React UI under `ui/` that mirrors the session-based chat flow used by NOMA triage:

- Route: `/{portfolio}/{org}/lgx/chat`
- Handler routing: `core: "lgx/demo_lgx_agent"`
- Session entity: `lgx-chat` / `lgx-{org}-{user_handle}`

Add `lgx` to `VITE_EXTENSIONS` in the console env (already set in `.env.development` when using the repo defaults), install the `lgx` tool in your portfolio, and open the **Chat** section in the LGX sidenav.

## Package layout

```
extensions/lgx/
├── README.md
├── ui/
│   ├── lgx.tsx
│   ├── package.json
│   ├── navigation/
│   ├── onboarding/
│   └── pages/
│       └── lgx_chat.tsx
└── package/
    ├── pyproject.toml        # renglo-lgx
    ├── setup.py
    ├── requirements.txt
    └── lgx/
        ├── __init__.py
        └── handlers/
            ├── demo_lgx_agent.py
            ├── models.py
            ├── sessions.py
            └── renglo_adapter.py
```

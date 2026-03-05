# Backend Design Document (BDD)

---

```
Project Name:   Postware
Document Type:  Backend Design Document (BDD)
Version:        0.1
Date:           2025-03-05
Status:         Draft
```

---

## Section 1 — User Stories

### P0 — MVP Critical

| ID | User Story |
|---|---|
| US-001 | As a solo developer, I want to run a single CLI command so that three platform-optimized posts are generated and delivered to my Telegram chat without manual effort. |
| US-002 | As a solo developer, I want the system to automatically select today's content pillar so that my posts follow the weekly schedule without me tracking it. |
| US-003 | As a solo developer, I want the system to enforce the 80/20 value-to-promotion ratio so that my content strategy stays on track automatically. |
| US-004 | As a solo developer, I want generation history stored locally so that the system avoids repeating topics and maintains pillar rotation. |
| US-005 | As a solo developer, I want Telegram delivery of a formatted post bundle so that I can immediately copy and publish from my phone. |
| US-006 | As a solo developer, I want to configure my LLM provider and model in a YAML file so that I can switch between cloud and local models without touching source files. |
| US-007 | As a solo developer, I want an `init` command so that I can get a working configuration scaffold in under two minutes. |

### P1 — Important

| ID | User Story |
|---|---|
| US-008 | As a solo developer, I want to send `/regenerate` in Telegram and pick a single platform so that I can get a fresh post for just that channel without re-running the full pipeline. |
| US-009 | As a solo developer, I want to send `/status` in Telegram so that I can check my content stats without opening a terminal. |
| US-010 | As a solo developer, I want a daemon mode so that post generation runs automatically every day at a configured time without a cron entry. |
| US-011 | As a solo developer, I want failed runs to log detailed errors to `errors.log` so that I can debug problems without re-running the pipeline. |

### P2 — Nice-to-Have

| ID | User Story |
|---|---|
| US-012 | As a solo developer, I want a `status` CLI command so that I can check pillar distribution and promo ratio from the terminal. |
| US-013 | As a solo developer, I want the system to retry failed LLM and Telegram calls automatically so that transient outages don't require manual intervention. |

---

## Section 2 — Entity Identification

### Entity: `GenerationRecord`
The core unit of stored data. One record per generation run.

| Field | Type | Constraints |
|---|---|---|
| `date` | string (ISO 8601) | Required, format: `YYYY-MM-DD` |
| `day_of_week` | string | Required; one of: Mon/Tue/Wed/Thu/Fri/Sat/Sun |
| `pillar` | string | Required; one of: P1/P2/P3/P4/P5 |
| `is_promotional` | boolean | Required |
| `platform_posts` | object | Required; contains `x`, `linkedin`, `threads` sub-objects |
| `platform_posts.x` | object | `text` (string, ≤280 chars), `format_type` (string), `image_suggestion` (string) |
| `platform_posts.linkedin` | object | `text` (string, ≤1500 chars), `format_type` (string), `image_suggestion` (string) |
| `platform_posts.threads` | object | `text` (string, ≤500 chars), `format_type` (string), `image_suggestion` (string) |
| `generated_at` | string (ISO 8601 datetime) | Required |
| `llm_provider` | string | Optional; recorded for diagnostics |
| `llm_model` | string | Optional; recorded for diagnostics |

### Entity: `AppConfig`
Loaded from `config.yaml` at runtime. Validated via Pydantic on load.

| Field | Type | Constraints |
|---|---|---|
| `project.name` | string | Required |
| `project.description` | string | Required |
| `project.url` | string | Optional |
| `author.name` | string | Required |
| `author.bio` | string | Optional |
| `milestones` | list[string] | Optional |
| `changelog` | list[string] | Optional |
| `llm.provider` | string | Required |
| `llm.model` | string | Required |
| `llm.base_url` | string | Optional (local models only) |
| `llm.temperature` | float | Optional; default 0.8 |
| `llm.max_tokens` | int | Optional; default 2000 |
| `schedule.time` | string | Required for daemon; format HH:MM |

### Entity: `EnvConfig`
Loaded from `.env` via python-dotenv.

| Variable | Required | Purpose |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | Authenticates bot with Telegram API |
| `TELEGRAM_CHAT_ID` | Yes | Destination for message delivery |
| `ANTHROPIC_API_KEY` | Conditional | Required if provider = anthropic |
| `OPENAI_API_KEY` | Conditional | Required if provider = openai |
| `GROQ_API_KEY` | Conditional | Required if provider = groq |
| `GOOGLE_API_KEY` | Conditional | Required if provider = google |

### Entity: `LLMPrompt`
Constructed at runtime; passed to `litellm.completion()`. Not persisted.

| Field | Description |
|---|---|
| `system_prompt` | Static instructions: role, output format, content strategy rules |
| `user_prompt` | Dynamic: project context, pillar, platform rules, recent post summaries, promo constraint |

---

## Section 3 — Throughput Tier

**Tier 1 — Single-User Local Tool**

Postware is a single-process, single-user CLI application running on a personal machine. There is no network-facing server, no concurrent users, and no distributed state. The sole throughput constraint is the LLM API response time (5–30s) and Telegram API response time (<2s). A simple modular monolith with file-based storage is the correct and complete architecture — no caching, no message queues, no read replicas are warranted or appropriate.

---

## Section 4 — Feature-to-Module Mapping

| Feature | Module | Priority |
|---|---|---|
| Config loading & validation | `config.py` + `models.py` | P0 |
| History read/write/prune | `history.py` | P0 |
| Pillar resolution & promo ratio | `history.py` | P0 |
| LLM prompt construction | `prompts.py` | P0 |
| LLM call via LiteLLM | `generator.py` | P0 |
| Output parsing & Pydantic validation | `generator.py` + `models.py` | P0 |
| Telegram message formatting | `telegram_bot.py` | P0 |
| Telegram message delivery | `telegram_bot.py` | P0 |
| CLI entrypoint (generate/start/status/init) | `main.py` | P0 |
| Telegram bot command handler (/generate, /regenerate, /status) | `telegram_bot.py` | P1 |
| APScheduler daemon | `scheduler.py` | P1 |
| Retry logic (LLM + Telegram) | `generator.py` + `telegram_bot.py` | P1 |
| Error logging to `errors.log` | All modules (shared logger) | P1 |

---

## Section 5 — Data Modeling

### Database Selection

**Storage: JSON flat file (`history.json`)**

Justification: Postware is a single-user local tool with a maximum dataset of 30 records. The access patterns are purely sequential (append, prune, full-scan for ratio calculations). A JSON file managed via Python's built-in `json` module is the correct solution — it requires zero dependencies, is human-readable and editable, is trivially backed up, and fits entirely within a single `json.load()` call. SQLite is explicitly out of scope per product requirements. No database engine of any kind is warranted.

---

### Entity Relationship Diagram

```
[AppConfig] 1 ──── 1 [LLMPrompt]  (config feeds prompt construction)
[AppConfig] 1 ──── 1 [EnvConfig]  (together form complete runtime config)
[GenerationRecord] * lives in [history.json]  (array, max 30 entries)
[LLMPrompt] ──── produces ──── [GenerationRecord]  (after successful completion)
```

---

### Schema: `history.json`

```
history.json root
└── records[]                    array of GenerationRecord, max 30 entries

GenerationRecord
├── date                         string       ISO 8601 date, e.g. "2025-03-05"
├── day_of_week                  string       "Mon" | "Tue" | "Wed" | "Thu" | "Fri" | "Sat" | "Sun"
├── pillar                       string       "P1" | "P2" | "P3" | "P4" | "P5"
├── is_promotional               boolean      true if post is promotional per 80/20 rule
├── generated_at                 string       ISO 8601 datetime, e.g. "2025-03-05T08:03:11"
├── llm_provider                 string       e.g. "anthropic"
├── llm_model                    string       e.g. "claude-3-5-sonnet-20241022"
└── platform_posts
    ├── x
    │   ├── text                 string       ≤280 chars
    │   ├── format_type          string       e.g. "Progress Update"
    │   └── image_suggestion     string       human-readable description
    ├── linkedin
    │   ├── text                 string       ≤1500 chars
    │   ├── format_type          string
    │   └── image_suggestion     string
    └── threads
        ├── text                 string       ≤500 chars
        ├── format_type          string
        └── image_suggestion     string
```

**Default empty structure (created by `init` and on first run):**
```json
{
  "records": []
}
```

---

### Schema: `config.yaml`

```yaml
project:
  name: string                   # Required
  description: string            # Required — used in LLM prompt
  url: string                    # Optional — included in promotional posts

author:
  name: string                   # Required — attributed in posts
  bio: string                    # Optional — tone/voice context

milestones:                      # Optional list — recent wins for LLM context
  - string

changelog:                       # Optional list — recent changes for LLM context
  - string

llm:
  provider: string               # Required — e.g. "anthropic", "openai", "groq", "ollama"
  model: string                  # Required — e.g. "claude-3-5-sonnet-20241022"
  base_url: string               # Optional — for local models (Ollama/LM Studio)
  temperature: float             # Optional — default: 0.8
  max_tokens: int                # Optional — default: 2000

schedule:
  time: string                   # Required for daemon mode — HH:MM format, e.g. "08:00"
```

---

### Indexing Strategy

Postware uses no database engine, so there are no indexes in the traditional sense. The equivalent access optimization notes for `history.json`:

| Access Pattern | Optimization |
|---|---|
| Promotional ratio (last 14 days) | Full scan on load; max 30 records — O(30) is negligible. No optimization needed. |
| Recent post summaries for deduplication | Full scan of last 30 records on load — same as above. |
| Pillar rotation check | Full scan of last 7 records — trivial. |
| Today's record lookup (for /regenerate) | Iterate records, compare `date` field — O(30). |

---

### Data Validation Rules (Pydantic models in `models.py`)

| Field | Rule |
|---|---|
| `config.project.name` | Non-empty string |
| `config.project.description` | Non-empty string |
| `config.llm.provider` | Must be one of: `anthropic`, `openai`, `groq`, `google`, `ollama`, `lmstudio` |
| `config.llm.model` | Non-empty string |
| `config.llm.temperature` | Float between 0.0 and 2.0 inclusive |
| `config.llm.max_tokens` | Integer between 100 and 8192 inclusive |
| `config.schedule.time` | Matches `^\d{2}:\d{2}$`; hours 00–23, minutes 00–59 |
| `GenerationRecord.date` | Matches `^\d{4}-\d{2}-\d{2}$` |
| `GenerationRecord.pillar` | Must be one of: `P1`, `P2`, `P3`, `P4`, `P5` |
| `GenerationRecord.platform_posts.x.text` | String; len ≤ 280 |
| `GenerationRecord.platform_posts.linkedin.text` | String; len ≤ 1500 |
| `GenerationRecord.platform_posts.threads.text` | String; len ≤ 500 |
| `history.json` records array | Maximum 30 entries enforced on save |

---

## Section 6 — Module Architecture

### Module Responsibilities

#### `main.py` — CLI Entrypoint
Handles CLI argument parsing and dispatches to appropriate modules. Four subcommands: `generate`, `start`, `status`, `init`. Uses Rich for all terminal output. Catches top-level exceptions and ensures non-zero exit codes on failure.

#### `config.py` — Configuration Loader
Loads and validates `config.yaml` using PyYAML + Pydantic. Loads `.env` using python-dotenv. Returns validated `AppConfig` and `EnvConfig` Pydantic model instances. Raises descriptive `ConfigError` on any validation failure.

#### `models.py` — Pydantic Data Models
Defines all data structures: `AppConfig`, `EnvConfig`, `GenerationRecord`, `PlatformPost`, `GeneratedBundle`. These models are the single source of truth for data shapes across all modules.

#### `history.py` — History Manager
Reads, writes, queries, and prunes `history.json`. Exposes:
- `load() → list[GenerationRecord]` — load with corruption recovery
- `save(records: list[GenerationRecord]) → None` — prune to 30, write atomically
- `get_promo_ratio(records, window_days=14) → float`
- `get_recent_pillars(records, n=7) → list[str]`
- `get_today_record(records) → GenerationRecord | None`
- `get_deduplication_context(records, n=10) → list[str]`

Atomic writes: write to `history.json.tmp` then rename to `history.json` to prevent partial-write corruption.

#### `prompts.py` — Prompt Builder
Constructs the system prompt and user prompt strings passed to LiteLLM. Takes `AppConfig`, resolved pillar, promo constraint flag, and deduplication context as inputs. Returns a structured prompt dict. The LLM output format specification (JSON schema for three platform posts) lives here.

#### `generator.py` — Content Generation Engine
Orchestrates the full generation pipeline: resolve pillar → calculate promo ratio → build prompt → call LiteLLM → parse and validate output → return `GeneratedBundle`. Implements retry logic with exponential backoff (3 attempts, 1s/2s/4s delays). Logs failures to `errors.log`.

#### `telegram_bot.py` — Telegram Delivery & Bot Handler
Two responsibilities:
1. **Delivery**: Formats `GeneratedBundle` into the Telegram message template; sends via `python-telegram-bot`; implements retry with exponential backoff; handles message splitting if >4096 chars.
2. **Bot commands**: Handles `/generate`, `/regenerate` (with inline keyboard), `/status` command callbacks.

#### `scheduler.py` — APScheduler Daemon
Initializes `BlockingScheduler` with a daily `CronTrigger` from `config.schedule.time`. Registers the generation pipeline as the job. Handles SIGINT/SIGTERM for graceful shutdown.

---

## Section 7 — Third-Party Integrations

| Integration | Library | Purpose | Failure Mode |
|---|---|---|---|
| Anthropic Claude | `litellm` | LLM completions | Retry 3× → errors.log → exit 1 |
| OpenAI GPT | `litellm` | LLM completions | Same |
| Groq | `litellm` | LLM completions | Same |
| Google Gemini | `litellm` | LLM completions | Same |
| Ollama (local) | `litellm` (base_url) | Local LLM completions | Connection refused → retry 3× → exit 1 |
| LM Studio (local) | `litellm` (base_url) | Local LLM completions | Same |
| Telegram Bot API | `python-telegram-bot` | Message delivery + bot commands | Retry 3× → errors.log → exit 1 |

---

## Section 8 — Error Handling Architecture

### Retry Policy

| Operation | Max Retries | Backoff Delays | On Final Failure |
|---|---|---|---|
| LLM API call | 3 | 1s, 2s, 4s | Log to `errors.log`, exit code 1 |
| Telegram message delivery | 3 | 1s, 2s, 4s | Log to `errors.log`, exit code 1 |
| LLM output validation (malformed) | 3 (new calls) | 1s, 2s, 4s | Log to `errors.log`, exit code 1 |

### BDD Scenarios

---

**Feature: Config Validation**

```gherkin
Scenario: config.yaml has missing required fields
  Given the user runs `python -m postware generate`
  And config.yaml exists but is missing the `llm.model` field
  When the config loader attempts to parse config.yaml
  Then the system exits with code 1
  And the terminal displays a Rich-formatted error listing each missing field by name
  And no LLM API calls are made

Scenario: .env is missing a required API key
  Given config.yaml is valid
  And the configured LLM provider is "anthropic"
  And ANTHROPIC_API_KEY is not set in .env
  When the config loader reads the environment
  Then the system exits with code 1
  And the terminal displays: "✗ Missing environment variable: ANTHROPIC_API_KEY"
```

---

**Feature: History Management**

```gherkin
Scenario: history.json does not exist on first run
  Given the user runs `python -m postware generate` for the first time
  And history.json does not exist in the project root
  When the history module attempts to load history.json
  Then the system creates history.json with an empty records array
  And the terminal displays: "ℹ history.json not found. Creating fresh history."
  And the generation pipeline continues normally

Scenario: history.json contains invalid JSON
  Given history.json exists but contains malformed JSON
  When the history module attempts to load history.json
  Then the system copies history.json to history.json.bak
  And creates a new history.json with an empty records array
  And logs a warning to errors.log: "Corrupt history.json backed up to history.json.bak"
  And the generation pipeline continues normally

Scenario: history.json grows beyond 30 entries
  Given history.json contains exactly 30 records
  When the history module saves a new GenerationRecord
  Then the oldest record is removed
  And history.json contains exactly 30 records after the save
```

---

**Feature: Promotional Ratio Enforcement**

```gherkin
Scenario: Promotional ratio is at or above 20% in the rolling 14-day window
  Given the last 14 days of history contain 3 or more promotional posts
  And the promotional ratio calculates to 22%
  When the generator resolves the content constraint for today's run
  Then the is_promotional flag is set to false in the LLM prompt
  And the terminal displays: "ℹ Promo ratio at 22%. Forcing value-driven content."
  And the generated posts contain no promotional calls to action

Scenario: Promotional ratio is below 20%
  Given the last 14 days of history contain fewer than 3 promotional posts
  And the promotional ratio calculates to 14%
  When the generator resolves the content constraint for today's run
  Then no promo override flag is applied
  And the LLM may generate either value-driven or promotional content per pillar logic
```

---

**Feature: LLM Generation with Retry**

```gherkin
Scenario: LLM returns well-formed output on first attempt
  Given config.yaml and .env are valid
  And history.json is loaded successfully
  When the generator calls litellm.completion() with the constructed prompt
  And the LLM returns a valid JSON object with posts for all three platforms
  Then the output is parsed into a GeneratedBundle
  And the record is appended to history.json
  And the bundle is passed to the Telegram delivery module

Scenario: LLM returns malformed output, then succeeds on retry
  Given the generator calls litellm.completion()
  And the first response fails Pydantic validation (missing "threads" platform)
  When the generator retries after a 1-second delay
  And the second response passes validation
  Then the GeneratedBundle is constructed from the second response
  And one warning is written to errors.log: "LLM output validation failed on attempt 1. Retrying."

Scenario: LLM API fails on all three attempts
  Given the generator calls litellm.completion()
  And all three attempts raise a connection error
  When the final retry fails
  Then the full error details are written to errors.log
  And the terminal displays: "✗ LLM failed after 3 attempts. See errors.log for details."
  And the system exits with code 1
  And no Telegram message is sent
  And history.json is not modified
```

---

**Feature: Telegram Delivery**

```gherkin
Scenario: Successful delivery of daily post bundle
  Given a valid GeneratedBundle exists for today
  When the Telegram delivery module formats and sends the message
  Then a single formatted message is delivered to the configured chat ID
  And the message contains sections for X, LinkedIn, and Threads with headers and dividers
  And the footer shows date, pillar, and promotional ratio
  And the terminal displays: "✓ Posts delivered to Telegram."

Scenario: Invalid Telegram credentials
  Given TELEGRAM_BOT_TOKEN contains an invalid value
  When the delivery module makes the first sendMessage API call
  And Telegram returns a 401 Unauthorized response
  Then the system exits immediately with code 1
  And the terminal displays: "✗ Telegram delivery failed: Invalid bot token or chat ID."
  And no retry is attempted

Scenario: Message body exceeds 4,096 characters
  Given the formatted bundle message exceeds Telegram's character limit
  When the delivery module detects the overflow during formatting
  Then the message is split into three separate messages — one per platform section
  And all three messages are sent sequentially to the same chat ID
```

---

**Feature: Telegram Bot /regenerate Command**

```gherkin
Scenario: /regenerate called with no prior generation today
  Given the user sends /regenerate in the Telegram chat
  And history.json contains no record for today's date
  When the bot processes the command
  Then the bot replies: "No posts generated today yet. Use /generate first."
  And no inline keyboard is shown
  And no LLM call is made

Scenario: Successful single-platform regeneration
  Given the user sends /regenerate in the Telegram chat
  And history.json contains a record for today's date
  When the bot sends the platform picker inline keyboard
  And the user taps the "LinkedIn" button
  Then the system generates a new LinkedIn post using today's pillar and context
  And today's record in history.json is updated with the new LinkedIn post
  And the bot sends the regenerated LinkedIn post to the chat with its metadata
```

---

**Feature: CLI `init` Command**

```gherkin
Scenario: First-time init on a clean directory
  Given no config.yaml, .env, or history.json exist in the project root
  When the user runs `python -m postware init`
  Then config.yaml is created with placeholder values for all required fields
  And .env is created as a copy of .env.example
  And history.json is created with an empty records array
  And a setup checklist is printed to the terminal with 5 action items
  And the system exits with code 0

Scenario: Init called when config.yaml already exists
  Given config.yaml already exists in the project root
  When the user runs `python -m postware init`
  Then the terminal displays: "⚠ config.yaml already exists. Overwrite? [y/N]: "
  And if the user enters "n", config.yaml is preserved unchanged
  And .env and history.json are still created if they do not exist
```

---

## Section 9 — Reality Check & Failure Analysis

| Risk | Assessment |
|---|---|
| **Single Point of Failure** | `history.json` is the only persistent store. Atomic writes (write to `.tmp`, then rename) prevent corruption from partial writes. Backup on corrupt-file detection prevents total data loss. Acceptable for a single-user local tool. |
| **Data Loss Scenario** | If the machine loses power between LLM success and history write, the posts are delivered to Telegram but not recorded. The user still receives their posts; only history tracking is affected. This is an acceptable edge case for the use case. |
| **Traffic Spike** | Not applicable. Single-user CLI tool with one invocation per day. LLM API rate limits are the only external constraint, and a single daily call is far below any provider's limits. |
| **Security Breach** | API keys live in `.env` excluded from version control. Blast radius of a compromised `.env` is limited to LLM API billing abuse and Telegram bot message sending to a single chat. No user data, no payment data, no personal records at risk. |
| **Deployment** | Not applicable. Runs locally on the developer's machine. Zero-downtime deployment is not a concern. |
| **Cost** | Single daily LLM call (one prompt, ~2000 tokens output). At current pricing, even GPT-4o costs under $0.05/day. Financially trivial. |
| **MVP Over-Engineering Check** | No over-engineering identified. Every component (LiteLLM, python-telegram-bot, APScheduler, Pydantic, Rich) is directly justified by a P0 or P1 feature. No components are premature. |


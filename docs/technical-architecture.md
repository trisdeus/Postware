# Technical Architecture Document

---

```
Project Name:   Postware
Document Type:  Technical Architecture Document (TAD)
Version:        0.1
Date:           2025-03-05
Status:         Draft
```

---

## Step 1: Discovery & Assumptions

All seven discovery dimensions are fully resolved across the approved specification suite. No clarifying questions required.

📌 **Confirmed Assumptions**

| Dimension | Value |
|---|---|
| **Core Purpose** | CLI tool generating daily platform-optimized social posts via LLM and delivering them to Telegram |
| **Target Users** | Single user — the developer running the tool on their own machine |
| **Stage** | v0 = functional MVP; v1 = production-ready single-user tool. No growth or enterprise stage anticipated. |
| **Team Size** | Solo developer |
| **Key Features** | LLM content generation, history-based pillar rotation, 80/20 enforcement, Telegram delivery, bot commands |
| **Constraints** | No database; no web server; no cloud deployment; Python 3.10+; runs locally |
| **Non-Functionals** | Pipeline ≤60s; no uptime SLA (user's machine); API keys never logged in plaintext |

---

## Step 2: Behavioral Classification

```
🏷️ PRIMARY: Compute-Heavy — the tool's dominant operation is an LLM API call
   that performs content generation; all other operations (file I/O, Telegram
   delivery) are lightweight orchestration around that call.

🏷️ SECONDARY: CRUD-Dominant — history.json read/write/prune operations are
   simple sequential file manipulations; structurally equivalent to CRUD
   against a micro-dataset (max 30 records).

📊 Read/Write Ratio Estimate: 60:40 — each run reads config + history,
   writes history once, and delivers output. Reads are slightly more frequent
   (status checks, /status bot command).

⚡ Latency Sensitivity: Low — the LLM call dominates (5–30s); a few hundred
   milliseconds of orchestration overhead is imperceptible. No real-time
   requirements.

📈 Expected Growth Trajectory: Stable — single-user tool. No user growth curve.
   The only scaling vector is adding more LLM providers or content pillars,
   both of which are configuration changes, not architectural ones.
```

---

## Step 3: Architecture Pattern Selection

```
🏗️ SELECTED PATTERN: Modular Monolith (Single-Process CLI)

📝 RATIONALE: Postware runs as a single Python process on a personal machine.
   There is one user, one data store (history.json), and one execution context.
   A modular monolith — a single process with clearly bounded internal modules —
   is the correct and complete architecture. Each module (config, history,
   generator, prompts, telegram_bot, scheduler, platform_utils) has a single
   responsibility and communicates via direct function calls and shared Pydantic
   models. No inter-service communication, no message broker, no network
   boundary between components is warranted.

⚠️ TRADE-OFFS ACCEPTED: The single-process model means that if a future
   requirement introduces genuine concurrency needs (e.g., simultaneous
   multi-user generation), the architecture would need to be revisited. This is
   an explicit non-goal for v0 and v1 and an acceptable trade-off.

🔄 MIGRATION PATH: If Postware ever evolves into a multi-user hosted service,
   the module boundaries already defined (generator.py, history.py,
   telegram_bot.py) map cleanly to microservice candidates. The Pydantic models
   in models.py would become the API contract types. history.json would be
   replaced by a proper database (PostgreSQL is the natural successor for
   structured generation records). This migration path is a future
   consideration, not a current requirement.
```

---

## Step 4: Data Strategy

### ADR-001: Storage — JSON Flat File vs. SQLite

**Decision ID:** ADR-001
**Status:** Accepted

#### Context
Postware requires persistent storage for one entity type: `GenerationRecord`. Maximum 30 records retained at any time. Access patterns are: full-scan on load, append on write, prune-to-30 on save. Single process, single user, no concurrency.

#### Decision
**JSON flat file (`history.json`)** managed via Python's built-in `json` module.

#### Rationale

| Factor | JSON File | SQLite |
|---|---|---|
| Dependencies | Zero — stdlib only | Requires `sqlite3` (stdlib, but introduces SQL layer) |
| Human readability | ✅ Directly inspectable and editable | ❌ Binary format requires tooling to inspect |
| Backup simplicity | ✅ `cp history.json history.json.bak` | ⚠️ Must use `.dump` or file copy with WAL handling |
| Query complexity | ✅ Full scan of 30 records is O(30) — negligible | Unnecessary for this data volume |
| Atomic writes | ✅ Write-to-tmp + rename pattern | ✅ WAL mode provides atomicity |
| Schema migration | ✅ Simple version field + migration logic in code | ⚠️ Requires ALTER TABLE migrations |
| Explicit constraint | ✅ Specified as no-database requirement | ❌ Violates product constraint |

#### Consequences
- **Positive:** Zero new dependencies, human-readable history, trivially portable (copy the file), inspectable without tooling.
- **Negative:** No query language; all filtering done in Python. Acceptable at ≤30 records.
- **Risk:** Atomic write pattern (write-to-tmp + rename) must be implemented correctly to prevent corruption. This is addressed in `history.py`.

#### Alternatives Considered
1. **SQLite** — Rejected: violates explicit product constraint; adds unnecessary complexity for 30-record dataset.
2. **In-memory only (no persistence)** — Rejected: pillar rotation, deduplication, and promo ratio enforcement all require cross-run history.

---

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PROCESS BOUNDARY                         │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │config.py │    │history.py│    │generator │    │telegram  │  │
│  │          │    │          │    │    .py   │    │  _bot.py │  │
│  │AppConfig │───▶│ records[]│───▶│          │───▶│          │  │
│  │EnvConfig │    │          │    │Pydantic  │    │formatted │  │
│  └──────────┘    └────┬─────┘    │validation│    │ message  │  │
│       │               │          └────┬─────┘    └────┬─────┘  │
│       │          ┌────▼──────┐        │               │        │
│       │          │history.   │   ┌────▼──────┐        │        │
│       │          │json       │   │prompts.py │        │        │
│       │          │(≤30 recs) │   │sanitize() │        │        │
│       │          └───────────┘   └───────────┘        │        │
│       │                                                │        │
└───────┼────────────────────────────────────────────────┼────────┘
        │                                                │
        ▼                                                ▼
  ┌───────────┐                                   ┌───────────────┐
  │  .env     │                                   │ Telegram      │
  │  config   │                                   │ Bot API       │
  │  .yaml    │                                   │               │
  └───────────┘                                   └───────────────┘
        │
        ▼
  ┌───────────┐
  │ LiteLLM  │
  │ (unified │
  │  layer)  │
  └─────┬────┘
        │
   ┌────┴───────────────────────────────────────────┐
   │                LLM PROVIDERS                    │
   │  anthropic │ openai │ groq │ google │ deepseek  │
   │  qwen │ minimax │ kimi │ z.ai │ ollama │ custom  │
   └─────────────────────────────────────────────────┘
```

### Data Schema Reference

Full schema specifications are defined in BDD v0.3. Summary for TAD cross-reference:

| Artifact | Type | Location | Max Size | Access Pattern |
|---|---|---|---|---|
| `history.json` | JSON flat file | Project root | 30 records (~15KB) | Full load on each run; append + prune on write |
| `config.yaml` | YAML file | Project root | ~2KB | Load once per run; validate via Pydantic |
| `.env` | Key-value file | Project root | <1KB | Load once per run via python-dotenv |
| `errors.log` | Plain text | Project root | Unbounded (v0/v1); rotation deferred to v1.1 | Append-only; never read by application code |

---

## Step 5: Technology Stack

### ADR-002: LLM Interface — LiteLLM vs. Direct Provider SDKs

**Decision ID:** ADR-002
**Status:** Accepted

#### Decision
**LiteLLM** as the unified LLM interface layer.

#### Rationale

| Factor | LiteLLM | Direct Provider SDKs (per-provider) |
|---|---|---|
| Provider switching | ✅ Single `litellm.completion()` call; change config only | ❌ Requires different SDK, different error types, different auth per provider |
| Local model support | ✅ Ollama and LM Studio via `base_url` override | ❌ No standard local model SDK |
| Retry / error normalisation | ✅ Unified exception hierarchy | ❌ Each provider has different error types |
| New provider support | ✅ Config change only | ❌ Code change required per provider |
| Dependency weight | ⚠️ Large transitive dependency tree | ✅ Smaller per-provider SDK |
| Maintenance risk | ⚠️ Single point of dependency; mitigated by pip-audit | ✅ Distributed across providers |

#### Consequences
- **Positive:** The user can switch from Claude to Qwen to a local Ollama model by changing two config fields. Zero code changes.
- **Negative:** LiteLLM is a large library with a substantial transitive dependency tree. `pip-audit` during `init` mitigates supply-chain risk.
- **Risk:** LiteLLM dropping support for a provider. Mitigation: all supported providers are mainstream; LiteLLM's provider list is actively maintained.

---

### ADR-003: Telegram Integration — python-telegram-bot vs. httpx direct calls

**Decision ID:** ADR-003
**Status:** Accepted

#### Decision
**python-telegram-bot** library.

#### Rationale

| Factor | python-telegram-bot | Direct httpx/requests calls |
|---|---|---|
| Bot command handling | ✅ Built-in handler registration, callback routing, inline keyboard management | ❌ Must implement handler dispatch, update parsing, callback routing manually |
| Message sending | ✅ Type-safe wrappers with automatic MarkdownV2 escaping helpers | ❌ Manual JSON construction; MarkdownV2 escaping is error-prone |
| Polling mode | ✅ `Application.run_polling()` handles long-polling loop | ❌ Must implement polling loop, backoff, error recovery manually |
| Async support | ✅ Native async/await (v20+) | ✅ httpx is also async-native |
| Maintenance | ✅ Actively maintained; tracks Telegram Bot API changes | ❌ Manual tracking of Telegram API changes |

#### Consequences
- **Positive:** Inline keyboard for `/regenerate`, command handler registration, and message formatting are all first-class features. Implementation complexity is dramatically reduced.
- **Negative:** Library is heavier than raw HTTP calls. Acceptable for this use case.

---

### Full Technology Stack

| Layer | Technology | Version Constraint | Rationale |
|---|---|---|---|
| **Language** | Python | ≥3.10 | Structural pattern matching, modern type hints, `match` statements; broadest developer machine coverage |
| **LLM Interface** | LiteLLM | Latest stable | Unified interface for all 13 supported providers; local model support via `base_url` |
| **Telegram** | python-telegram-bot | ≥20.0 (async) | Native async; built-in inline keyboards, handler routing, MarkdownV2 helpers |
| **Config parsing** | PyYAML | Latest stable | Human-readable YAML; de facto standard for Python developer tool configuration |
| **Env loading** | python-dotenv | Latest stable | Standard `.env` file loading; zero-config credential management |
| **Validation** | Pydantic | v2 | Fast, type-safe schema validation; excellent error messages; first-class Python type hint integration |
| **Scheduling** | APScheduler | ≥3.10 | Lightweight in-process scheduler; cron-style triggers; no external broker |
| **Terminal output** | Rich | Latest stable | Best-in-class Python terminal formatting; panels, tables, progress bars, ANSI colour |
| **File permissions** | `os` (stdlib) + `pywin32` (optional) | pywin32: latest stable | `os.chmod()` for Unix; `pywin32` for Windows ACLs (optional dependency) |
| **Dependency audit** | pip-audit | Latest stable | PyPA-maintained; queries OSV database; no API key required; JSON output |
| **Testing** | pytest | Latest stable | Industry standard; fixture model well-suited to CLI testing patterns |

---

## Step 6: Module Architecture

### Module Dependency Graph

```
main.py
├── config.py
│   ├── models.py          (AppConfig, EnvConfig)
│   └── platform_utils.py  (init-time only)
├── generator.py
│   ├── config.py
│   ├── history.py
│   ├── prompts.py
│   │   └── models.py      (AppConfig)
│   └── models.py          (GeneratedBundle, PlatformPost)
├── telegram_bot.py
│   ├── generator.py       (bot /generate, /regenerate triggers)
│   ├── history.py         (/status, /regenerate pre-check)
│   └── models.py
├── scheduler.py
│   └── generator.py       (scheduled job target)
└── history.py
    └── models.py          (GenerationRecord)
```

**Dependency rules:**
- `models.py` has zero internal imports. It is the dependency floor.
- `config.py` imports only `models.py`. It has no knowledge of generation or Telegram.
- `history.py` imports only `models.py`. It has no knowledge of LLM or Telegram.
- `prompts.py` imports only `models.py`. It has no network calls, no file I/O.
- `generator.py` imports `config`, `history`, `prompts`, `models`. It orchestrates; it does not deliver.
- `telegram_bot.py` imports `generator`, `history`, `models`. It delivers; it does not generate independently.
- `main.py` is the only module that imports everything. It is the composition root.
- `platform_utils.py` is imported only by `main.py` during `init`. No other module needs it.

This structure enforces a strict layering: **models → config/history/prompts → generator → telegram_bot → main**. Circular dependencies are structurally impossible within this design.

---

### Module Specifications

#### `main.py` — Composition Root & CLI Entrypoint

**Responsibility:** Parse CLI subcommands; compose and invoke the correct pipeline; manage process lifecycle; handle top-level exceptions; enforce exit codes.

**Key decisions:**
- Uses `argparse` (stdlib) for subcommand parsing. No third-party CLI framework needed for four subcommands.
- Detects TTY mode via `sys.stdout.isatty()` at startup; sets a global `INTERACTIVE` flag consumed by Rich output components to suppress progress indicators in cron/daemon mode.
- Calls `sys.exit(0)` or `sys.exit(1)` explicitly at all exit points. Never relies on implicit exit.
- Catches all unhandled exceptions at the top level, logs them to `errors.log` via the shared logger, and exits with code 1.

**Python version check:** On startup, before any other logic, verify `sys.version_info >= (3, 10)`. If not:
```
✗ Postware requires Python 3.10 or higher.
  Current version: 3.9.x
  Install Python 3.10+ from https://python.org
```
Exit code 1.

---

#### `config.py` — Configuration Loader

**Responsibility:** Load, parse, and validate `config.yaml` and `.env`; return typed `AppConfig` and `EnvConfig` instances; perform API key format validation.

**Load sequence:**
1. Check `config.yaml` exists → `FileNotFoundError` → `ConfigError` with init suggestion
2. Parse YAML via `PyYAML` → `yaml.YAMLError` → `ConfigError` with line number if available
3. Validate against `AppConfig` Pydantic model → `ValidationError` → `ConfigError` listing each failed field
4. Load `.env` via `python-dotenv` → missing variables → `ConfigError` per missing key
5. Validate API key format for configured provider → warning (non-blocking) if format mismatch

**`ConfigError`:** Custom exception subclassing `Exception`. Carries a human-readable `message` field and an optional `fields` list for validation errors. Caught by `main.py` which formats and prints it via Rich before exiting.

---

#### `models.py` — Pydantic Data Models

**Responsibility:** Define all data shapes as the single source of truth for type contracts across all modules.

**Models defined:**

```
PlatformPost
├── text: str
├── format_type: str
└── image_suggestion: str

GeneratedBundle
├── date: str                    (ISO 8601)
├── day_of_week: DayOfWeek       (Enum: Mon/Tue/Wed/Thu/Fri/Sat/Sun)
├── pillar: Pillar               (Enum: P1/P2/P3/P4/P5)
├── is_promotional: bool
├── platform_posts: PlatformPosts
│   ├── x: PlatformPost
│   ├── linkedin: PlatformPost
│   └── threads: PlatformPost
├── generated_at: datetime
├── llm_provider: str | None
└── llm_model: str | None

GenerationRecord                 (subset of GeneratedBundle; what is stored)
└── (same fields; GeneratedBundle is both the runtime and storage model)

AppConfig
├── project: ProjectConfig
├── author: AuthorConfig
├── milestones: list[str]
├── changelog: list[str]
├── llm: LLMConfig
└── schedule: ScheduleConfig

EnvConfig
├── telegram_bot_token: SecretStr
├── telegram_chat_id: str
└── api_keys: dict[str, SecretStr]
```

**`SecretStr` note:** Pydantic's `SecretStr` type is used for `telegram_bot_token` and all API key values. `SecretStr` values do not expose their content in `str()` or `repr()` calls, providing a secondary line of defence against accidental logging — complementing the explicit `RedactionFilter`.

---

#### `history.py` — History Manager

**Responsibility:** All read, write, query, and prune operations on `history.json`. The application's single interface to persistent state.

**Public API:**

```python
load(path: Path) -> list[GenerationRecord]
# Reads history.json. On FileNotFoundError: creates empty history, logs info.
# On JSONDecodeError: backs up to .bak, creates empty history, logs warning.
# Returns list of GenerationRecord (max 30).

save(records: list[GenerationRecord], path: Path) -> None
# Prunes to 30 records (oldest first). Writes atomically:
# 1. Serialize to JSON string
# 2. Write to history.json.tmp
# 3. os.replace(tmp, history.json)   ← atomic on POSIX and Windows (NTFS)
# On OSError: logs warning, does not raise (delivery proceeds).

get_promo_ratio(records: list[GenerationRecord], window_days: int = 14) -> float
# Returns fraction of records in last window_days that are promotional.
# Returns 0.0 if no records in window.

get_recent_pillars(records: list[GenerationRecord], n: int = 7) -> list[str]
# Returns pillar values from the n most recent records.

get_today_record(records: list[GenerationRecord]) -> GenerationRecord | None
# Returns the record whose date matches today's date in local timezone, or None.

get_deduplication_context(records: list[GenerationRecord], n: int = 10) -> list[str]
# Returns list of text summaries from the n most recent records for LLM dedup prompt.

update_today_platform(records, platform: str, post: PlatformPost) -> list[GenerationRecord]
# Used by /regenerate. Finds today's record, replaces the specified platform post.
# Returns updated records list (caller must call save()).
```

**Atomic write rationale:** `os.replace()` is atomic on POSIX filesystems and atomic on NTFS (Windows) when source and destination are on the same volume. Writing to `.tmp` first ensures that a power failure during the write leaves either the old complete file or the new complete file — never a partial write.

---

#### `prompts.py` — Prompt Builder

**Responsibility:** Construct the system and user prompts passed to LiteLLM. Apply sanitization to all user-supplied config values before embedding. Define the LLM output format contract.

**`sanitize_for_prompt(value: str, max_length: int) -> str`:**

Applied to all `AppConfig` string fields before prompt inclusion. Rules (full specification in BDD v0.3, Section 10.3):
- Strip whitespace
- Truncate to `max_length` with `…` suffix
- Replace instruction-injection patterns with `[removed]`
- Escape template delimiters (`{`, `}`)

**LLM output format contract:**

The system prompt instructs the LLM to return a JSON object matching this schema:

```json
{
  "x": {
    "text": "string (≤280 chars)",
    "format_type": "string",
    "image_suggestion": "string"
  },
  "linkedin": {
    "text": "string (≤1500 chars)",
    "format_type": "string",
    "image_suggestion": "string"
  },
  "threads": {
    "text": "string (≤500 chars)",
    "format_type": "string",
    "image_suggestion": "string"
  },
  "is_promotional": "boolean"
}
```

The system prompt explicitly instructs: return JSON only, no preamble, no markdown fences, no explanation. `generator.py` strips any accidental markdown fences before parsing.

---

#### `generator.py` — Content Generation Engine

**Responsibility:** Orchestrate the full generation pipeline from config + history inputs to a validated `GeneratedBundle` output. Manage LiteLLM call and retry logic.

**Pipeline sequence:**

```
resolve_pillar(day_of_week, recent_pillars) -> Pillar
calculate_promo_constraint(promo_ratio) -> bool (force_value_driven)
build_prompt(config, pillar, force_value_driven, dedup_context) -> dict
call_llm(prompt, llm_config) -> str          (raw LLM response)
parse_response(raw: str) -> dict             (JSON parse + fence strip)
validate_output(parsed: dict) -> GeneratedBundle  (Pydantic validation)
```

**Retry implementation:**

```python
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = [1, 2, 4]

for attempt in range(MAX_ATTEMPTS):
    try:
        raw = call_llm(prompt, llm_config)
        parsed = parse_response(raw)
        bundle = validate_output(parsed)
        return bundle
    except (LLMCallError, ValidationError) as e:
        if attempt < MAX_ATTEMPTS - 1:
            log_warning(f"↻ Attempt {attempt+1}/{MAX_ATTEMPTS} failed. Retrying in {BACKOFF_SECONDS[attempt]}s…")
            time.sleep(BACKOFF_SECONDS[attempt])
        else:
            log_error(e)
            raise GenerationFailedError(f"LLM failed after {MAX_ATTEMPTS} attempts") from e
```

**`call_llm` error normalisation:** All LiteLLM exceptions are caught and re-raised as internal `LLMCallError` instances. This prevents LiteLLM's exception hierarchy from leaking into the orchestration layer and makes retry logic provider-agnostic.

---

#### `telegram_bot.py` — Delivery & Bot Command Handler

**Responsibility:** Two distinct sub-responsibilities, co-located because they share the bot client instance and auth logic.

**Sub-responsibility 1 — Message Delivery (`send_bundle`, `send_message`):**

```python
def send_bundle(bundle: GeneratedBundle, env: EnvConfig) -> None:
    message = format_bundle(bundle)          # returns MarkdownV2 string
    send_with_retry(message, env)            # 3 attempts, exponential backoff

def send_with_retry(message: str, env: EnvConfig) -> None:
    for attempt in range(MAX_ATTEMPTS):
        try:
            bot.send_message(chat_id=env.telegram_chat_id,
                             text=message,
                             parse_mode=ParseMode.MARKDOWN_V2)
            return
        except TelegramError as e:
            if is_credential_error(e):       # 401/400 → no retry
                raise DeliveryCredentialError(str(e)) from e
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(BACKOFF_SECONDS[attempt])
            else:
                raise DeliveryFailedError(...) from e
```

**Message splitting logic:** `format_bundle()` returns either one message string (if ≤4,096 chars) or a list of three message strings (one per platform section). `send_with_retry` accepts either form and iterates if a list is returned.

**Sub-responsibility 2 — Bot Command Handlers:**

All handlers follow the same structure:

```python
async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. AUTHORIZE
    if not is_authorized(update.effective_user.id, env.telegram_chat_id):
        logger.debug("Unauthorized command attempt discarded.")
        return                               # silent discard

    # 2. EXECUTE
    ...

    # 3. RESPOND
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN_V2)
```

**Polling vs. Webhook:** Postware uses **long-polling** (`Application.run_polling()`), not webhooks. Rationale: webhooks require a publicly reachable HTTPS endpoint, which contradicts the local-machine-only architecture. Long-polling requires no inbound network access and works correctly on any developer machine including those behind NAT or firewalls.

**Concurrency note:** `python-telegram-bot` v20+ is async. The bot's polling loop and the APScheduler daemon are the only two concurrent execution contexts in the application. When `postware start` is running, APScheduler uses a `BackgroundScheduler` and the Telegram bot uses `Application.run_polling()` on the main thread's event loop. The scheduled job is submitted to the event loop via `asyncio.run_coroutine_threadsafe()`.

---

#### `scheduler.py` — APScheduler Daemon

**Responsibility:** Initialize APScheduler with a daily `CronTrigger`; register the generation pipeline as the scheduled job; handle graceful shutdown on SIGINT/SIGTERM.

**Scheduler configuration:**

```python
scheduler = BlockingScheduler(timezone="local")
scheduler.add_job(
    func=run_generation_pipeline,
    trigger=CronTrigger(hour=HH, minute=MM),   # parsed from config.schedule.time
    id="daily_generation",
    replace_existing=True,
    misfire_grace_time=3600                    # if system was asleep, run within 1 hour
)
```

**`misfire_grace_time=3600` rationale:** Developer machines sleep and wake. If the scheduled time passes while the machine is asleep, APScheduler will still execute the job when the machine wakes, provided it wakes within the grace period (1 hour). This prevents missed posts due to laptop sleep cycles without requiring an always-on machine.

**Graceful shutdown:**

```python
import signal

def handle_shutdown(signum, frame):
    logger.info("⚡ Shutdown signal received. Stopping Postware daemon.")
    scheduler.shutdown(wait=True)              # wait=True: let running job complete
    sys.exit(0)

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)
```

---

#### `platform_utils.py` — File Permission Management

**Responsibility:** Apply restrictive file permissions to sensitive files on both Unix and Windows. Called only by `main.py` during `init`.

**Platform dispatch:**

```python
def harden_file(path: Path) -> HardeningResult:
    if sys.platform == "win32":
        return _harden_windows(path)
    else:
        return _harden_unix(path)

def _harden_unix(path: Path) -> HardeningResult:
    try:
        os.chmod(path, 0o600)
        return HardeningResult(success=True, method="chmod-600")
    except OSError as e:
        return HardeningResult(success=False, error=str(e))

def _harden_windows(path: Path) -> HardeningResult:
    try:
        import win32security          # pywin32 — optional dependency
        return _harden_windows_pywin32(path)
    except ImportError:
        return _harden_windows_icacls(path)

def _harden_windows_icacls(path: Path) -> HardeningResult:
    username = os.environ.get("USERNAME", "")
    r1 = subprocess.run(["icacls", str(path), "/inheritance:r"], capture_output=True)
    r2 = subprocess.run(["icacls", str(path), f"/grant:r", f"{username}:(R,W)"], capture_output=True)
    if r1.returncode == 0 and r2.returncode == 0:
        return HardeningResult(success=True, method="icacls")
    return HardeningResult(success=False, error=r2.stderr.decode())
```

---

### Shared Logger Configuration

The shared logger is configured once in `main.py` at process startup and used by all modules via `logging.getLogger("postware")`.

```
Logger: "postware"
├── Handler: StreamHandler (stderr)
│   ├── Level: WARNING (non-interactive) / INFO (interactive)
│   ├── Formatter: Rich-based (via RichHandler)
│   └── Filter: RedactionFilter      ← strips API keys from all records
└── Handler: FileHandler (errors.log, mode="a")
    ├── Level: WARNING
    ├── Formatter: "%(asctime)s [%(levelname)s] %(module)s: %(message)s"
    └── Filter: RedactionFilter      ← same filter on file handler
```

**`RedactionFilter` implementation:** Subclasses `logging.Filter`. On `filter(record)`:
1. Formats the record message to a string.
2. Iterates the redaction replacement pairs compiled at startup (from `EnvConfig` secret values + regex patterns).
3. Replaces any match in the formatted string.
4. Re-sets `record.msg` to the redacted string and clears `record.args`.
5. Returns `True` (always — this is a mutation filter, not a gating filter).

---

## Step 7: Inter-Module Communication Patterns

All communication between modules is **synchronous in-process function calls**. No message queues, no event buses, no shared mutable state between modules (except the logger and the `EnvConfig` instance passed through the call chain).

**Data passing convention:**

```
main.py
  │
  ├─ config.py.load() ──────────────────────> AppConfig, EnvConfig
  │                                                │
  ├─ history.py.load() ─────────────────────> list[GenerationRecord]
  │                                                │
  ├─ generator.py.generate(config, records) ──> GeneratedBundle
  │                                                │
  ├─ history.py.save(records + new_record) ──> None (side effect)
  │                                                │
  └─ telegram_bot.py.send_bundle(bundle, env) > None (side effect)
```

No module modifies another module's data. `generator.py` returns a new `GeneratedBundle`; it does not write to history. `history.py.save()` is called by `main.py` (or `telegram_bot.py` for `/regenerate`), not by `generator.py`. This makes the pipeline testable at each boundary: every function is a pure transformation or an explicit I/O operation.

---

## Step 8: Error Handling Architecture

### Error Type Hierarchy

```
PostwareError (base)
├── ConfigError           — config.py: config/env load or validation failure
├── HistoryError          — history.py: non-recoverable history operation
│   └── HistoryWriteError — subclass: write failed (non-fatal; delivery proceeds)
├── GenerationError       — generator.py
│   ├── LLMCallError      — API call failed (retryable)
│   ├── LLMOutputError    — output validation failed (retryable)
│   └── GenerationFailedError  — all retries exhausted (fatal)
└── DeliveryError         — telegram_bot.py
    ├── DeliveryCredentialError  — bad token/chat ID (fatal, no retry)
    └── DeliveryFailedError      — network/API failure after retries (fatal)
```

**Handling convention:**
- `ConfigError` → caught by `main.py`; Rich-formatted output; exit code 1; no API calls made
- `HistoryWriteError` → caught by `main.py`; warning logged; delivery continues; exit code 0 if delivery succeeds
- `GenerationFailedError` → caught by `main.py`; error logged; exit code 1; no Telegram delivery; history not modified
- `DeliveryCredentialError` → caught by `main.py`; error logged; exit code 1
- `DeliveryFailedError` → caught by `main.py`; error logged; exit code 1; posts were generated (noted in error message)
- All unhandled exceptions → caught by top-level handler in `main.py`; logged to `errors.log` with traceback; exit code 1

---

## Step 9: Testing Architecture

### Test Strategy

| Layer | Test Type | Tools | Coverage Target |
|---|---|---|---|
| `models.py` | Unit | pytest | 100% — pure data models; all validation rules |
| `config.py` | Unit | pytest + tmp_path fixture | All valid/invalid config permutations; all missing field combinations |
| `history.py` | Unit | pytest + tmp_path | Load/save/prune/corrupt recovery/atomic write; all public API methods |
| `prompts.py` | Unit | pytest | Sanitization rules; injection pattern removal; prompt structure |
| `generator.py` | Unit (mocked LiteLLM) | pytest + unittest.mock | Retry logic (3 failure paths); output parsing; promo ratio enforcement |
| `telegram_bot.py` | Unit (mocked bot) | pytest + unittest.mock | Message formatting; splitting logic; authorization check; all bot commands |
| `platform_utils.py` | Unit (mocked os/subprocess) | pytest + unittest.mock | Unix chmod; Windows pywin32 path; Windows icacls fallback; unsupported case |
| `main.py` | Integration | pytest + subprocess | Each CLI command end-to-end with mocked LiteLLM and Telegram |

### Key Test Fixtures

```python
@pytest.fixture
def valid_config(tmp_path) -> Path:
    """Write a valid config.yaml to tmp_path and return the path."""

@pytest.fixture
def valid_env(monkeypatch):
    """Set all required env vars for the configured provider."""

@pytest.fixture
def history_with_records(tmp_path) -> Path:
    """Write history.json with 10 sample GenerationRecord entries."""

@pytest.fixture
def mock_litellm_success(monkeypatch):
    """Patch litellm.completion() to return a valid GeneratedBundle JSON."""

@pytest.fixture
def mock_litellm_fail_then_succeed(monkeypatch):
    """Patch litellm.completion() to fail once then succeed on retry."""

@pytest.fixture
def mock_telegram_send(monkeypatch):
    """Patch bot.send_message() to capture sent messages without network calls."""
```

### Critical Test Cases

| ID | Scenario | Assertion |
|---|---|---|
| T-01 | `generate` with missing `config.yaml` | Exit code 1; error message contains "config.yaml not found"; zero API calls |
| T-02 | `generate` with promo ratio at 22% | `is_promotional=False` in generated bundle; info message emitted |
| T-03 | LLM returns malformed JSON on attempts 1 and 2, valid on attempt 3 | Bundle returned; two retry warnings logged; exit code 0 |
| T-04 | LLM fails all 3 attempts | `GenerationFailedError` raised; exit code 1; `errors.log` contains error details; history.json unchanged |
| T-05 | `history.json` contains 30 records; new record saved | history.json contains exactly 30 records after save (oldest pruned) |
| T-06 | `history.json` contains corrupt JSON | `.bak` file created; fresh history created; warning logged; pipeline continues |
| T-07 | Telegram message body is 5,000 chars | Three separate messages sent (split by platform section) |
| T-08 | Unauthorized Telegram user sends `/generate` | Handler returns without executing pipeline; no LLM call; no reply sent |
| T-09 | API key logged in exception message | `errors.log` content does not contain the key value; `[REDACTED]` token present instead |
| T-10 | `init` on Unix system | `.env` has mode `0o600`; `config.yaml` has mode `0o600`; `history.json` has mode `0o600` |
| T-11 | `sanitize_for_prompt()` with injection string | Output contains `[removed]`; original injection phrase absent |
| T-12 | `postware status` with no history | Status panel rendered; "No generation history" message; exit code 0 |

---

## Step 10: Build, Packaging & Distribution

### `pyproject.toml` Structure

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "postware"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "litellm",
    "python-telegram-bot>=20.0",
    "pyyaml",
    "python-dotenv",
    "pydantic>=2.0",
    "apscheduler>=3.10",
    "rich",
]

[project.optional-dependencies]
windows = ["pywin32"]
dev = [
    "pytest",
    "pytest-asyncio",
    "pip-audit",
]

[project.scripts]
postware = "postware.main:cli"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**`[project.scripts]` entry point:** Defining `postware` as a console script entry point means users can invoke `postware generate` directly after `pip install`, in addition to `python -m postware generate`. Both invocation styles are supported.

**Version strategy:** Starts at `0.1.0`. Semantic versioning: MAJOR.MINOR.PATCH. v0.x = P0 feature set (functional MVP); v1.0.0 = P1 feature set (production-ready). Breaking changes to `history.json` schema increment MAJOR.

---

## Step 11: Architecture Decision Records (ADR) Index

| ID | Decision | Status | Document Section |
|---|---|---|---|
| ADR-001 | JSON flat file over SQLite for history storage | Accepted | Step 4 |
| ADR-002 | LiteLLM as unified LLM interface | Accepted | Step 5 |
| ADR-003 | python-telegram-bot over direct httpx calls | Accepted | Step 5 |
| ADR-004 | Long-polling over webhooks for Telegram bot | Accepted | Step 6 (`telegram_bot.py`) |
| ADR-005 | `argparse` (stdlib) over Click/Typer for CLI | Accepted | Step 6 (`main.py`) |
| ADR-006 | `APScheduler` `misfire_grace_time=3600` for laptop sleep tolerance | Accepted | Step 6 (`scheduler.py`) |
| ADR-007 | `SecretStr` in `EnvConfig` as secondary credential protection | Accepted | Step 6 (`models.py`) |
| ADR-008 | `os.replace()` for atomic history writes | Accepted | Step 6 (`history.py`) |

### ADR-004: Long-Polling vs. Webhooks

**Decision ID:** ADR-004
**Status:** Accepted

**Decision:** Long-polling via `Application.run_polling()`.

**Rationale:**

| Factor | Long-Polling | Webhooks |
|---|---|---|
| Inbound network access required | ❌ No — outbound only | ✅ Yes — requires public HTTPS URL |
| Works behind NAT/firewall | ✅ Yes | ❌ No without tunnel (ngrok, etc.) |
| Works on local machine | ✅ Always | ❌ Only with additional infrastructure |
| Setup complexity | ✅ Zero config | ❌ HTTPS cert + reverse proxy or tunnel |
| Appropriate for local tool | ✅ Yes | ❌ No |

**Consequence:** Long-polling introduces a persistent outbound connection to the Telegram API. This is acceptable for a long-running daemon (`postware start`). For one-shot `generate` runs, the Telegram bot is not polled — only the `send_message` API is called directly.

### ADR-005: `argparse` vs. Click/Typer

**Decision ID:** ADR-005
**Status:** Accepted

**Decision:** Python stdlib `argparse`.

**Rationale:** Postware has four subcommands with no nested subcommands, no complex option types, and no interactive prompts (beyond the `init` overwrite confirmation). Click and Typer are excellent frameworks but introduce a dependency for functionality that `argparse` handles completely. For a four-subcommand CLI, stdlib is the correct choice. If the command surface grows significantly in a future version, migration to Click or Typer is straightforward.

---

## Step 12: Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | LiteLLM drops support for a provider mid-use | Low | High (generation fails) | Pinned minor version in `pyproject.toml`; `pip-audit` catches CVEs; migration to direct SDK is a config + import change |
| R-02 | Telegram Bot API deprecates long-polling | Very Low | High (bot commands fail) | `python-telegram-bot` library tracks Telegram API changes; update library to adopt webhook alternative |
| R-03 | LLM provider changes output format (JSON wrapping) | Medium | Medium (parse fails) | Retry logic + fence-stripping in `parse_response()` handles most format drift; Pydantic validation provides clear failure signal |
| R-04 | `history.json` corruption (disk failure mid-write) | Very Low | Low (history reset; posts still delivered) | Atomic write via `os.replace()`; `.bak` file on corrupt detection |
| R-05 | API key exposed via poorly-handled exception | Low | High (credential compromise) | `SecretStr` in models; `RedactionFilter` on all log handlers; two independent layers |
| R-06 | pip-audit finds CRITICAL CVE in LiteLLM transitive dep | Medium | High (supply chain) | `init` audit + `scripts/audit_deps.py` for scheduled audits; `pip install --upgrade` to patch |
| R-07 | LLM cost spike from repeated `/generate` bot calls | Low | Medium (unexpected API bill) | Telegram sender authorization blocks unauthorized callers; user controls their own usage |
| R-08 | `misfire_grace_time` causes duplicate run on wake | Very Low | Low (extra post generated) | APScheduler's `replace_existing=True` and single job ID prevent duplicate scheduling; duplicate runs are noted as acceptable in PRD |
| R-09 | Windows ACL hardening fails silently | Low | Medium (credentials exposed to local users) | `HardeningResult` struct surfaces failure to `main.py`; warning printed to terminal and logged |
| R-10 | Python version < 3.10 on user machine | Low | High (tool fails to start) | Python version check at process startup with clear error and upgrade URL before any other logic executes |

---

## Step 13: Implementation Roadmap

### v0 — Functional MVP (P0 Features)

Deliver a working, single-use generation and delivery tool. No security hardening. No bot interactivity. No daemon.

| Module | Deliverable |
|---|---|
| `models.py` | All Pydantic models defined; all validators passing |
| `config.py` | YAML + .env load; Pydantic validation; `ConfigError` |
| `history.py` | Full public API; atomic write; corruption recovery; prune-to-30 |
| `prompts.py` | Prompt construction (without sanitization — added in v1) |
| `generator.py` | LiteLLM call; retry logic; output parsing; `GeneratedBundle` output |
| `telegram_bot.py` | `send_bundle()` and `send_message()` delivery only; no bot command handlers |
| `main.py` | `generate` and `status` subcommands; Python version check; shared logger (without `RedactionFilter` — added in v1) |
| `init` support | `generate starter config.yaml`, `.env`, `history.json`; print checklist; no permission hardening (added in v1) |
| Tests | T-01 through T-06, T-12 |

**v0 exit criteria:** `python -m postware generate` runs end-to-end; posts delivered to Telegram; history updated; errors logged; exit codes correct.

---

### v1 — Production-Ready (P1 Features)

Add all security measures, bot commands, retry logic, and daemon mode. Suitable for daily use on a professional machine.

| Module | Deliverable |
|---|---|
| `models.py` | `SecretStr` on `EnvConfig` credential fields |
| `config.py` | API key format validation (warnings) |
| `prompts.py` | `sanitize_for_prompt()` applied to all `AppConfig` string fields |
| `telegram_bot.py` | Bot command handlers (`/generate`, `/regenerate`, `/status`); sender authorization; message splitting |
| `scheduler.py` | APScheduler daemon; SIGINT/SIGTERM graceful shutdown |
| `platform_utils.py` | Unix chmod; Windows pywin32 + icacls; `HardeningResult` |
| `main.py` | `RedactionFilter` on all log handlers; `start` subcommand; `init` with permission hardening + pip-audit |
| `scripts/audit_deps.py` | Standalone dependency scanner; exit code 1 on HIGH/CRITICAL CVE |
| Tests | Full test suite T-01 through T-12 + bot command tests + security tests |

**v1 exit criteria:** All P1 features operational; all security measures active; full test suite passing; `pip-audit` clean on `pip install postware`.

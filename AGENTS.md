# AGENTS.md

## Project Overview

**Product:** Postware
**Description:** A Python CLI tool that automatically generates three platform-optimized social media posts per day — for X (Twitter), LinkedIn, and Threads — and delivers them as a single formatted bundle to the developer's Telegram chat. It is built exclusively for solo developers and indie hackers who are building in public and need a consistent social media presence without sacrificing engineering time. The tool enforces a five-pillar weekly content strategy, an 80/20 value-to-promotion ratio, and topic deduplication using a local JSON history file, with LLM flexibility powered by LiteLLM.

**Target Users:** Solo software developers, indie hackers, and technical founders aged 25–40 who are actively building in public, comfortable with CLI tools and YAML configuration, and want to maintain a daily posting cadence across three platforms with zero daily writing effort.

**Core Features:**

- Content generation engine with five weighted content pillars (Build in Public, Teaching, Opinions, Data & Results, Community), weekly pillar schedule, and 80/20 value-to-promotion ratio enforcement
- Platform-specific formatting for X (≤280 chars, casual tone), LinkedIn (≤1,500 chars, professional tone), and Threads (≤500 chars, conversational tone)
- LiteLLM unified interface supporting cloud providers (Anthropic, OpenAI, Groq, Google, DeepSeek, Qwen, Minimax, Kimi, Z.ai) and local models (Ollama, LM Studio, custom endpoints)
- File-based post history (`history.json`, max 30 records) for pillar rotation, promotional ratio tracking, and topic deduplication
- Telegram delivery of formatted post bundles with per-platform headers, image suggestions, and a metadata footer
- Telegram bot commands: `/generate` (full pipeline), `/regenerate` (single-platform regeneration with inline keyboard), `/status` (content stats)
- CLI commands: `generate` (one-shot run), `start` (APScheduler daemon), `status` (terminal stats panel), `init` (file scaffolding and security hardening)
- Error logging to `errors.log` with automatic retry (3 attempts, exponential backoff) for LLM and Telegram API calls
- Security measures: Telegram sender authorization, log redaction filter for API keys, prompt injection sanitization, file permission hardening (`0o600` on Unix; Windows ACLs), API key format validation, and dependency auditing via `pip-audit`

**Constraints:**

- No database libraries (no SQLite, no ORM) — `history.json` is the only persistent store
- No web server, no port binding, no network-facing service
- No direct posting to social media APIs — user copies and pastes manually
- Single-user, single-process, local machine execution only
- Python 3.10+ required on macOS, Linux, and Windows
- End-to-end pipeline must complete in ≤60 seconds under normal conditions with a cloud LLM provider

---

## Technology Stack

| Layer | Technology | Version Constraint | Justification |
| --- | --- | --- | --- |
| Language | Python | ≥3.10 | Target persona is comfortable with Python; structural pattern matching and modern type hints required; broadest developer machine coverage |
| LLM Interface | LiteLLM | Latest stable | Single unified `litellm.completion()` interface for 13+ providers; local model support via `base_url`; eliminates per-provider integration code |
| Telegram | python-telegram-bot | ≥20.0 (async) | Native async/await; built-in inline keyboard management, handler routing, MarkdownV2 helpers, and long-polling loop |
| Configuration | PyYAML + python-dotenv | Latest stable | YAML is human-readable and editable for developer tool config; `.env` is the established standard for credential management |
| Data Validation | Pydantic | v2 | Fast, type-safe schema validation; excellent error messages; first-class Python type hint integration; `SecretStr` for credential protection |
| Scheduling | APScheduler | ≥3.10 | Lightweight in-process scheduler with `CronTrigger` and `misfire_grace_time` for laptop sleep tolerance; no external broker required |
| Terminal Output | Rich | Latest stable | Best-in-class Python terminal formatting; panels, tables, progress bars, ANSI color, and `NO_COLOR` support |
| CLI Parsing | argparse (stdlib) | Built-in | Four subcommands with no nested depth; stdlib is correct for this surface area; no third-party dependency required |
| Data Storage | JSON flat file | Built-in `json` module | Zero dependencies; human-readable and editable; sufficient for ≤30 records; atomic writes via `os.replace()` |
| File Permissions | `os` (stdlib) + optional `pywin32` | pywin32: latest stable | `os.chmod()` for Unix; `pywin32` preferred for Windows ACLs with `icacls` subprocess fallback |
| Dependency Audit | pip-audit | Latest stable (dev/optional) | PyPA-maintained; queries OSV database; no API key required; JSON output; run during `init` and via `scripts/audit_deps.py` |
| Testing | pytest + pytest-asyncio | Latest stable | Industry standard; fixture model well-suited to CLI and async bot testing patterns |

---

## System Architecture

**Pattern:** Modular Monolith — Single-Process CLI Application

```text
┌──────────────────────────────────────────────────────────────────┐
│                        PROCESS BOUNDARY                          │
│                                                                  │
│   main.py  (Composition Root & CLI Entrypoint)                   │
│      │                                                           │
│      ├── config.py ──────── AppConfig, EnvConfig (Pydantic)      │
│      │        │                                                  │
│      │        └── models.py  (All data shapes — no imports)      │
│      │                                                           │
│      ├── history.py ──────── history.json (≤30 records, atomic)  │
│      │        └── models.py                                      │
│      │                                                           │
│      ├── generator.py ────── LiteLLM orchestration + retry       │
│      │        ├── config.py                                      │
│      │        ├── history.py                                     │
│      │        ├── prompts.py  (sanitize_for_prompt + builder)    │
│      │        └── models.py  (GeneratedBundle, PlatformPost)     │
│      │                                                           │
│      ├── telegram_bot.py ─── Delivery + Bot command handlers     │
│      │        ├── generator.py  (for /generate, /regenerate)     │
│      │        ├── history.py    (for /status, /regenerate check) │
│      │        └── models.py                                      │
│      │                                                           │
│      ├── scheduler.py ─────── APScheduler daemon (start command) │
│      │        └── generator.py                                   │
│      │                                                           │
│      └── platform_utils.py ── File permission hardening (init)   │
│                                                                  │
│   Shared Logger ─── RedactionFilter on ALL handlers              │
│                      StreamHandler (stderr) + FileHandler (errors.log) │
└──────────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
   ┌────────────┐                    ┌─────────────────┐
   │  LiteLLM   │                    │  Telegram        │
   │  (unified) │                    │  Bot API         │
   └─────┬──────┘                    └─────────────────┘
         │
   ┌─────┴──────────────────────────────────────────────────┐
   │  LLM PROVIDERS                                          │
   │  anthropic · openai · groq · google · deepseek · qwen  │
   │  minimax · kimi · z.ai · ollama · lmstudio · custom    │
   └─────────────────────────────────────────────────────────┘
```

**Dependency layering rule (strict, no exceptions):**

- `models.py` has zero internal imports — it is the dependency floor
- `config.py` and `history.py` import only `models.py`
- `prompts.py` imports only `models.py` — no network calls, no file I/O
- `generator.py` imports `config`, `history`, `prompts`, `models` — orchestrates; does not deliver
- `telegram_bot.py` imports `generator`, `history`, `models` — delivers; does not generate independently
- `main.py` is the only module that imports everything — it is the composition root
- Circular dependencies are structurally impossible within this layering

**Telegram polling model:** Long-polling via `Application.run_polling()` — requires no public HTTPS endpoint, works behind NAT/firewall, correct for a local-machine tool. For one-shot `generate` runs, only `bot.send_message()` is called; polling is not activated.

---

## Repository Structure

```text
postware/
├── pyproject.toml
├── .env.example
├── .gitignore                  # Must exclude .env, config.yaml, history.json, errors.log
├── config.yaml                 # Generated by `init`; user-maintained
├── history.json                # Generated by `init` or on first run; auto-managed
├── errors.log                  # Append-only; generated at runtime
├── README.md
├── AGENTS.md
├── src/
│   └── postware/
│       ├── __init__.py
│       ├── main.py             # CLI entrypoint, composition root, shared logger setup
│       ├── config.py           # config.yaml + .env loader, Pydantic validation, key format check
│       ├── models.py           # All Pydantic data models — dependency floor
│       ├── generator.py        # Content generation engine, LiteLLM calls, retry logic
│       ├── prompts.py          # Prompt builder, sanitize_for_prompt(), LLM output schema
│       ├── history.py          # history.json read/write/query/prune, atomic writes
│       ├── telegram_bot.py     # Telegram delivery, bot command handlers, sender auth
│       ├── scheduler.py        # APScheduler daemon, SIGINT/SIGTERM graceful shutdown
│       └── platform_utils.py   # File permission hardening (Unix chmod + Windows ACL)
├── tests/
│   ├── conftest.py             # Shared fixtures
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_config.py
│   │   ├── test_history.py
│   │   ├── test_prompts.py
│   │   ├── test_generator.py
│   │   ├── test_telegram_bot.py
│   │   └── test_platform_utils.py
│   └── integration/
│       └── test_cli.py         # End-to-end CLI command tests with mocked LLM and Telegram
└── scripts/
    └── audit_deps.py           # Standalone dependency scanner; exits code 1 on HIGH/CRITICAL CVE
```

### File Placement Rules

| File Type | Location | Notes |
| --- | --- | --- | --- |
| Pydantic data models | `src/postware/models.py` | All models in one file; the dependency floor |
| Config loading logic | `src/postware/config.py` | One module for both YAML and `.env` |
| History read/write/query | `src/postware/history.py` | All `history.json` I/O here; nowhere else |
| LLM prompt construction | `src/postware/prompts.py` | No network calls; no file I/O |
| Generation pipeline | `src/postware/generator.py` | Orchestration only; calls prompts, history, LiteLLM |
| Telegram delivery + bot | `src/postware/telegram_bot.py` | Delivery and bot handlers co-located (shared bot client) |
| APScheduler daemon | `src/postware/scheduler.py` | Daemon logic isolated from generation |
| File permission logic | `src/postware/platform_utils.py` | Called only by `main.py` during `init` |
| CLI entrypoint | `src/postware/main.py` | Composition root; imports all modules |
| Unit tests | `tests/unit/test_<module>.py` | One test file per source module |
| Integration tests | `tests/integration/test_cli.py` | Full CLI subcommand end-to-end tests |
| Dependency audit script | `scripts/audit_deps.py` | Standalone; not imported by application code |
| Runtime data files | Project root (`config.yaml`, `history.json`, `errors.log`) | Excluded from version control via `.gitignore` |
| Secrets | `.env` (project root) | Never committed; `.env.example` committed with placeholders |

---

## Agent Roles

### Planner Agent

**Purpose:** Decompose feature requests and version milestones into ordered, atomic development tasks mapped to specific modules and acceptance criteria.

**Inputs:**

- Feature description, user story, or bug report
- Current version target (v0 = P0 features only; v1 = P0 + P1 features)
- PRD feature prioritization table (P0 Must / P1 Should)
- Module architecture and dependency layering from this AGENTS.md

**Outputs:**

- Ordered task list with priorities (P0, P1) and complexity estimates (S, M, L, XL)
- Dependency graph between tasks — no task may begin before its dependency is complete
- Per-task specification: which module is affected, which files are created or modified, what the acceptance criterion is

**Rules:**

1. Every task must target exactly one module (e.g., `history.py`, `generator.py`). Tasks that span multiple modules must be split.
2. v0 tasks must be planned and completed before any v1 task begins. v0 exit criterion: `python -m postware generate` runs end-to-end with posts delivered to Telegram, history updated, and errors logged.
3. Every task must specify which of the 12 critical test cases (T-01 through T-12) it unlocks or satisfies.
4. Tasks involving `models.py` must be scheduled before any module that depends on the models being defined.
5. Security measures (Telegram auth, log redaction, prompt sanitization, file permissions, key validation, dependency audit) are P1 tasks and must be planned as a discrete block after v0 is complete.
6. No task may be marked complete unless its stated acceptance criterion is met and its corresponding test passes.

**Works With:** Developer Agent, Tester Agent

---

### Developer Agent

**Purpose:** Implement all application modules in strict conformance with the technical architecture, module dependency rules, and coding standards defined in this document.

**Inputs:**

- Task specification from Planner Agent (module, files, acceptance criterion)
- Module architecture and dependency layering rules from this AGENTS.md
- Data schema definitions (`GenerationRecord`, `AppConfig`, `EnvConfig`, `GeneratedBundle`, `PlatformPost`)
- BDD scenarios for the feature being implemented

**Outputs:**

- Implemented module code passing all linting, formatting, and type-checking gates
- Updated `pyproject.toml` if new dependencies are introduced
- Inline docstrings for all public functions

**Rules:**

1. Never import a module that violates the dependency layering: `models.py` has zero internal imports; `config.py` and `history.py` import only `models.py`; `prompts.py` imports only `models.py`; `generator.py` imports config, history, prompts, models; `telegram_bot.py` imports generator, history, models; `main.py` imports everything. Circular imports are a blocking error.
2. Never use a database library. All persistence goes through `history.py` using the JSON flat file pattern. Atomic writes must use `os.replace()` via a `.tmp` file.
3. All LiteLLM exceptions must be caught in `generator.py` and re-raised as internal `LLMCallError` instances. No LiteLLM exception types may leak into the orchestration layer.
4. All log statements must go through `logging.getLogger("postware")`. Never use `print()` for logging. Rich is used only for terminal user-facing output, not for log records.
5. Retry logic (3 attempts, backoff 1s/2s/4s) must be implemented identically in `generator.py` (LLM) and `telegram_bot.py` (Telegram delivery). Invalid credentials (`401` / `400` on first attempt) must not be retried — raise `DeliveryCredentialError` immediately.
6. All `AppConfig` string fields must be passed through `sanitize_for_prompt()` in `prompts.py` before embedding in the LLM prompt. Raw config values must never appear directly in prompt strings.
7. `EnvConfig` must use Pydantic `SecretStr` for `telegram_bot_token` and all API key fields. `SecretStr` values must never be coerced to plain strings except when constructing the LiteLLM or Telegram API call.
8. `platform_utils.py` must be called only from `main.py` during `init`. No other module may import it.
9. The Python version check (`sys.version_info >= (3, 10)`) must be the first logic executed in `main.py`, before any import of application modules.
10. `sys.stdout.isatty()` must be checked at startup. When `False` (cron/daemon context), all Rich progress indicators and spinners must be suppressed; only the final outcome line is emitted.

**Works With:** Planner Agent, Tester Agent, Reviewer Agent

---

### Tester Agent

**Purpose:** Write, maintain, and execute the full test suite covering all modules, all 12 critical test cases, and all BDD scenarios defined in the specification.

**Inputs:**

- Implemented module code from Developer Agent
- 12 critical test cases (T-01 through T-12) from the Technical Architecture Document
- BDD scenarios from the Backend Design Document (v0.2)
- Error type hierarchy from the Technical Architecture Document

**Outputs:**

- Test files in `tests/unit/test_<module>.py` (one per source module) and `tests/integration/test_cli.py`
- `conftest.py` with all shared fixtures
- Coverage report showing ≥90% coverage on `models.py` and `history.py`; ≥80% on all other modules
- Test run output confirming all tests pass before handing off to Reviewer Agent

**Rules:**

1. All 12 critical test cases (T-01 through T-12) must have corresponding test functions. No test case may be omitted or approximated.
2. LiteLLM (`litellm.completion()`) and Telegram bot (`bot.send_message()`) must always be mocked via `unittest.mock`. No real API calls in any test.
3. File system tests must use `pytest`'s `tmp_path` fixture. No test may read or write the real `history.json`, `config.yaml`, or `.env`.
4. Retry logic tests must verify both the retry sequence (warnings logged on attempts 1 and 2) and the final failure state (exit code 1, `errors.log` updated, `history.json` unchanged).
5. The `RedactionFilter` test (T-09) must confirm that the literal API key value is absent from `errors.log` and that `[REDACTED:...]` tokens are present in its place.
6. Authorization tests (T-08) must confirm that unauthorized Telegram user IDs result in zero LLM calls and zero replies — not just a logged warning.
7. All async bot handler tests must use `pytest-asyncio` with `asyncio_mode = "auto"`. No `asyncio.run()` calls in tests.
8. Tests must be deterministic — no random seeds, no time-dependent logic without mocking `datetime.date.today()`.

**Works With:** Developer Agent, Reviewer Agent

---

### Security Reviewer Agent

**Purpose:** Verify that all five v1 security measures are correctly implemented, non-bypassable, and consistent with the specifications in the Backend Design Document (v0.2), Section 10.

**Inputs:**

- Implemented `telegram_bot.py`, `config.py`, `prompts.py`, `main.py`, `platform_utils.py`
- Shared logger configuration in `main.py`
- Security specifications from BDD v0.2, Section 10 (10.1 through 10.7)
- Test results for security-related test cases (T-08, T-09, T-11)

**Outputs:**

- Security review report identifying any non-conformance with the five security measures
- Confirmed pass or explicit list of issues to be resolved by Developer Agent before merge

**Rules:**

1. **Telegram authorization (10.1):** Confirm that every bot command handler (`/generate`, `/regenerate`, `/status`) validates `update.effective_user.id` against `TELEGRAM_CHAT_ID` as the **first operation** before any application logic executes. Unauthorized senders must be silently discarded — verify that no response is sent and no LLM call is made.
2. **Log redaction (10.2):** Confirm that `RedactionFilter` is attached to **both** the `StreamHandler` and the `FileHandler` at logger setup time. Verify the redaction replacement pairs cover all provider-specific API keys in `EnvConfig` and the Telegram bot token. Confirm `SecretStr` in `EnvConfig` provides a second independent layer.
3. **Prompt sanitization (10.3):** Confirm `sanitize_for_prompt()` is called on all `AppConfig` string fields (`project.name`, `project.description`, `author.bio`, all `milestones` items, all `changelog` items) before any of these values appear in the LLM prompt. Verify the four sanitization rules: whitespace stripping, length truncation, injection pattern removal (`[removed]` replacement), and template delimiter escaping.
4. **File permissions (10.4 + 10.7):** On Unix, confirm `os.chmod(path, 0o600)` is called on `.env`, `config.yaml`, and `history.json` immediately after each is created during `init`. On Windows, confirm the pywin32 → icacls fallback chain is implemented in `platform_utils.py` and called from `main.py` during `init`. Confirm `os.chmod()` is never called on Windows.
5. **API key format validation (10.5):** Confirm format checks run during `generate` and `start` flows, before any external API call. Confirm validation failures produce a **warning** (non-blocking), not a hard exit. Confirm the warning message identifies the expected key format prefix.
6. **Dependency audit (10.6):** Confirm `scripts/audit_deps.py` exits with code 1 on HIGH or CRITICAL severity findings and code 0 otherwise. Confirm `pip-audit` absence is handled gracefully (warning, no block). Confirm `init` invokes the audit and reports findings without blocking completion.
7. No security measure may be bypassed via a configuration flag or environment variable. If a bypass mechanism is found, it is a blocking issue.

**Works With:** Developer Agent, Reviewer Agent

---

### Reviewer Agent

**Purpose:** Review all code for correctness, adherence to coding standards, module boundary compliance, and readiness for the target version milestone (v0 or v1).

**Inputs:**

- All implemented and tested code from Developer Agent
- Security review report from Security Reviewer Agent (v1 only)
- Test coverage report from Tester Agent
- This AGENTS.md coding standards and quality rules

**Outputs:**

- Line-level review comments for any standards violations, logic errors, or module boundary breaches
- Explicit approval (all issues resolved) or rejection with required fixes before re-review

**Rules:**

1. No code may be approved if it violates the module dependency layering. Any import that creates a cycle or violates the layer order is a blocking issue.
2. No code may be approved if it contains hardcoded API keys, bot tokens, model names, or base URLs. All such values must come from `AppConfig` or `EnvConfig`.
3. No code may be approved if it uses `print()` for logging, bypasses the shared logger, or omits `logger.getLogger("postware")` for any log-level message.
4. All public functions must have Google-style docstrings with `Args`, `Returns`, and `Raises` sections. Functions without docstrings are a blocking issue.
5. `errors.log` must never be read by application code — it is append-only. If any module opens `errors.log` for reading, it is a blocking issue.
6. The v0 milestone may be approved without security measures (v1 features). The v1 milestone requires a passed Security Reviewer report before approval.
7. Any commented-out code blocks in a commit are a blocking issue. Temporary debug statements must be removed.
8. The `history.json` pruning invariant must be verified in code review: the `save()` function in `history.py` must enforce exactly 30 records on every write, never more.

**Works With:** Developer Agent, Tester Agent, Security Reviewer Agent

---

## Development Workflow

| Step | Agent | Action | Artifact |
| --- | --- | --- | --- |
| 1 | Planner | Decompose the target version milestone (v0 or v1) into ordered tasks with module assignments and acceptance criteria | Ordered task list with priorities and dependency graph |
| 2 | Developer | Implement `models.py` first (dependency floor); all Pydantic models, enums, and error hierarchy | `models.py` with all data shapes passing `mypy --strict` |
| 3 | Developer | Implement `config.py` and `history.py` (depend only on `models.py`) | Config loader with `ConfigError`; history manager with atomic writes and corruption recovery |
| 4 | Developer | Implement `prompts.py` (no network, no I/O) | Prompt builder with `sanitize_for_prompt()` and LLM output schema |
| 5 | Developer | Implement `generator.py` (core pipeline, retry logic, LiteLLM integration) | Working generation engine returning `GeneratedBundle` |
| 6 | Developer | Implement `telegram_bot.py` (delivery + bot command handlers) | Delivery with retry; `/generate`, `/regenerate`, `/status` handlers; sender authorization (v1) |
| 7 | Developer | Implement `scheduler.py` and `platform_utils.py` (v1) | APScheduler daemon with graceful shutdown; file permission hardening for Unix and Windows |
| 8 | Developer | Implement `main.py` (composition root, CLI parsing, shared logger, `RedactionFilter`) | Fully wired CLI with all four subcommands, exit codes, and Rich terminal output |
| 9 | Tester | Write and run full test suite; confirm all 12 critical test cases pass | Test files in `tests/unit/` and `tests/integration/`; coverage report ≥80% on all modules |
| 10 | Security Reviewer | Review all five v1 security measures against BDD v0.2 Section 10 specifications (v1 milestone only) | Security review report with explicit pass or list of required fixes |
| 11 | Reviewer | Review all code for standards compliance, module boundary correctness, and milestone readiness | Approved code or rejection with required fixes |

### Workflow Rules

- No step may begin until the previous step's artifact is complete and verified.
- The module implementation order in Steps 2–8 must be followed. `models.py` first, always.
- If the Tester finds failures, control returns to the Developer Agent. No test may be skipped or marked as expected-failure without explicit justification.
- If the Reviewer rejects code, the Developer Agent receives the specific comments and fixes them before re-review. The Reviewer does not fix code.
- If the Security Reviewer identifies an issue, it is treated as a blocking P0 regardless of the severity classification and must be resolved before any v1 milestone approval.
- The v0 milestone (Steps 1–9 + 11, skipping Step 10) must be fully complete before any v1 work begins.

---

## Task Format

All tasks must use this structure:

```text
TASK: [TASK-ID]
Objective: [Single clear sentence describing what is implemented or fixed]
Priority: [P0 | P1]
Complexity: [S | M | L | XL]
Version: [v0 | v1]
Assigned To: [Agent Name]
Dependencies: [TASK-IDs or "None"]
Module: [src/postware/<module>.py]

Inputs:
- [What the agent receives to begin this task]
- [E.g., models.py with GenerationRecord defined]

Steps:
1. [Step 1]
2. [Step 2]
3. [Step 3]

Output:
- [Deliverable file or artifact]
- [E.g., history.py with load(), save(), get_promo_ratio() passing all unit tests]

Acceptance Criteria:
- [Criterion 1 — specific and testable]
- [Criterion 2]
- [References critical test case if applicable, e.g., "T-05 passes"]
```

**Example task:**

```text
TASK: POSTWARE-007
Objective: Implement atomic history.json write with prune-to-30 enforcement in history.py
Priority: P0
Complexity: M
Version: v0
Assigned To: Developer Agent
Dependencies: POSTWARE-002 (models.py with GenerationRecord defined)
Module: src/postware/history.py

Inputs:
- models.py with GenerationRecord, GeneratedBundle defined
- history.json schema specification (BDD v0.2, Section 5)
- Atomic write pattern: write to history.json.tmp, then os.replace()

Steps:
1. Implement load(path: Path) -> list[GenerationRecord] with FileNotFoundError and JSONDecodeError recovery
2. Implement save(records: list[GenerationRecord], path: Path) -> None with prune-to-30 and atomic write
3. Implement get_promo_ratio(), get_recent_pillars(), get_today_record(), get_deduplication_context(), update_today_platform()
4. Write unit tests in tests/unit/test_history.py covering all public API methods and all edge cases

Output:
- src/postware/history.py with full public API implemented
- tests/unit/test_history.py with all scenarios covered

Acceptance Criteria:
- T-05 passes: history.json contains exactly 30 records after saving a 31st entry
- T-06 passes: corrupt history.json results in .bak file creation and fresh history
- Atomic write: os.replace() used; no direct write to history.json
- All public API methods have Google-style docstrings
```

---

## Coding Standards

### Python (All Modules)

- Use Python 3.10+ syntax. Structural pattern matching (`match`/`case`) is permitted and preferred for pillar and day-of-week dispatch.
- All functions must have type hints for every parameter and return value. `Any` is forbidden without an explicit inline comment explaining why.
- All public functions must have Google-style docstrings with `Args:`, `Returns:`, and `Raises:` sections.
- Use `snake_case` for functions and variables. Use `PascalCase` for classes and Pydantic models. Use `UPPER_CASE` for module-level constants.
- Maximum file length: 400 lines. If a module exceeds 400 lines, it must be split. Exception: `models.py` may reach 500 lines as all models must remain in one file.
- All I/O operations (file reads/writes, API calls) must use appropriate error handling — no bare `except:` clauses. Catch specific exception types.
- Use `async/await` for all Telegram bot handler functions (required by `python-telegram-bot` v20+). Synchronous LiteLLM calls in `generator.py` are acceptable (LiteLLM's sync interface is used by design).
- Sort imports in three groups separated by blank lines: (1) stdlib, (2) third-party, (3) local. Enforced by `isort`.
- Format with Black (line length 88). Lint with Ruff. Both must pass with zero warnings before any code is handed to the Reviewer.
- Run `mypy --strict` on all source modules. No unresolved type errors permitted.

### Naming Conventions

| Element | Convention | Example |
| --- | --- | --- |
| Module files | `snake_case.py` | `telegram_bot.py`, `platform_utils.py` |
| Pydantic models | `PascalCase` | `GenerationRecord`, `AppConfig`, `PlatformPost` |
| Pydantic enums | `PascalCase` | `Pillar`, `DayOfWeek` |
| Custom exceptions | `PascalCase` + descriptive suffix | `ConfigError`, `LLMCallError`, `DeliveryCredentialError` |
| Constants | `UPPER_CASE` | `MAX_ATTEMPTS`, `BACKOFF_SECONDS`, `MAX_HISTORY_RECORDS` |
| Private functions | Leading underscore | `_harden_unix()`, `_harden_windows()` |
| Test functions | `test_<scenario>` | `test_history_prunes_to_30_on_save` |
| Fixtures | Descriptive noun | `valid_config`, `history_with_records`, `mock_litellm_success` |

### Error Handling

- Every raised exception must carry a human-readable message. Never raise bare `Exception("something went wrong")`.
- The custom exception hierarchy must be used exclusively. No raw `ValueError` or `RuntimeError` from application code — use the appropriate `PostwareError` subclass.
- `ConfigError` is always caught by `main.py` and rendered via Rich before `sys.exit(1)`. It must never reach the user as a raw traceback.
- Unhandled exceptions at the top level of `main.py` must be caught, logged to `errors.log` with full traceback, and result in `sys.exit(1)`.

### Logging Standards

- Use `logging.getLogger("postware")` in every module. Never create child loggers with different names.
- Log levels: `DEBUG` for unauthorized command discards and internal state; `INFO` for auto-recovery events (fresh history created, promo ratio override); `WARNING` for non-fatal errors and edge cases; `ERROR` for retry exhaustion and pipeline failures.
- Never log `SecretStr` values directly. The `RedactionFilter` is a second layer of defence, not the first.
- Rich terminal output (`console.print()`) is for user-facing messages only. It is not a substitute for logging.

### Configuration and Secrets

- No hardcoded API keys, model names, base URLs, or schedule times anywhere in source code.
- All provider-specific configuration comes from `AppConfig` (loaded from `config.yaml`).
- All credentials come from `EnvConfig` (loaded from `.env` via python-dotenv).
- `.env`, `config.yaml`, `history.json`, and `errors.log` must be listed in `.gitignore`. The repository must never contain real credentials.

---

## Quality Rules

### Testing

- All 12 critical test cases (T-01 through T-12) must have a corresponding passing test before any milestone is approved.
- Minimum test coverage: 100% on `models.py`; ≥90% on `history.py`; ≥80% on all other modules.
- All tests must be isolated. No test may depend on the state left by another test. Use `tmp_path` for all file system fixtures.
- LiteLLM and Telegram API calls must always be mocked. Running the test suite must make zero real external API calls.
- Retry logic must be tested for all three paths: failure on attempt 1 then success, failure on attempts 1 and 2 then success, and failure on all three attempts.
- The `history.json` pruning invariant (exactly 30 records after save) must be tested with boundary values: 29 records + 1 new = 30; 30 records + 1 new = 30 (oldest removed).

### Performance

- End-to-end pipeline (invocation to Telegram delivery confirmation) must complete in ≤60 seconds at p95 with a cloud LLM provider. LLM response time is the variable; orchestration overhead must not exceed 3 seconds.
- `python -m postware status` must return output in ≤2 seconds. No LLM or Telegram calls in the status path.
- `history.json` read, process, and write cycle must complete in ≤500ms. The file is capped at 30 records; no optimization beyond standard file I/O is required.
- The `history.json` pruning invariant must hold on every write. No `save()` call may leave more than 30 records in the file.

### Reliability

- All LLM API calls and Telegram message sends must use the retry policy: 3 attempts, exponential backoff 1s/2s/4s.
- Invalid Telegram credentials (`401`/`400` response on first attempt) must not be retried. Raise `DeliveryCredentialError` immediately.
- `history.json` writes must use atomic `os.replace()` semantics. Partial-write corruption is not acceptable.
- Daemon mode must register `SIGINT` and `SIGTERM` signal handlers. Graceful shutdown must call `scheduler.shutdown(wait=True)` to allow a running job to complete or time out.
- `APScheduler` must be configured with `misfire_grace_time=3600` to handle laptop sleep cycles. A missed trigger must execute within 1 hour of wake.

### Observability

- Every terminal output line must begin with exactly one status icon (`✓`, `✗`, `⚠`, `ℹ`, `↻`, `…`) followed by a single space and the message. No line is emitted without an icon.
- In non-interactive mode (`not sys.stdout.isatty()`), all Rich spinners and progress indicators must be suppressed. Only the final outcome line is emitted to avoid polluting cron/systemd logs.
- Error messages must answer three questions: what failed, why it failed (or where to find out), and what the user can do next.

---

## Security Rules

1. **Telegram sender authorization:** Every bot command handler must validate `update.effective_user.id` against `TELEGRAM_CHAT_ID` as the first operation. Unauthorized senders receive a silent discard — no response, no LLM call, no history access. Silent discard is logged at `DEBUG` level with no PII.
2. **Log redaction:** `RedactionFilter` must be attached to all log handlers (`StreamHandler` and `FileHandler`) at process startup. Redaction must cover all provider API key values from `EnvConfig`, the Telegram bot token, and regex patterns for known key formats (`sk-*`, `sk-ant-*`, `gsk_*`). `SecretStr` in `EnvConfig` provides a second independent layer of protection.
3. **Prompt injection sanitization:** All `AppConfig` string fields embedded in LLM prompts must be passed through `sanitize_for_prompt()`. Sanitization rules: strip whitespace, truncate to max length, replace injection patterns with `[removed]`, escape template delimiters. Raw config values must never appear directly in prompt strings.
4. **File permission hardening:** During `init`, `.env`, `config.yaml`, and `history.json` must receive `0o600` permissions immediately after creation on Unix-like systems. On Windows, the pywin32 ACL method is preferred; `icacls` subprocess is the fallback; inability to apply either produces a terminal warning and log entry but does not block `init`.
5. **API key format validation:** Format checks for the configured LLM provider's API key must run during `generate` and `start` flows before any external API call. Validation failures produce a `WARNING`-level log and terminal warning — not a hard exit — because key formats are not formally standardized.
6. **Dependency scanning:** `scripts/audit_deps.py` must exit with code 1 if any HIGH or CRITICAL severity CVE is found. The `init` command must invoke `pip-audit` and surface findings. Absence of `pip-audit` must produce a warning, not a failure.
7. **Secret management:** API keys and the Telegram bot token must be stored only in `.env`. They must never appear in `config.yaml`, any source file, any test file, or in `errors.log` in plaintext.
8. **Version control hygiene:** `.env`, `config.yaml`, `history.json`, and `errors.log` must be listed in `.gitignore`. The `.env.example` file must contain only placeholder values (e.g., `your_anthropic_key_here`).
9. **Error messages:** Bot command error messages sent to Telegram must never include raw exception strings, stack traces, or credential-adjacent values. Technical detail goes to `errors.log` only.
10. **Single-process assumption:** No concurrency primitives (threads, asyncio locks on `history.json`, multiprocessing) are to be introduced. The single-process, exclusive-access assumption is a design constraint, not an oversight.

---

## Communication Protocol

All agent outputs must include these sections:

```text
## Summary
[One-paragraph description of what was done, which module was affected,
 and which acceptance criteria were met]

## Plan
[Numbered list of steps taken or to be taken]

## Files Created
- [src/postware/history.py] — [purpose: history.json manager with full public API]
- [tests/unit/test_history.py] — [purpose: unit tests for all history.py public methods]

## Files Modified
- [src/postware/models.py] — [what changed: added GenerationRecord.llm_provider field]

## Dependencies Added
- [No new dependencies] OR [pydantic>=2.0 — required for SecretStr and v2 validation API]

## Test Results
- [T-05: PASS — history pruned to exactly 30 records on 31st save]
- [T-06: PASS — corrupt JSON backed up to .bak, fresh history created]

## Security Notes
- [Any security implications of the changes, even if no security features were touched]
- [E.g., "sanitize_for_prompt() called on all new config fields embedded in prompt"]

## Next Steps
- [Which task runs next per the dependency graph]
- [Which agent should act next]

## Issues / Blockers
- [Any problems encountered, design decisions made, or clarifications needed]
- [E.g., "LiteLLM v1.x changed exception hierarchy — LLMCallError wrapping updated"]
```

---

## Dependency Management

- All runtime dependencies are declared in `pyproject.toml` under `[project.dependencies]` with minimum version pins (e.g., `pydantic>=2.0`).
- `pywin32` is declared under `[project.optional-dependencies] windows` — it is not a cross-platform runtime dependency.
- `pip-audit` and `pytest`/`pytest-asyncio` are declared under `[project.optional-dependencies] dev` — they are not runtime dependencies.
- No dependency may be added without a comment in `pyproject.toml` stating its purpose and which feature it enables.
- Run `pip-audit` before finalizing any version milestone to verify no HIGH or CRITICAL CVEs in the dependency tree.
- Prefer well-maintained packages with active commits and documented changelogs. LiteLLM and python-telegram-bot are the highest-risk dependencies due to their large transitive dependency trees — pin minor versions in production to avoid unexpected breaking changes.
- Never introduce a dependency that duplicates functionality already in the approved stack (e.g., do not add `requests` when `httpx` is already available via LiteLLM's tree; do not add `click` or `typer` when `argparse` is specified for CLI parsing).
- The no-database constraint is absolute. Any PR introducing `sqlite3`, `sqlalchemy`, `tortoise-orm`, or any other database library or ORM is immediately rejected regardless of justification.

---

## Self-Correction Rules

1. If any test fails, the Developer Agent must fix the root cause before proceeding. Tests must not be skipped, marked `xfail`, or have their assertions weakened to make them pass.
2. If `mypy --strict`, Black, Ruff, or isort fail, the Developer Agent must fix the violations immediately. Inline suppression comments (`# type: ignore`, `# noqa`) require an explicit justification comment on the same line.
3. If the module dependency layering is violated (any import that creates a cycle or violates the layer order), the Developer Agent must restructure the code before any review. The Reviewer Agent will reject on sight.
4. If the Security Reviewer identifies a non-conformance with any of the five v1 security measures, it is treated as a P0 blocker regardless of its apparent severity. No v1 milestone approval may proceed until the finding is resolved and the Security Reviewer has re-reviewed.
5. If the `history.json` pruning invariant is violated (more than 30 records after a save), the Developer Agent must fix `history.py.save()` immediately. This is a data integrity violation.
6. If an LLM API call or Telegram delivery exhausts all three retry attempts, the pipeline must log the full error to `errors.log`, exit with code 1, and must not modify `history.json`. If code is found that modifies history after a failed pipeline, it is a blocking bug.
7. If a `SecretStr` value is found to be coerced to a plain string anywhere except the immediate LiteLLM or Telegram API call site, the Developer Agent must fix it and the Security Reviewer must re-review the affected module.
8. If `errors.log` is found to contain a string matching any known API key format (the guardrail metric from the PRD), the `RedactionFilter` implementation must be fixed before any milestone is approved.
9. If the daemon crashes due to an unhandled exception, the Developer Agent must add a top-level exception handler in `scheduler.py` or `main.py` that logs the traceback to `errors.log` before the process exits. External process managers (systemd, supervisor) handle restart; Postware must not attempt to self-heal.
10. If a platform-specific edge case is discovered (e.g., `os.replace()` atomicity on a network filesystem, Windows ACL failure mode), the Developer Agent must document it as a comment in the affected module and update the Risk Register entry if the risk profile changes.

---

## Deployment Rules

Postware is a local CLI tool with no cloud deployment. "Deployment" means the two operational modes a user runs on their own machine.

**One-Shot Mode (cron):**

- User sets up a system cron entry: `0 8 * * * cd /path/to/postware && python -m postware generate`
- Cron mode relies on exit codes: code 0 = success, code 1 = failure. Cron job runners can be configured to send email on non-zero exit.
- All terminal output in cron mode must be minimal — only the final outcome line (`✓` or `✗`). Progress indicators must be suppressed via `sys.stdout.isatty()` detection.

**Daemon Mode (APScheduler):**

- User runs `python -m postware start` under a process manager (systemd unit, supervisor config, or macOS launchd plist).
- The daemon must handle `SIGINT` and `SIGTERM` with graceful shutdown (`scheduler.shutdown(wait=True)`).
- If the daemon crashes, the process manager is responsible for restart. Postware does not attempt self-restart.
- `misfire_grace_time=3600` ensures that a job missed due to laptop sleep executes when the machine wakes, within a 1-hour window.

**Setup (init):**

- `python -m postware init` is the only "deployment" step. It creates `config.yaml`, `.env`, and `history.json`; applies file permissions; runs the dependency audit; and prints the setup checklist.
- The `init` command must be idempotent for `.env` and `history.json` (create if absent, skip if present). For `config.yaml`, the user must confirm overwrite `[y/N]` with `N` as the safe default.
- After `init`, the user must complete the setup checklist manually (fill in API keys in `.env`, fill in project details in `config.yaml`, configure Telegram bot via BotFather).

**Version upgrades:**

- `history.json` schema must not have breaking changes between patch versions. Breaking schema changes increment the MAJOR version.
- If a schema migration is required, `history.py` must detect the old version field and migrate in-place before use.
- Users upgrade by running `pip install --upgrade postware` followed by `python -m postware status` to verify the tool is operational.

# v0 Milestone — Ordered Task List

> **Version target:** v0 — Functional MVP (P0 features F1–F7 only)
> **Exit criterion:** `python -m postware generate` runs end-to-end with posts delivered to Telegram, history updated, and errors logged.
context
---

## Dependency Graph

```text
graph TD
    PW001["PW-001<br/>models.py<br/>Enums & Base Models"]
    PW002["PW-002<br/>models.py<br/>Config Models"]
    PW003["PW-003<br/>models.py<br/>Error Hierarchy"]
    PW004["PW-004<br/>config.py<br/>Config Loader"]
    PW005["PW-005<br/>history.py<br/>History Manager"]
    PW006["PW-006<br/>prompts.py<br/>Prompt Builder"]
    PW007["PW-007<br/>generator.py<br/>LLM Call & Parse"]
    PW008["PW-008<br/>generator.py<br/>Pipeline Orchestration"]
    PW009["PW-009<br/>telegram_bot.py<br/>Delivery"]
    PW010["PW-010<br/>main.py<br/>CLI & Logger"]
    PW011["PW-011<br/>main.py<br/>generate Command"]
    PW012["PW-012<br/>main.py<br/>status Command"]
    PW013["PW-013<br/>main.py<br/>init Command"]

    PW001 --> PW002
    PW001 --> PW003
    PW002 --> PW004
    PW001 --> PW005
    PW001 --> PW006
    PW004 --> PW007
    PW005 --> PW008
    PW006 --> PW007
    PW003 --> PW007
    PW007 --> PW008
    PW008 --> PW009
    PW003 --> PW009
    PW004 --> PW010
    PW010 --> PW011
    PW008 --> PW011
    PW009 --> PW011
    PW005 --> PW011
    PW005 --> PW012
    PW010 --> PW012
    PW010 --> PW013
```

### Execution Order (Critical Path)

| Phase | Tasks | Gate |
|-------|-------|-------|
| 1 — Dependency Floor | PW-001, PW-002, PW-003 | All data shapes defined |
| 2 — Foundation Modules | PW-004, PW-005 | Config loads & validates; history reads/writes/prunes |
| 3 — Prompt Construction | PW-006 | Prompts build without I/O |
| 4 — Generation Engine | PW-007, PW-008 | LLM call works; full pipeline returns `GeneratedBundle` |
| 5 — Delivery | PW-009 | Telegram message sent |
| 6 — CLI Shell | PW-010, PW-011, PW-012, PW-013 | All CLI commands wired; end-to-end works |

---

## Task List

---

```text
TASK: PW-001
Objective: Define all Pydantic enums, PlatformPost, PlatformPosts, GeneratedBundle, and GenerationRecord models in models.py
Priority: P0
Complexity: M
Version: v0
Assigned To: Developer Agent
Dependencies: None
Module: src/postware/models.py

Inputs:
- Data schema reference from Technical Architecture Document (Step 4)
- Platform formatting rules from PRD (FR-002): X ≤280, LinkedIn ≤1500, Threads ≤500
- Content pillar definitions from PRD (FR-003): P1–P5 with day-of-week mapping

Steps:
1. Define Pillar enum (P1 through P5 with human-readable labels)
2. Define DayOfWeek enum (Mon through Sun)
3. Define PlatformPost model with text, format_type, image_suggestion fields
4. Define PlatformPosts model with x, linkedin, threads fields (each PlatformPost)
5. Define GeneratedBundle model with date, day_of_week, pillar, is_promotional, platform_posts, generated_at, llm_provider, llm_model
6. Define GenerationRecord as the storage-equivalent model (same fields as GeneratedBundle)
7. Add PILLAR_SCHEDULE constant mapping DayOfWeek → Pillar
8. Add PLATFORM_CHAR_LIMITS constant dict
9. Verify models.py has zero internal imports (dependency floor rule)

Output:
- src/postware/models.py with all generation-related Pydantic models, enums, and constants

Acceptance Criteria:
- All models pass mypy --strict
- models.py contains zero imports from other src/postware/ modules
- Pillar enum has exactly 5 members (P1–P5)
- DayOfWeek enum has exactly 7 members (Mon–Sun)
- PILLAR_SCHEDULE maps all 7 days to the correct pillars per PRD FR-003
- PlatformPost, GeneratedBundle, GenerationRecord are valid Pydantic v2 models
- T-02 unlocked: GeneratedBundle.is_promotional field exists for promo ratio enforcement
- T-05 unlocked: GenerationRecord exists for history storage
```

---

```text
TASK: PW-002
Objective: Define AppConfig, ProjectConfig, AuthorConfig, LLMConfig, ScheduleConfig, and EnvConfig Pydantic models in models.py
Priority: P0
Complexity: M
Version: v0
Assigned To: Developer Agent
Dependencies: PW-001 (models.py with generation models defined)
Module: src/postware/models.py

Inputs:
- Config schema reference from Technical Architecture Document (Step 6, config.py section)
- Supported provider list from PRD FR-008
- config.yaml structure from AGENTS.md repository structure

Steps:
1. Define ProjectConfig model with name, description fields
2. Define AuthorConfig model with bio field
3. Define LLMConfig model with provider, model, base_url (optional) fields
4. Define ScheduleConfig model with time field (HH:MM string)
5. Define AppConfig model composing ProjectConfig, AuthorConfig, milestones, changelog, LLMConfig, ScheduleConfig
6. Define EnvConfig model with telegram_bot_token (str for v0), telegram_chat_id (str), and api_keys (dict[str, str])
7. Add SUPPORTED_PROVIDERS constant listing all valid provider strings
8. Add Pydantic validators for required fields and provider validation

Output:
- src/postware/models.py updated with all config-related Pydantic models

Acceptance Criteria:
- AppConfig validates a well-formed config dict and rejects missing required fields
- EnvConfig validates presence of telegram_bot_token and telegram_chat_id
- LLMConfig.provider validated against SUPPORTED_PROVIDERS list
- T-01 unlocked: AppConfig validation will reject incomplete configs, enabling the missing-config test
- T-12 unlocked: AppConfig and EnvConfig shapes exist for status command to load
```

> [!NOTE]
> `EnvConfig` uses plain `str` for token/key fields in v0. `SecretStr` upgrade is a v1/P1 task.

---

```text
TASK: PW-003
Objective: Define the complete PostwareError exception hierarchy in models.py
Priority: P0
Complexity: S
Version: v0
Assigned To: Developer Agent
Dependencies: PW-001 (models.py exists)
Module: src/postware/models.py

Inputs:
- Error Type Hierarchy from Technical Architecture Document (Step 8)
- Error handling conventions from AGENTS.md coding standards

Steps:
1. Define PostwareError(Exception) as base class with message field
2. Define ConfigError(PostwareError)
3. Define HistoryError(PostwareError) and HistoryWriteError(HistoryError)
4. Define GenerationError(PostwareError), LLMCallError(GenerationError), LLMOutputError(GenerationError), GenerationFailedError(GenerationError)
5. Define DeliveryError(PostwareError), DeliveryCredentialError(DeliveryError), DeliveryFailedError(DeliveryError)

Output:
- src/postware/models.py updated with complete error hierarchy

Acceptance Criteria:
- All 9 exception classes defined with correct inheritance
- Every exception carries a human-readable message field
- T-01 unlocked: ConfigError exists for config validation failures
- T-04 unlocked: GenerationFailedError exists for retry exhaustion
- T-06 unlocked: HistoryError hierarchy exists for corruption recovery
```

---

```text
TASK: PW-004
Objective: Implement config.yaml and .env loading with Pydantic validation in config.py
Priority: P0
Complexity: M
Version: v0
Assigned To: Developer Agent
Dependencies: PW-002 (AppConfig, EnvConfig models defined), PW-003 (ConfigError defined)
Module: src/postware/config.py

Inputs:
- models.py with AppConfig, EnvConfig, ConfigError
- Config load sequence from Technical Architecture Document (Step 6, config.py section)
- config.yaml structure from AGENTS.md

Steps:
1. Implement load_config(path: Path) → AppConfig that reads config.yaml, parses YAML, validates via Pydantic
2. Implement load_env() → EnvConfig that loads .env via python-dotenv, validates required fields
3. Convert all load/parse/validate errors into ConfigError with descriptive messages
4. Handle FileNotFoundError for missing config.yaml with init suggestion
5. Handle yaml.YAMLError with line number if available
6. Handle Pydantic ValidationError by listing each failed field

Output:
- src/postware/config.py with load_config() and load_env() functions

Acceptance Criteria:
- config.py imports only from models.py (dependency layering rule)
- load_config() returns valid AppConfig for well-formed YAML
- load_config() raises ConfigError for missing file, invalid YAML, and missing required fields
- load_env() returns valid EnvConfig for well-formed .env
- load_env() raises ConfigError for missing required env vars
- T-01 passes: missing config.yaml → exit code 1, error message contains "config.yaml not found", zero API calls
```

---

```text
TASK: PW-005
Objective: Implement atomic history.json read/write/query/prune in history.py
Priority: P0
Complexity: M
Version: v0
Assigned To: Developer Agent
Dependencies: PW-001 (GenerationRecord model defined), PW-003 (HistoryError, HistoryWriteError defined)
Module: src/postware/history.py

Inputs:
- models.py with GenerationRecord, PlatformPost, HistoryError, HistoryWriteError
- history.py public API specification from Technical Architecture Document (Step 6)
- Atomic write pattern: write to history.json.tmp, then os.replace()

Steps:
1. Implement load(path: Path) → list[GenerationRecord] with FileNotFoundError and JSONDecodeError recovery
2. Implement save(records: list[GenerationRecord], path: Path) → None with prune-to-30 and atomic write via os.replace()
3. Implement get_promo_ratio(records, window_days=14) → float
4. Implement get_recent_pillars(records, n=7) → list[str]
5. Implement get_today_record(records) → GenerationRecord | None
6. Implement get_deduplication_context(records, n=10) → list[str]
7. Handle corrupt JSON: back up to .bak, create fresh history, log warning
8. Handle missing file: create empty structure, log info

Output:
- src/postware/history.py with full public API implemented

Acceptance Criteria:
- history.py imports only from models.py (dependency layering rule)
- T-05 passes: history.json contains exactly 30 records after saving a 31st entry (oldest pruned)
- T-06 passes: corrupt history.json results in .bak file creation and fresh history created
- Atomic write: os.replace() used; no direct write to history.json
- All public API methods have Google-style docstrings
- get_promo_ratio returns 0.0 for empty history
```

---

```
TASK: PW-006
Objective: Implement LLM prompt construction and output format contract in prompts.py
Priority: P0
Complexity: M
Version: v0
Assigned To: Developer Agent
Dependencies: PW-001 (Pillar, AppConfig, PlatformPost models defined)
Module: src/postware/prompts.py

Inputs:
- models.py with Pillar, AppConfig, PlatformPost, PLATFORM_CHAR_LIMITS
- Prompt builder specification from Technical Architecture Document (Step 6, prompts.py section)
- LLM output JSON schema from Technical Architecture Document
- Content pillar definitions and platform formatting rules from PRD (FR-002, FR-003)

Steps:
1. Implement build_system_prompt() that defines the LLM's role, output JSON schema, and platform-specific formatting rules
2. Implement build_user_prompt(config, pillar, force_value_driven, dedup_context) that constructs the user prompt with project context, pillar instructions, and dedup context
3. Define the expected LLM output JSON schema as a string constant for system prompt injection
4. Embed all platform character limits and tone requirements in the system prompt

Output:
- src/postware/prompts.py with build_system_prompt() and build_user_prompt() functions

Acceptance Criteria:
- prompts.py imports only from models.py (dependency layering rule)
- No network calls and no file I/O in prompts.py
- System prompt contains exact JSON schema contract for LLM output
- User prompt includes project context, pillar name, promo constraint, and dedup context
- Platform character limits embedded correctly: X ≤280, LinkedIn ≤1500, Threads ≤500
- T-02 unlocked: force_value_driven parameter exists for promo ratio enforcement in prompt
```

> [!NOTE]
> `sanitize_for_prompt()` is a v1/P1 feature (F13). In v0, config values are embedded directly in prompts without sanitization.

---

```
TASK: PW-007
Objective: Implement LiteLLM call wrapper with error normalisation and JSON response parsing in generator.py
Priority: P0
Complexity: M
Version: v0
Assigned To: Developer Agent
Dependencies: PW-004 (config.py with LLMConfig), PW-006 (prompts.py), PW-003 (LLMCallError, LLMOutputError defined)
Module: src/postware/generator.py

Inputs:
- models.py with LLMConfig, GeneratedBundle, LLMCallError, LLMOutputError
- prompts.py with build_system_prompt(), build_user_prompt()
- config.py with load_config(), load_env()
- generator.py pipeline specification from Technical Architecture Document (Step 6)

Steps:
1. Implement call_llm(system_prompt, user_prompt, llm_config, env) → str that calls litellm.completion()
2. Wrap all LiteLLM exceptions into LLMCallError (error normalisation rule)
3. Implement parse_response(raw: str) → dict that strips markdown fences and parses JSON
4. Implement validate_output(parsed: dict) → GeneratedBundle via Pydantic validation
5. Raise LLMOutputError on parse failure or validation failure

Output:
- src/postware/generator.py with call_llm(), parse_response(), validate_output() functions

Acceptance Criteria:
- All LiteLLM exceptions caught and re-raised as LLMCallError (no LiteLLM types leak)
- Markdown fence stripping works for ```json and ``` wrappers
- Valid JSON produces a valid GeneratedBundle
- Invalid JSON raises LLMOutputError
- T-03 unlocked: parse and validation failure handling exists for retry scenarios
- T-04 unlocked: LLMCallError exists for retry exhaustion
```

---

```
TASK: PW-008
Objective: Implement full generation pipeline orchestration with pillar resolution, promo enforcement, and v0 single-attempt call in generator.py
Priority: P0
Complexity: L
Version: v0
Assigned To: Developer Agent
Dependencies: PW-007 (call_llm, parse, validate), PW-005 (history.py with query functions)
Module: src/postware/generator.py

Inputs:
- generator.py with call_llm(), parse_response(), validate_output()
- history.py with get_promo_ratio(), get_recent_pillars(), get_deduplication_context()
- models.py with PILLAR_SCHEDULE, Pillar, DayOfWeek
- Pipeline sequence from Technical Architecture Document (Step 6, generator.py section)

Steps:
1. Implement resolve_pillar(day_of_week, recent_pillars) → Pillar using PILLAR_SCHEDULE and recent history for adjustment
2. Implement calculate_promo_constraint(promo_ratio) → bool that returns True (force value-driven) if ratio ≥ 0.20
3. Implement generate(config, env, records) → GeneratedBundle that orchestrates the full pipeline:
   a. Resolve today's pillar
   b. Calculate promo constraint from history
   c. Build prompts via prompts.py
   d. Call LLM via call_llm()
   e. Parse and validate response
   f. Return GeneratedBundle with metadata (date, pillar, provider info)
4. For v0: single attempt only — on failure, raise GenerationFailedError immediately (retry logic is v1/P1 F8)
5. Log info message when promo ratio override is active

Output:
- src/postware/generator.py with generate() as the top-level pipeline function

Acceptance Criteria:
- generate() returns a complete GeneratedBundle with all metadata fields populated
- T-02 passes: when promo ratio ≥ 20%, is_promotional forced to False in generated bundle; info message logged
- T-04 partially unlocked: GenerationFailedError raised on LLM failure (single attempt in v0; full retry in v1)
- Pillar resolution uses PILLAR_SCHEDULE with day-of-week mapping
- generator.py imports config, history, prompts, models only (dependency layering rule)
```

> [!IMPORTANT]
> v0 uses single-attempt LLM calls. The 3-attempt retry logic with exponential backoff (F8) is a v1/P1 feature. In v0, any LLM failure raises `GenerationFailedError` immediately.

---

```
TASK: PW-009
Objective: Implement Telegram message formatting and delivery (send_bundle) in telegram_bot.py
Priority: P0
Complexity: M
Version: v0
Assigned To: Developer Agent
Dependencies: PW-008 (GeneratedBundle output), PW-003 (DeliveryError hierarchy)
Module: src/postware/telegram_bot.py

Inputs:
- models.py with GeneratedBundle, PlatformPost, EnvConfig, DeliveryCredentialError, DeliveryFailedError
- Telegram message format specification from PRD (Section 5.3)
- Message splitting logic from PRD FR-005 (4,096 char limit)

Steps:
1. Implement format_bundle(bundle: GeneratedBundle) → str | list[str] that formats the Telegram message per PRD Section 5.3 spec
2. Implement message splitting: if formatted message > 4,096 chars, split into 3 messages by platform section
3. Implement send_bundle(bundle, env) → None that sends formatted message(s) via bot.send_message()
4. For v0: single attempt only — on Telegram error, raise DeliveryFailedError immediately
5. Detect credential errors (401/400) and raise DeliveryCredentialError immediately

Output:
- src/postware/telegram_bot.py with format_bundle() and send_bundle() functions

Acceptance Criteria:
- telegram_bot.py imports generator, history, models only (dependency layering rule)
- Message format matches PRD Section 5.3 template (platform headers, dividers, footer with date/pillar/promo)
- T-07 passes: 5,000-char message body results in three separate messages sent
- Credential errors (401/400) raise DeliveryCredentialError immediately without retry
- All sent messages use the correct chat_id from EnvConfig
```

> [!NOTE]
> v0 delivery is single-attempt. The 3-attempt Telegram retry logic (F8) is v1/P1. Bot command handlers (/generate, /regenerate, /status) are v1/P1 (F9). Sender authorization is v1/P1 (F11).

---

```
TASK: PW-010
Objective: Implement CLI entrypoint shell with argparse, shared logger setup, and Python version check in main.py
Priority: P0
Complexity: M
Version: v0
Assigned To: Developer Agent
Dependencies: PW-004 (config.py for config loading)
Module: src/postware/main.py

Inputs:
- main.py specification from Technical Architecture Document (Step 6)
- CLI commands from PRD FR-006: generate, status, init (start is v1)
- Shared logger configuration from Technical Architecture Document (Step 6, Shared Logger section)
- Python version check requirement from AGENTS.md Developer Rules #9

Steps:
1. Implement Python version check as the first logic: sys.version_info >= (3, 10)
2. Set up shared logger: logging.getLogger("postware") with StreamHandler (stderr) and FileHandler (errors.log, append mode)
3. Detect TTY mode via sys.stdout.isatty() and set INTERACTIVE flag
4. Set up argparse with three subcommands: generate, status, init (start is v1)
5. Implement top-level exception handler: catch PostwareError subtypes and unhandled exceptions, log to errors.log, print via Rich, exit code 1
6. Implement ConfigError → Rich formatted error output and exit code 1

Output:
- src/postware/main.py with CLI skeleton, logger setup, version check, and top-level error handling

Acceptance Criteria:
- Python version check is the first logic executed before any application module import
- Shared logger configured with StreamHandler + FileHandler
- Rich output suppressed when not interactive (sys.stdout.isatty() == False)
- T-01 partially unlocked: top-level handler catches ConfigError and exits with code 1
- main.py is the composition root — imports all other modules (dependency layering rule)
```

> [!NOTE]
> v0 logger does NOT include `RedactionFilter` — that is a v1/P1 feature (F12). v0 uses basic log formatting only.

---

```
TASK: PW-011
Objective: Wire the generate CLI subcommand end-to-end in main.py
Priority: P0
Complexity: L
Version: v0
Assigned To: Developer Agent
Dependencies: PW-010 (CLI shell), PW-008 (generate pipeline), PW-009 (send_bundle delivery), PW-005 (history save)
Module: src/postware/main.py

Inputs:
- main.py with CLI skeleton and error handling
- config.py with load_config(), load_env()
- history.py with load(), save()
- generator.py with generate()
- telegram_bot.py with send_bundle()
- Pipeline flow from Technical Architecture Document (Step 7, data passing convention)

Steps:
1. Implement cmd_generate() function that orchestrates the full pipeline:
   a. Load config and env via config.py
   b. Load history via history.py
   c. Call generate(config, env, records) via generator.py
   d. Append GeneratedBundle to records list
   e. Save updated records via history.py
   f. Send bundle to Telegram via telegram_bot.py
   g. Print Rich success output with date, pillar, promo ratio, provider, duration
2. Handle HistoryWriteError: warn but continue to delivery
3. Handle GenerationFailedError: log error, exit code 1, do NOT modify history
4. Handle DeliveryCredentialError and DeliveryFailedError: log error, exit code 1
5. Time the pipeline and display duration

Output:
- src/postware/main.py with cmd_generate() fully wired

Acceptance Criteria:
- python -m postware generate runs end-to-end: config loaded → history loaded → posts generated → history updated → Telegram delivered → exit code 0
- T-01 passes: missing config.yaml → exit code 1 with clear error; zero API calls
- T-02 passes: promo ratio ≥ 20% → is_promotional forced False; info message emitted
- T-04 applicable: LLM failure → exit code 1; errors.log updated; history.json unchanged
- T-05 applicable: history.json pruned to 30 records after save
- T-06 applicable: corrupt history.json → .bak created; fresh history; pipeline continues
- Rich output uses status icons (✓, ✗, ⚠, ℹ) per PRD Section 5.2
- v0 EXIT CRITERION MET: end-to-end pipeline works
```

---

```
TASK: PW-012
Objective: Implement the status CLI subcommand in main.py
Priority: P0
Complexity: S
Version: v0
Assigned To: Developer Agent
Dependencies: PW-010 (CLI shell), PW-005 (history.py query functions)
Module: src/postware/main.py

Inputs:
- main.py with CLI skeleton
- history.py with load(), get_promo_ratio(), get_today_record(), get_recent_pillars()
- models.py with PILLAR_SCHEDULE, DayOfWeek
- Status output specification from PRD FR-006 and Section 5.2

Steps:
1. Implement cmd_status() that loads history and displays:
   a. Today's pillar (from PILLAR_SCHEDULE)
   b. 14-day promotional ratio
   c. Total posts generated (len of records)
   d. Last generation timestamp
2. Render output as a Rich panel or table
3. Handle empty history gracefully: "No generation history" message

Output:
- src/postware/main.py with cmd_status() implemented

Acceptance Criteria:
- T-12 passes: status with no history renders "No generation history" panel; exit code 0
- Status output completes in ≤2 seconds (no LLM or Telegram calls)
- Rich panel displays pillar, promo ratio, total posts, and last run timestamp
- Exit code 0 on success
```

---

```
TASK: PW-013
Objective: Implement the init CLI subcommand for file scaffolding in main.py
Priority: P0
Complexity: S
Version: v0
Assigned To: Developer Agent
Dependencies: PW-010 (CLI shell)
Module: src/postware/main.py

Inputs:
- main.py with CLI skeleton
- init flow from PRD (Flow 3, Section 4.1)
- Idempotency rules from PRD EC-09: .env and history.json created if absent; config.yaml prompts overwrite confirmation

Steps:
1. Implement cmd_init() that creates starter files:
   a. config.yaml with placeholder values and inline comments (confirm overwrite if exists)
   b. .env with placeholder credential values (create if absent, skip if present)
   c. history.json with empty {"records": []} structure (create if absent, skip if present)
2. Print setup checklist with numbered action items
3. Handle overwrite confirmation for config.yaml: [y/N] prompt with N as safe default

Output:
- src/postware/main.py with cmd_init() implemented

Acceptance Criteria:
- init creates config.yaml, .env, and history.json in the project root
- Idempotent for .env and history.json (create if absent, skip if present)
- config.yaml overwrite requires explicit "y" confirmation
- Setup checklist printed with actionable items (fill in API keys, set up Telegram bot, etc.)
- Exit code 0 on success
```

> [!NOTE]
> v0 init does NOT apply file permissions — that is v1/P1 (F14). v0 init does NOT run pip-audit — that is v1/P1 (F16).

---

## Test Case Mapping Summary

| Test Case | Description | Unlocked By |
|---|---|---|
| T-01 | Missing config.yaml → exit 1, clear error, zero API calls | PW-004, PW-010, PW-011 |
| T-02 | Promo ratio ≥ 20% → is_promotional forced False | PW-001, PW-008, PW-011 |
| T-03 | Malformed JSON on attempts 1-2, valid on 3 → success | **v1 only** (requires retry logic, F8) |
| T-04 | LLM fails all attempts → exit 1, error logged, history unchanged | PW-007, PW-008, PW-011 |
| T-05 | 30 records + 1 new → exactly 30 after save | PW-005, PW-011 |
| T-06 | Corrupt history.json → .bak, fresh history, continues | PW-005 |
| T-07 | 5,000-char Telegram message → split into 3 messages | PW-009 |
| T-08 | Unauthorized Telegram user → silent discard | **v1 only** (F11 — Telegram auth) |
| T-09 | API key in error → redacted in errors.log | **v1 only** (F12 — RedactionFilter) |
| T-10 | init on Unix → 0o600 permissions | **v1 only** (F14 — file permissions) |
| T-11 | sanitize_for_prompt with injection → [removed] | **v1 only** (F13 — prompt sanitization) |
| T-12 | status with no history → panel rendered, exit 0 | PW-012 |

> [!IMPORTANT]
> v0 covers test cases **T-01, T-02, T-04 (single attempt), T-05, T-06, T-07, T-12**. Test cases T-03, T-08, T-09, T-10, T-11 require v1/P1 features and are out of scope for v0. The Technical Architecture v0 roadmap (Step 13) confirms v0 tests cover "T-01 through T-06, T-12".

---

## Complexity Summary

| Complexity | Count | Tasks |
|---|---|---|
| S (Small) | 3 | PW-003, PW-012, PW-013 |
| M (Medium) | 8 | PW-001, PW-002, PW-004, PW-005, PW-006, PW-007, PW-009, PW-010 |
| L (Large) | 2 | PW-008, PW-011 |
| XL (Extra-Large) | 0 | — |

## Anti-Scope Confirmation

The following v1/P1 features are explicitly excluded from this task list:

- ❌ Retry logic with exponential backoff (F8)
- ❌ Telegram bot commands: /generate, /regenerate, /status (F9)
- ❌ APScheduler daemon mode and `start` command (F10)
- ❌ Telegram sender authorization (F11)
- ❌ Log redaction filter (F12)
- ❌ Prompt injection sanitization / sanitize_for_prompt() (F13)
- ❌ File permission hardening — Unix chmod and Windows ACLs (F14, F17)
- ❌ API key format validation (F15)
- ❌ pip-audit dependency scanning (F16)
- ❌ SecretStr on EnvConfig credentials (v1 security)
- ❌ scheduler.py module (v1)
- ❌ platform_utils.py module (v1)
- ❌ scripts/audit_deps.py (v1)

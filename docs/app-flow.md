# App Flow Document

---

```
Project Name:   Postware
Document Type:  App Flow Document
Version:        0.1
Date:           2025-03-05
Status:         Draft
```

---

## 🌟 North Star Action

```
🌟 NORTH STAR ACTION: Developer receives a formatted daily post bundle in Telegram
                      containing three platform-optimized posts, ready to copy and publish.

📏 SHORTEST PATH (Configured system → Value Delivered):
   Step 1: Cron triggers `python -m postware generate` (or user runs it manually)
   Step 2: System loads config, history, resolves today's pillar
   Step 3: LLM generates three posts
   Step 4: Formatted bundle delivered to Telegram chat

⏱️ COMMAND COUNT: 1 (single CLI invocation or zero after cron is configured)
⚠️ TAP ASSESSMENT: OPTIMAL — after first-time setup, the user's interaction
   cost is zero. The entire pipeline is autonomous.
```

---

## Phase 1: Logic Foundations

### 1A — Happy Path Entry Points

| Platform | Trigger | Entry Point | Auth Required |
|---|---|---|---|
| Terminal | Manual invocation | `python -m postware generate` | No (API keys in .env) |
| Cron | Scheduled job | `python -m postware generate` | No |
| Telegram chat | `/generate` bot command | Telegram bot listener | No (single-user chat ID) |
| Terminal | Daemon startup | `python -m postware start` | No |

### 1B — Pre-Conditions

| Condition | Required For |
|---|---|
| `config.yaml` present and valid | All flows |
| `.env` present with valid LLM API key | All generation flows |
| `.env` present with valid Telegram bot token + chat ID | All delivery flows |
| `history.json` present (or creatable) | All generation flows |
| LLM provider API reachable (or local model server running) | Generation flows |
| Telegram Bot API reachable | All delivery and bot flows |

### 1C — Secondary Flows

| # | Goal | Entry Point | Frequency | Intersects Happy Path? |
|---|---|---|---|---|
| 1 | Single-platform regeneration | `/regenerate` Telegram command | Weekly | Yes — shares LLM + delivery pipeline |
| 2 | Status check | `postware status` or `/status` | Daily | No — read-only, no generation |
| 3 | First-time setup | `python -m postware init` | Once | No — pre-condition creator |
| 4 | Daemon mode startup | `python -m postware start` | Once per session | Wraps Happy Path |
| 5 | Graceful daemon shutdown | SIGINT / SIGTERM | Rare | Terminates Happy Path wrapper |

---

## Phase 2: Detailed Flow Maps

### Flow 1 — Daily Post Generation (CLI / Cron)

```
[ENTRY] ─────────────────────────────────────────────────────────────────
  cron trigger OR `python -m postware generate`
  OR Telegram /generate command → delegates to this same pipeline

[STATE 1: Config & Env Load]
  Primary action: Parse config.yaml + load .env
  ─────────────────────────────────────────
  ✅ SUCCESS → STATE 2
  
  ❌ UNHAPPY PATH: config.yaml missing
     📍 Trigger: File not found at expected path
     👁️ User Sees: Rich-formatted terminal error:
        "✗ config.yaml not found. Run `python -m postware init` to create one."
     🔄 Recovery Action: Run `python -m postware init`
     🚪 Escape Hatch: Exit code 1. No API calls made.

  ❌ UNHAPPY PATH: config.yaml has missing required fields
     📍 Trigger: Pydantic validation failure on load
     👁️ User Sees: Rich-formatted error listing each missing field by name:
        "✗ config.yaml validation failed. Missing required fields: project.name, llm.model"
     🔄 Recovery Action: User edits config.yaml to fill in flagged fields
     🚪 Escape Hatch: Exit code 1. No API calls made.

  ❌ UNHAPPY PATH: .env missing or API key absent
     📍 Trigger: python-dotenv finds no .env or key value is empty string
     👁️ User Sees: "✗ Missing environment variable: ANTHROPIC_API_KEY.
        Check your .env file."
     🔄 Recovery Action: User adds key to .env
     🚪 Escape Hatch: Exit code 1.

[STATE 2: History Load]
  Primary action: Read and parse history.json
  ─────────────────────────────────────────
  ✅ SUCCESS → STATE 3

  ❌ UNHAPPY PATH: history.json does not exist
     📍 Trigger: First-ever run, or file was deleted
     👁️ User Sees: Terminal info message: "ℹ history.json not found. Creating fresh history."
     🔄 Recovery Action: System auto-creates history.json with empty default structure
     🚪 Escape Hatch: None needed — auto-recovery, flow continues.

  ❌ UNHAPPY PATH: history.json is corrupt (invalid JSON)
     📍 Trigger: Partial write, manual edit error, disk issue
     👁️ User Sees: "⚠ history.json is corrupt. Backed up to history.json.bak.
        Creating fresh history."
     🔄 Recovery Action: System backs up corrupt file, creates fresh history.json, logs warning to errors.log
     🚪 Escape Hatch: Flow continues. User can inspect .bak file manually.

[STATE 3: Pillar & Ratio Resolution]
  Primary action: Map today's day-of-week → pillar; calculate 14-day promo ratio
  ─────────────────────────────────────────────────────────────────────────────
  ✅ SUCCESS → STATE 4 (with resolved pillar + value/promo flag)

  ❌ UNHAPPY PATH: Promotional ratio at or above 20%
     📍 Trigger: Last 14 days of history contain ≥20% promotional posts
     👁️ User Sees: Terminal info: "ℹ Promo ratio at 22%. Forcing value-driven content."
     🔄 Recovery Action: System overrides prompt directive to force value-driven output. No user action needed.
     🚪 Escape Hatch: None needed — auto-handled.

[STATE 4: LLM Prompt Construction & Completion]
  Primary action: Build prompt with full context; call litellm.completion()
  ─────────────────────────────────────────────────────────────────────────────
  ✅ SUCCESS → STATE 5

  ❌ UNHAPPY PATH: LLM returns malformed / incomplete output
     📍 Trigger: Response missing one or more platform posts, or fails schema validation
     👁️ User Sees: Terminal: "⚠ LLM output invalid. Retrying (attempt 2/3)..."
     🔄 Recovery Action: Automatic retry with exponential backoff (1s → 2s → 4s)
     🚪 Escape Hatch: After 3 failures → log full error to errors.log, exit code 1.
        Terminal: "✗ LLM failed after 3 attempts. See errors.log for details."

  ❌ UNHAPPY PATH: LLM API connection error (network, timeout)
     📍 Trigger: requests.ConnectionError or timeout exception from litellm
     👁️ User Sees: "⚠ LLM API unreachable. Retrying (attempt 1/3)..."
     🔄 Recovery Action: Exponential backoff retry (1s → 2s → 4s)
     🚪 Escape Hatch: After 3 failures → errors.log, exit code 1.

  ❌ UNHAPPY PATH: Local model server (Ollama/LM Studio) not running
     📍 Trigger: Connection refused on configured base_url
     👁️ User Sees: "✗ Cannot connect to local model at http://localhost:11434.
        Is Ollama running? Start it with `ollama serve`."
     🔄 Recovery Action: User starts local model server, re-runs command
     🚪 Escape Hatch: Exit code 1 after 3 retries.

  ❌ UNHAPPY PATH: Unsupported LLM provider string in config
     📍 Trigger: LiteLLM raises BadRequestError for unknown provider
     👁️ User Sees: "✗ Unsupported LLM provider: 'grok'. Supported providers:
        anthropic, openai, groq, google, ollama, lmstudio"
     🔄 Recovery Action: User corrects provider field in config.yaml
     🚪 Escape Hatch: Exit code 1. No retries attempted.

[STATE 5: History Write]
  Primary action: Append generation record to history.json; prune to 30 entries
  ─────────────────────────────────────────────────────────────────────────────
  ✅ SUCCESS → STATE 6

  ❌ UNHAPPY PATH: File system write permission error
     📍 Trigger: history.json or its directory is not writable
     👁️ User Sees: "⚠ Could not write to history.json: [Errno 13] Permission denied.
        Posts generated but history not saved."
     🔄 Recovery Action: User fixes file permissions. Delivery still proceeds.
     🚪 Escape Hatch: Log warning, continue to Telegram delivery.

[STATE 6: Telegram Message Format & Delivery]
  Primary action: Format bundle message; call Telegram Bot API sendMessage
  ─────────────────────────────────────────────────────────────────────────────
  ✅ SUCCESS → [EXIT: success]
  Terminal: "✓ Posts delivered to Telegram. Pillar: Build in Public | Promo ratio: 14%"
  Exit code 0.

  ❌ UNHAPPY PATH: Invalid Telegram bot token or chat ID
     📍 Trigger: Telegram API returns 401 Unauthorized or 400 Bad Request on first attempt
     👁️ User Sees: "✗ Telegram delivery failed: Invalid bot token or chat ID.
        Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env."
     🔄 Recovery Action: User verifies bot token via BotFather and chat ID
     🚪 Escape Hatch: Exit code 1. No retries (credentials are definitively wrong).

  ❌ UNHAPPY PATH: Telegram API temporarily unreachable
     📍 Trigger: Network error or Telegram service outage
     👁️ User Sees: "⚠ Telegram delivery failed. Retrying (attempt 1/3)..."
     🔄 Recovery Action: Exponential backoff retry
     🚪 Escape Hatch: After 3 failures → errors.log, exit code 1.
        "✗ Telegram delivery failed after 3 attempts. Posts were generated.
         See errors.log."

  ❌ UNHAPPY PATH: Message exceeds Telegram's 4,096-character limit
     📍 Trigger: Combined formatted message (all 3 platforms + metadata) exceeds limit
     👁️ User Sees: Three separate messages, one per platform section
     🔄 Recovery Action: System auto-splits by platform section before sending
     🚪 Escape Hatch: If any individual platform section exceeds 4,096 chars, truncate with note: "[Truncated — post exceeds display limit. Full text in errors.log]"
```

---

### Flow 2 — Telegram Bot /regenerate

```
[ENTRY] ──────────────────────────────────────────────────
  User sends /regenerate in Telegram chat

[STATE 1: Today's History Check]
  Primary action: Check history.json for a record dated today
  ─────────────────────────────────────────────────────────
  ✅ Record found → STATE 2

  ❌ UNHAPPY PATH: No posts generated today
     📍 Trigger: history.json has no entry for today's date
     👁️ User Sees: Bot replies: "No posts generated today yet. Use /generate first."
     🔄 Recovery Action: User sends /generate
     🚪 Escape Hatch: Flow ends. No further action.

[STATE 2: Platform Picker]
  Primary action: Bot sends inline keyboard — three buttons: [X] [LinkedIn] [Threads]
  ─────────────────────────────────────────────────────────────────────────────────
  ✅ User taps a button → STATE 3

  ❌ UNHAPPY PATH: User ignores inline keyboard (timeout)
     📍 Trigger: No callback received within a reasonable window
     👁️ User Sees: Keyboard remains active indefinitely (Telegram default)
     🔄 Recovery Action: User can tap any button at any time; flow resumes
     🚪 Escape Hatch: None needed — no timeout enforced on bot side.

[STATE 3: Single-Platform LLM Generation]
  Primary action: Build single-platform prompt; call litellm.completion()
  ─────────────────────────────────────────────────────────────────────────────
  ✅ SUCCESS → STATE 4

  ❌ UNHAPPY PATH: LLM failure
     📍 Trigger: API error or malformed output (same mechanics as Flow 1 STATE 4)
     👁️ User Sees: Bot sends: "⚠ Regeneration failed after 3 attempts. Try again later."
     🔄 Recovery Action: User retries /regenerate
     🚪 Escape Hatch: Error logged to errors.log. Bot does not crash.

[STATE 4: History Update & Delivery]
  Primary action: Overwrite today's record for selected platform in history.json;
                  send regenerated post to Telegram
  ─────────────────────────────────────────────────────────────────────────────
  ✅ SUCCESS → [EXIT]
  Bot sends regenerated post with platform header and metadata.

  ❌ UNHAPPY PATH: history.json write failure
     📍 Trigger: Permission error during save
     👁️ User Sees: Regenerated post still delivered; bot appends:
        "⚠ History not updated due to a file write error."
     🔄 Recovery Action: User checks file permissions
     🚪 Escape Hatch: Delivery succeeds regardless.
```

---

### Flow 3 — First-Time Setup (`postware init`)

```
[ENTRY] ──────────────────────────────────────
  User runs `python -m postware init`

[STATE 1: Existing File Check]
  Primary action: Check for existing config.yaml
  ─────────────────────────────────────────────
  ✅ No config.yaml found → STATE 2

  ❌ UNHAPPY PATH: config.yaml already exists
     📍 Trigger: File found at expected path
     👁️ User Sees: "⚠ config.yaml already exists.
        Overwrite? [y/N]: "
     🔄 Recovery Action: User types 'y' to overwrite → STATE 2
                         User types 'n' or hits Enter → skip config creation,
                         proceed with .env and history.json creation only
     🚪 Escape Hatch: 'n' preserves existing config. Flow continues for other files.

[STATE 2: File Creation]
  Primary action: Write config.yaml (placeholders), copy .env.example → .env,
                  create history.json (empty default structure)
  ─────────────────────────────────────────────────────────────────────────────
  ✅ SUCCESS → STATE 3

  ❌ UNHAPPY PATH: File system permission error
     📍 Trigger: Write permission denied in working directory
     👁️ User Sees: "✗ Cannot create files in current directory: [Errno 13].
        Check directory permissions."
     🔄 Recovery Action: User adjusts permissions or changes to a writable directory
     🚪 Escape Hatch: Exit code 1. No partial files left behind.

[STATE 3: Setup Checklist Output]
  Primary action: Print formatted setup checklist to terminal
  ─────────────────────────────────────────────────────────────────────────────────────
  ✅ SUCCESS → [EXIT: code 0]
  Output:
  "✓ Postware initialized.

   Next steps:
   [ ] 1. Open .env and add your LLM API key (e.g., ANTHROPIC_API_KEY)
   [ ] 2. Add your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env
   [ ] 3. Open config.yaml and fill in your project details
   [ ] 4. Create a Telegram bot via @BotFather if you haven't already
   [ ] 5. Run `python -m postware generate` to test your setup"
```

---

### Flow 4 — Daemon Mode (`postware start`)

```
[ENTRY] ──────────────────────────────────────────
  User runs `python -m postware start`

[STATE 1: Config Validation]
  Same as Flow 1 STATE 1. Any config error → exit code 1.

[STATE 2: Scheduler Initialization]
  Primary action: APScheduler reads schedule time from config.yaml; registers
                  daily job pointing to generation pipeline
  ─────────────────────────────────────────────────────────────────────────────
  ✅ SUCCESS → STATE 3
  Terminal: "✓ Daemon started. Next run scheduled for 08:00. Press Ctrl+C to stop."

  ❌ UNHAPPY PATH: Invalid schedule time in config
     📍 Trigger: time value not parseable (e.g., "8am" instead of "08:00")
     👁️ User Sees: "✗ Invalid schedule time '8am'. Use HH:MM format (e.g., 08:00)."
     🚪 Escape Hatch: Exit code 1.

[STATE 3: Running / Waiting]
  Primary action: Daemon blocks, waits for scheduled trigger time
  Each trigger → executes Flow 1 pipeline in full.
  ─────────────────────────────────────────────────────────────────────────────
  ❌ UNHAPPY PATH: SIGINT / SIGTERM received
     📍 Trigger: User presses Ctrl+C or system sends termination signal
     👁️ User Sees: "⚡ Shutdown signal received. Stopping Postware daemon."
     🔄 Recovery Action: APScheduler shuts down gracefully; no jobs interrupted
     🚪 Escape Hatch: Exit code 0.

  ❌ UNHAPPY PATH: Daemon process crashes
     📍 Trigger: Unhandled exception in scheduler or generation pipeline
     👁️ User Sees: Error written to errors.log; process exits
     🔄 Recovery Action: External process manager (systemd, supervisor) restarts daemon
     🚪 Escape Hatch: This is intentionally out of scope for Postware self-healing.
```

---

## Phase 3: Terminal View Layouts

### View 1 — Generation Success Output
```
┌─────────────────────────────────────────────────────────┐
│  POSTWARE                                               │
│─────────────────────────────────────────────────────────│
│  ✓ Posts generated and delivered to Telegram            │
│                                                         │
│  Date:         Monday, 2025-03-05                       │
│  Pillar:       P1 · Build in Public                     │
│  Promo ratio:  14% (target: ≤20%)                       │
│  LLM:          claude-3-5-sonnet (anthropic)            │
│  Duration:     12.4s                                    │
└─────────────────────────────────────────────────────────┘
```

### View 2 — Status Output (`postware status`)
```
┌─────────────────────────────────────────────────────────┐
│  POSTWARE STATUS                                        │
│─────────────────────────────────────────────────────────│
│  Today's pillar:      P1 · Build in Public              │
│  Promo ratio (14d):   14%  ████░░░░░░ (target: 20%)     │
│  Total posts:         87                                │
│  Last generated:      2025-03-04 08:03:11               │
│                                                         │
│  Pillar distribution (30d):                             │
│  P1 Build in Public   ██████████  33% (target 30%)      │
│  P2 Teaching          ████████    27% (target 25%)      │
│  P3 Opinions          █████       17% (target 15%)      │
│  P4 Data & Results    █████       13% (target 15%)      │
│  P5 Community         ████        10% (target 15%)      │
└─────────────────────────────────────────────────────────┘
```

### View 3 — Telegram Daily Bundle Message
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🐦 X (TWITTER)
Pillar: P1 · Build in Public | Format: Progress Update

[Post text — ≤280 chars]

📸 Image suggestion: Screenshot of git commit history
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💼 LINKEDIN
Pillar: P1 · Build in Public | Format: Behind-the-Scenes

[Post text — ≤1,500 chars]

📸 Image suggestion: Terminal screenshot of test run output
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧵 THREADS
Pillar: P1 · Build in Public | Format: Quick Update

[Post text — ≤500 chars]

📸 Image suggestion: Side-by-side before/after code comparison
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 2025-03-05 · Pillar: Build in Public · Promo: 14%
```

---

## Phase 4: System State Machine

```
[UNCONFIGURED] ──init──> [CONFIGURED]
                              │
               ┌──────────────┼──────────────┐
               │              │              │
          generate          start          status
               │              │              │
               ▼              ▼              ▼
        [GENERATING]    [DAEMON:IDLE]   [STATUS_OUT]
               │              │
        ┌──────┴──────┐   trigger
        │             │       │
    [LLM_CALL]   [LLM_FAIL]  [GENERATING]
        │             │
    [DELIVERING]  [ERROR_LOG]
        │
   ┌────┴────┐
   │         │
[SUCCESS]  [TELEGRAM_FAIL]
               │
           [ERROR_LOG]
```

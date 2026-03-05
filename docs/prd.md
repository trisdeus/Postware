# Product Requirements Document (PRD)

---

```
Project Name:   Postware
Document Type:  Product Requirements Document (PRD)
Version:        0.1
Date:           2025-03-05
Status:         Draft
```

---

## 1. Executive Summary

Postware is a Python CLI tool that automatically generates three platform-optimized social media posts per day — for X (Twitter), LinkedIn, and Threads — and delivers them as a formatted bundle to the developer's Telegram chat. It is built exclusively for solo developers and indie hackers who are building in public and need a consistent social media presence without sacrificing engineering time. The problem is acute right now: building-in-public has become a primary audience-growth strategy for solo founders, yet daily content creation remains a manual, context-switching tax that compounds across weeks and months. If Postware ships, the single most important outcome is that a developer can maintain a daily, on-strategy posting cadence across three platforms with zero daily effort beyond copying and pasting.

---

## 2. Problem Definition

### 2.1 Problem Statement

Solo developers building software in public struggle to maintain a consistent, platform-differentiated social media presence across X, LinkedIn, and Threads, resulting in an estimated 30–60 minutes of daily context-switching that displaces coding time and still produces content with inconsistent tone, repeated topics, and degraded audience growth.

### 2.2 Evidence & Validation

- ⚠️ **Assumption — requires validation via developer survey:** Estimated 30–60 minutes/day spent on social content creation by active build-in-public developers. Suggested validation: 10-question survey distributed via Indie Hackers or X/Twitter developer communities.
- ⚠️ **Assumption — requires validation via cohort analysis:** Developers who skip posting for 3+ consecutive days experience measurable audience growth stalls. Suggested validation: analysis of public follower-growth data from vocal build-in-public accounts.
- **Observed market gap:** Existing social media scheduling tools (Buffer, Hootsuite, Typefully) focus on scheduling pre-written content. None generate platform-differentiated posts from a developer's project context, and none enforce content strategy rules (pillar weights, value/promo ratios) automatically.
- **Platform format divergence is real and non-trivial:** X requires ≤280 characters and a witty tone; LinkedIn rewards ≤1,500-character professional narratives; Threads favors ≤500-character conversational posts with minimal hashtags. Writing three coherent but format-distinct posts daily from a single idea is a repeatable skill tax.
- **LLM accessibility makes this solvable today:** The availability of high-quality LLMs via API (Anthropic, OpenAI, Groq) and locally (Ollama) makes automated, context-aware post generation both technically feasible and low-cost (sub-$0.05/day for cloud providers).

### 2.3 Goals & Objectives (SMART Framework)

| # | Objective | Specific | Measurable | Achievable | Relevant | Time-Bound |
|---|---|---|---|---|---|---|
| G1 | Eliminate daily social content creation time | Generate and deliver three platform-ready posts requiring zero writing effort from the user | Generation-to-delivery pipeline completes in ≤60 seconds; user effort = copy + paste only | Single LLM call with structured output; well-defined prompt templates | Directly solves the primary daily time tax | From day 1 of first run |
| G2 | Maintain consistent posting cadence | Automate daily generation via cron or daemon so posts are ready every morning without user initiation | ≥90% of days in any rolling 30-day window have successful generation and delivery | APScheduler daemon or cron handles scheduling; retry logic handles transient failures | Cadence consistency is the core audience-growth lever | Over any 30-day period post-setup |
| G3 | Enforce content strategy automatically | Apply five weighted content pillars, weekly schedule, and 80/20 value/promo ratio without user tracking | Pillar distribution within ±5 percentage points of targets over 30 days; promo ratio between 15–25% | History-based pillar rotation and ratio enforcement built into generation logic | Content quality and audience trust depend on strategic consistency | Measurable after 14 days of history |
| G4 | Support model flexibility without friction | Allow switching between any LiteLLM-supported cloud or local LLM provider by editing one config field | Zero code changes required to switch providers; config validation catches bad values before any API call | LiteLLM unified interface abstracts all provider differences | Developer tools must respect the user's infrastructure choices and cost constraints | At launch |

### 2.4 Target Audience

**Primary Persona — "Shipping Sasha"**

- **Name/Archetype:** The Prolific Solo Builder
- **Demographics:** 25–40 years old; software developer, indie hacker, or technical founder; high technical literacy (comfortable with CLI, YAML, .env files, cron); likely working on a side project alongside a day job or full-time on an early-stage product
- **Behaviors:** Commits code daily; shares progress updates sporadically; has accounts on X, LinkedIn, and Threads but posts inconsistently; uses tools like Obsidian, Raycast, or Warp that live in the terminal; values automation and loathes repetitive non-coding tasks
- **Pain Points:**
  1. Spends 30–60 minutes daily writing social posts, often skipping days entirely when shipping pressure is high
  2. Writes the same idea three times in three different tones for three platforms — or worse, cross-posts the same text everywhere and gets poor engagement
  3. Loses track of content strategy (which topics have been covered, whether recent posts have been too promotional) because there is no system
- **Goals:** Maintain a daily, on-brand social presence that grows their audience and builds credibility — without it feeling like a second job

---

**Anti-Persona — Who Postware Is NOT For**

- **Marketing teams and agencies:** Postware is a single-user local tool with no multi-user support, no approval workflows, no brand asset management, and no analytics dashboard. Teams need collaborative tools with role-based access.
- **Non-technical users:** Postware requires Python 3.10+, comfort with CLI commands, YAML file editing, and Telegram bot setup. Users who cannot configure a `.env` file are not the target and would find setup prohibitive.
- **Developers who want to autopost directly:** Postware deliberately excludes direct posting to social platforms. Users who want zero-touch automation (generate AND publish without manual copy-paste) are out of scope; direct social API integration is explicitly deferred.

---

## 3. Feature Prioritization (MoSCoW)

| # | Feature Name | User Story | Priority | Rationale / Notes |
|---|---|---|---|---|
| F1 | Content Generation Engine | As a solo developer, I want the system to generate three platform-optimized posts using my project context so that I receive ready-to-publish content with zero writing effort. | P0 — Must | The entire product's value proposition. Without this, nothing else matters. |
| F2 | Telegram Delivery | As a solo developer, I want the generated posts delivered to my Telegram chat as a formatted bundle so that I can copy and publish from any device. | P0 — Must | Delivery is the final mile. Posts generated but not delivered provide no value. |
| F3 | Content Pillar Rotation & 80/20 Enforcement | As a solo developer, I want the system to automatically apply the weekly pillar schedule and enforce the value-to-promo ratio so that my content strategy runs on autopilot. | P0 — Must | Without strategy enforcement, the tool generates content but not *on-strategy* content — defeating the core value proposition. |
| F4 | File-Based History & Deduplication | As a solo developer, I want the system to track recent posts locally so that content is never repeated and pillar rotation stays on target. | P0 — Must | History is the foundation for rotation, ratio calculation, and deduplication. Without it, every day is a cold start. |
| F5 | LLM Flexibility (LiteLLM) | As a solo developer, I want to configure my LLM provider in a YAML file so that I can use cloud or local models without changing source code. | P0 — Must | Different developers have different cost constraints and privacy preferences. Hardcoding a single provider would exclude a significant portion of the target audience. |
| F6 | CLI Interface (generate / status / init / start) | As a solo developer, I want clear CLI commands so that I can run, configure, and inspect Postware from the terminal. | P0 — Must | The CLI is the primary control surface for the tool. Without it there is no interface. |
| F7 | Error Logging (`errors.log`) | As a solo developer, I want all failure details written to `errors.log` so that I can debug problems without re-running the pipeline. | P0 — Must | Promoted to P0 per BDD v0.2. A tool that fails silently is not production-ready. |
| F8 | Retry Logic (LLM + Telegram) | As a solo developer, I want the system to automatically retry failed API calls so that transient outages do not require manual intervention. | P1 — Should | Transient failures are expected in API-dependent tools. Three retries with exponential backoff is a minimal reliability guarantee. |
| F9 | Telegram Bot Commands (/generate, /regenerate, /status) | As a solo developer, I want to trigger generation and check status from Telegram so that I can interact with Postware without opening a terminal. | P1 — Should | High convenience value; /regenerate is particularly important for correcting a single off-target post without re-running the full pipeline. |
| F10 | APScheduler Daemon Mode | As a solo developer, I want a long-running daemon mode so that daily generation runs automatically without setting up a cron entry. | P1 — Should | Lowers the operational barrier for users unfamiliar with cron syntax, and provides a more observable process. |
| F11 | Telegram Sender Authorization | As a solo developer, I want the bot to reject commands from unknown Telegram users so that no one else can trigger LLM calls or read my content history. | P1 — Should | Single-user tool operating on the user's own API keys. Unauthorized access creates real cost exposure. |
| F12 | Log Redaction Filter | As a solo developer, I want API keys and secrets automatically redacted from `errors.log` so that sensitive credentials are never stored in a plaintext file. | P1 — Should | A tool that writes secrets to a log file violates basic operational security. |
| F13 | Prompt Injection Sanitization | As a solo developer, I want user-supplied config values sanitized before LLM prompt inclusion so that malformed inputs cannot override my content strategy instructions. | P1 — Should | Low implementation cost; prevents accidental or adversarial degradation of output quality. |
| F14 | Local File Permissions (Unix + Windows ACLs) | As a solo developer, I want `init` to set restrictive file permissions on `.env` and `config.yaml` so that other local users or processes cannot read my API keys. | P1 — Should | The `.env` file contains high-value API credentials. Default file permissions on multi-user systems leave them exposed. |
| F15 | API Key Format Validation | As a solo developer, I want early-warning format checks on my API keys so that I am alerted to malformed credentials before any external API call is attempted. | P1 — Should | Prevents confusing auth errors deep in the pipeline; the check is low-cost and high-signal. |
| F16 | Secure Dependency Scanning (`pip-audit`) | As a solo developer, I want the `init` command to audit my dependencies for known vulnerabilities so that I am alerted to supply-chain risks at setup time. | P1 — Should | LiteLLM and python-telegram-bot are large dependency trees. CVEs in transitive dependencies are a real risk category. |
| F17 | Windows ACL Hardening | As a solo developer on Windows, I want `init` to apply native Windows ACLs to sensitive files so that other local accounts cannot read my API keys. | P1 — Should | The Unix chmod approach provides zero protection on Windows. Windows users deserve equivalent security. |
| F18 | Direct Social Media Posting | As a solo developer, I want Postware to automatically post to X, LinkedIn, and Threads so that I don't need to copy and paste. | P3 — Won't (this version) | Requires per-platform OAuth flows, API approvals (especially X), terms of service compliance, and error handling for post rejection. Significantly out of scope for v1.0. |
| F19 | Web UI / Dashboard | As a solo developer, I want a browser-based dashboard to manage Postware so that I don't need to use the terminal. | P3 — Won't (this version) | Contradicts the CLI-first design philosophy and single-user local tool architecture. |
| F20 | Multi-User Support | As a team, I want multiple developers to share a single Postware instance so that we can generate posts for a shared project. | P3 — Won't (this version) | Requires authentication, authorization, isolated history per user, and shared config management. Architectural change, not an incremental feature. |

**MVP Scope Boundary**:
v0 (initial release): Ships F1–F7 (all P0 features) only — content generation engine, Telegram delivery, pillar rotation and 80/20 enforcement, file-based history, LLM flexibility, CLI interface, and error logging. The tool is functional and useful but carries no security hardening, no bot command interactivity, and no daemon mode.
v1 (first production-ready release): Adds F8–F17 (all P1 features) — retry logic, Telegram bot commands, daemon mode, and all five security measures. This is the minimum bar for recommending Postware for daily use on a shared or professional machine.
F18–F20 are explicitly deferred and will not be considered for inclusion without a separate scoping exercise.

---

## 4. Detailed Requirements

### 4.1 User Flows

Four primary flows govern all user interactions. Full step-by-step detail, decision points, and error states are specified in the approved App Flow Document (v0.1). Summaries below.

**Flow 1 — Daily Post Generation (CLI / Cron / Daemon):**
Entry via `python -m postware generate`, scheduled cron job, or Telegram `/generate` command. System loads and validates config → loads history → resolves pillar and promo ratio → constructs LLM prompt → calls LiteLLM → parses and validates output → writes history → formats and delivers Telegram message → exits code 0. Any failure at any stage triggers retry logic (where applicable) and ultimately exits code 1 with errors logged.

**Flow 2 — Telegram Bot /regenerate:**
User sends `/regenerate` → bot checks for today's generation record → presents platform picker (inline keyboard) → user selects one platform → system regenerates only that platform's post → overwrites today's history record → delivers regenerated post.

**Flow 3 — First-Time Setup (init):**
User runs `python -m postware init` → system checks for existing config → creates `config.yaml`, `.env`, `history.json` with safe defaults → sets file permissions → runs dependency audit → prints setup checklist → exits code 0.

**Flow 4 — Daemon Mode (start):**
User runs `python -m postware start` → config validated → APScheduler initialized with `config.schedule.time` → daily job registered → daemon blocks → each trigger executes Flow 1 in full → SIGINT/SIGTERM triggers graceful shutdown.

### 4.2 Functional Requirements

#### FR-001: Content Generation Engine

| Attribute | Specification |
|---|---|
| Trigger | `generate` CLI command, Telegram `/generate`, or APScheduler daily trigger |
| Pillar resolution | Map current day-of-week to pillar per fixed weekly schedule: Mon→P1, Tue→P2, Wed→P3, Thu→P4, Fri→P1, Sat→P5, Sun→P2 |
| Promo ratio check | Calculate promotional post percentage over rolling 14-day window from `history.json`; if ≥20%, force `is_promotional = false` in prompt regardless of pillar |
| Deduplication context | Include summaries of last 10 generation records in LLM prompt to prevent topic repetition |
| Output | Three `PlatformPost` objects (X, LinkedIn, Threads), each containing: `text`, `format_type`, `image_suggestion` |
| Validation | Output validated against Pydantic `GeneratedBundle` model; character limits enforced per platform |
| Retry | 3 attempts with 1s/2s/4s exponential backoff on LLM failure or output validation failure |
| On final failure | Log full error details to `errors.log`; exit code 1; no Telegram delivery; `history.json` not modified |

#### FR-002: Platform-Specific Formatting Rules

| Platform | Max Characters | Tone | Hashtags | Links |
|---|---|---|---|---|
| X (Twitter) | 280 | Casual, witty | 1–3 | Not inline |
| LinkedIn | 1,500 | Professional, insightful | 3–5 | Allowed |
| Threads | 500 | Conversational | 0–2 | Not allowed |

#### FR-003: Content Pillar Weights and Weekly Schedule

| Pillar | ID | Target Weight | Scheduled Days |
|---|---|---|---|
| Build in Public | P1 | 30% | Monday, Friday |
| Teaching | P2 | 25% | Tuesday, Sunday |
| Opinions | P3 | 15% | Wednesday |
| Data & Results | P4 | 15% | Thursday |
| Community | P5 | 15% | Saturday |

Pillar rotation logic adjusts selection if recent history shows a pillar significantly over its target weight. The adjustment operates as a nudge, not a hard override — the weekly schedule takes priority; rotation prevents chronic over-indexing across weeks.

#### FR-004: History Management

| Attribute | Specification |
|---|---|
| Storage | `history.json` in project root; plain JSON; no database |
| Max entries | 30; oldest pruned on save |
| Atomic writes | Write to `history.json.tmp` → rename to `history.json` |
| Corruption recovery | Detect invalid JSON on load → back up to `history.json.bak` → create fresh file → log warning → continue |
| Missing file | Create with empty `{ "records": [] }` structure; log info message; continue |
| Concurrent access | Not addressed; single-process assumption enforced |

#### FR-005: Telegram Delivery

| Attribute | Specification |
|---|---|
| Message structure | Single message: three sections (X, LinkedIn, Threads) separated by horizontal dividers; each section contains post text, pillar label, format type, image suggestion; footer shows date, pillar, and promo ratio |
| Message splitting | If formatted message exceeds 4,096 characters, split into three messages by platform section |
| Retry | 3 attempts with 1s/2s/4s exponential backoff |
| Invalid credentials | Exit code 1 on first attempt with no retry; credentials are definitively wrong |
| Authorization | All incoming bot commands validated against `TELEGRAM_CHAT_ID`; unauthorized senders silently discarded |

#### FR-006: CLI Commands

| Command | Behaviour | Exit Code on Success |
|---|---|---|
| `python -m postware generate` | One-shot full pipeline run | 0 |
| `python -m postware start` | Long-running daemon with APScheduler | 0 (on graceful shutdown) |
| `python -m postware status` | Print today's pillar, 14-day promo ratio, total posts, last generation timestamp | 0 |
| `python -m postware init` | Scaffold config files, set permissions, run dependency audit, print checklist | 0 |

#### FR-007: Telegram Bot Commands

| Command | Behaviour |
|---|---|
| `/generate` | Triggers full generation pipeline; delivers bundle to chat |
| `/regenerate` | Presents platform picker; regenerates single platform post; updates history |
| `/status` | Returns today's pillar, 14-day promo ratio, total posts generated, last generation timestamp |

#### FR-008: LLM Provider Support

Supported providers via LiteLLM unified interface:

| Tier | Providers |
|---|---|
| Native cloud | `anthropic`, `openai`, `groq`, `google` |
| Extended cloud | `deepseek`, `qwen`, `minimax`, `kimi`, `z.ai` |
| Local / custom | `ollama`, `lmstudio`, `custom` (requires `base_url`) |

### 4.3 Non-Functional Requirements

| Category | Requirement | Version | Rationale |
|---|---|---|---|
| **Performance** | End-to-end pipeline completes in ≤60 seconds under normal conditions with a cloud LLM provider | v0 | LLM response is the primary variable; 60s is a generous but meaningful upper bound |
| **Performance** | `history.json` read, process, and write operations complete in ≤500ms | v0 | Max 30 records; O(30) full scan; generous bound |
| **Reliability** | ≥90% of days in any rolling 30-day window result in successful generation and delivery | v0 | Core product promise; requires retry logic (v1) to be reliably achievable in practice |
| **Reliability** | Retry logic exhausted before any non-zero exit; no silent failures | v1 | Automatic retry is a P1 feature; v0 fails fast on first API error with a logged error and non-zero exit |
| **Security** | API keys and Telegram token never written to `errors.log` in plaintext | v1 | Log redaction filter is a P1 security measure |
| **Security** | `.env`, `config.yaml`, `history.json` created with `0o600` permissions on Unix; Windows ACLs applied on Windows | v1 | File permission hardening is a P1 security measure |
| **Security** | All Telegram bot commands validated against `TELEGRAM_CHAT_ID` before execution | v1 | Telegram bot commands are a P1 feature; authorization ships with them |
| **Compatibility** | Runs on Python 3.10+ on macOS, Linux, and Windows | v0 | Broadest developer machine coverage |
| **Compatibility** | Zero breaking changes to `history.json` schema between patch versions | v0 | User's local history must survive upgrades from day one |
| **Observability** | All terminal output styled via Rich with consistent status icons (✓, ✗, ⚠, ℹ) | v0 | Scannable output is critical for a tool run in automated cron contexts |
| **Startup time** | `python -m postware status` returns output in ≤2 seconds | v0 | Status is read-only; no LLM or Telegram calls involved |

### 4.4 Edge Cases

| # | Edge Case | Category | Expected Behaviour |
|---|---|---|---|
| EC-01 | `config.yaml` missing required field | Invalid input | Exit code 1; Rich-formatted error lists every missing field by name; no API calls made |
| EC-02 | `history.json` contains invalid JSON | Data corruption | Back up to `.bak`; create fresh file; log warning; continue |
| EC-03 | Promotional ratio ≥20% | Business rule | Force `is_promotional = false` in LLM prompt; log info message; continue |
| EC-04 | LLM returns output missing one platform post | API response | Treat as validation failure; retry up to 3 times; log on final failure |
| EC-05 | Ollama/LM Studio server not running | Connectivity | Connection refused detected; retry 3×; exit code 1 with actionable error message advising user to start the server |
| EC-06 | Telegram message exceeds 4,096 characters | Size limit | Auto-split into three messages by platform section before sending |
| EC-07 | Telegram invalid bot token or chat ID | Auth failure | Exit code 1 on first attempt; no retry; clear error message distinguishing token vs. chat ID issues |
| EC-08 | `/regenerate` called before any generation today | State prerequisite | Bot replies: "No posts generated today yet. Use /generate first."; no LLM call made |
| EC-09 | `init` run when `config.yaml` already exists | Idempotency | Prompt user to confirm overwrite `[y/N]`; default is preserve; `.env` and `history.json` created regardless |
| EC-10 | SIGINT/SIGTERM received during daemon run | Process lifecycle | APScheduler shuts down gracefully; running job (if mid-pipeline) is allowed to complete or times out within 30 seconds; exit code 0 |
| EC-11 | `history.json` write fails (permission error) | File system | Log warning; Telegram delivery proceeds; history not updated for this run |
| EC-12 | Unsupported provider string in `config.yaml` | Validation | Exit code 1; error lists all supported providers; suggests `custom` with `base_url` for unlisted LiteLLM providers |
| EC-13 | API key format validation warning | Security | Warning emitted to terminal and `errors.log`; system does NOT exit; continues to LLM call |
| EC-14 | `pip-audit` not installed when `init` runs | Missing tooling | Warning printed; audit skipped; `init` continues normally; exit code 0 |
| EC-15 | Unauthorized Telegram user sends `/generate` | Security | Silent discard; no response sent; DEBUG log entry written; no LLM call made |

---

## 5. Design & UX Requirements

### 5.1 Interface Philosophy

Postware has two interfaces: the terminal and the Telegram chat. Both must feel like tools built by a developer who respects the user's time and attention.

**Terminal:** Output must be scannable in under 3 seconds. Every line of output serves a purpose — no verbose logging on success paths, no stack traces exposed to the user (those go to `errors.log`). Rich formatting provides visual hierarchy. Status icons (✓, ✗, ⚠, ℹ) communicate state at a glance before the user reads the text.

**Telegram:** The daily bundle is the product. The message must be immediately usable — a developer should be able to open Telegram, read the three posts, and begin copy-pasting to social platforms within 60 seconds. No clutter, no unnecessary metadata beyond what aids decision-making.

### 5.2 Terminal Output Specifications

| Output Context | Rich Style | Content |
|---|---|---|
| Generation success | Green `✓` prefix | Date, pillar, promo ratio, LLM provider, pipeline duration |
| Validation error | Red `✗` prefix | Specific field or constraint that failed; actionable fix |
| Warning (non-fatal) | Yellow `⚠` prefix | What was detected; what the system did in response |
| Info (auto-recovery) | Blue `ℹ` prefix | What happened; no action required from user |
| Status output | Rich table or panel | Pillar, promo ratio with inline bar, total posts, last run timestamp, 30-day pillar distribution |
| Init output | Checklist format | Numbered action items with checkbox prefix `[ ]` |

### 5.3 Telegram Message Specifications

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🐦 X (TWITTER)
Pillar: [Pillar Name] | Format: [Format Type]

[Post text]

📸 [Image suggestion]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💼 LINKEDIN
Pillar: [Pillar Name] | Format: [Format Type]

[Post text]

📸 [Image suggestion]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧵 THREADS
Pillar: [Pillar Name] | Format: [Format Type]

[Post text]

📸 [Image suggestion]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 [YYYY-MM-DD] · [Pillar Name] · Promo: [X]%
```

### 5.4 Accessibility

N/A for this product in the traditional sense — Postware is a CLI tool and Telegram client. Screen reader compatibility is provided by the terminal emulator and Telegram app natively. Rich library output uses Unicode characters and emoji; if a terminal does not support Unicode, Rich degrades gracefully to plain ASCII equivalents. No additional accessibility work is required for v1.0.

---

## 6. Technical Constraints & Architecture Summary

### 6.1 Technology Stack

| Component | Technology | Justification |
|---|---|---|
| Language | Python 3.10+ | Developer tool audience is comfortable with Python; ecosystem has best-in-class libraries for every required function |
| LLM interface | LiteLLM | Single unified interface for all cloud and local providers; eliminates per-provider integration code |
| Telegram | python-telegram-bot | Mature, well-maintained; supports both polling (bot commands) and direct message sending |
| Config | PyYAML + python-dotenv | YAML is human-readable and editable; .env is the established standard for credential management |
| Validation | Pydantic v2 | Fast, type-safe; first-class YAML and dict validation; excellent error messages |
| Scheduling | APScheduler | Lightweight; supports cron-style triggers; no external broker required |
| Terminal output | Rich | Best-in-class Python terminal formatting; tables, panels, progress indicators |
| Data storage | JSON flat file | Zero dependencies; human-readable; sufficient for ≤30 records |

### 6.2 Architecture Constraints

- **No database libraries.** SQLite and any ORM are explicitly out of scope. `history.json` is the only persistent store.
- **No web server.** Postware runs as a local CLI process. No HTTP server, no port binding, no network-facing service.
- **No direct social media API integration.** X, LinkedIn, and Threads APIs are out of scope for v1.0.
- **Single-process assumption.** No concurrency model is required. File operations assume exclusive access.
- **Local execution only.** No cloud deployment, no Docker containerisation, no hosted infrastructure required.

### 6.3 Project Structure

```
postware/
├── pyproject.toml
├── .env.example
├── config.yaml
├── README.md
├── history.json
├── errors.log
├── src/
│   └── postware/
│       ├── __init__.py
│       ├── main.py           # CLI entrypoint
│       ├── config.py         # Config loader + validation
│       ├── models.py         # Pydantic data models
│       ├── generator.py      # Content generation engine
│       ├── prompts.py        # Prompt builder + sanitization
│       ├── history.py        # History manager
│       ├── telegram_bot.py   # Delivery + bot commands
│       ├── scheduler.py      # APScheduler daemon
│       └── platform_utils.py # File permissions (Unix + Windows)
├── tests/
└── scripts/
    └── audit_deps.py         # Standalone dependency scanner
```

---

## 7. Key Performance Indicators (KPIs)

### 7.1 North Star Metric

- **Metric:** Percentage of days in a rolling 30-day window with successful generation and Telegram delivery (Generation Consistency Rate)
- **Why This Metric:** Postware's core promise is eliminating the daily content creation burden. A post that was never generated and delivered provides zero value, regardless of how good the LLM output quality is on the days it does run. Consistency is the product.
- **Current Baseline:** Not applicable — greenfield product; baseline established from first 30 days of use
- **Target:** ≥90% (27 or more successful days out of any rolling 30-day window)

### 7.2 Supporting KPIs

| KPI | Definition | Target | Measurement Method |
|---|---|---|---|
| Pillar Distribution Accuracy | Distribution of pillar usage over 30 days vs. target weights (P1: 30%, P2: 25%, P3: 15%, P4: 15%, P5: 15%) | Within ±5 percentage points of each target | Derived from `history.json`; visible in `postware status` |
| Promotional Ratio | Percentage of promotional posts in rolling 14-day window | Between 15% and 25% (centred on 20% target) | Derived from `history.json` `is_promotional` field |
| Pipeline Duration | End-to-end time from command invocation to Telegram delivery confirmation | ≤60 seconds (p95) with a cloud LLM provider | Logged in terminal success output |
| Setup Time | Time from `python -m postware init` to first successful `generate` run | ≤10 minutes for a user familiar with CLI tools | Manual testing benchmark |
| Error Recovery Rate | Percentage of transient LLM or Telegram failures resolved by automatic retry (without requiring user intervention) | ≥80% of failures resolved within 3 retry attempts | Ratio of retry-success log entries to total error log entries |

### 7.3 Guardrail Metrics

- Generation pipeline must not exceed 60 seconds (p95) as new LLM providers or history entries are added.
- `history.json` must never exceed 30 entries after a save operation — the pruning invariant must hold on every write.
- `errors.log` must never contain a string matching any known API key format (enforced by log redaction filter).

---

### 8. Security Requirements

All security measures are **v1 features**. v0 ships with no security hardening beyond standard `.gitignore` exclusion of `.env`. Users running v0 on a single-user personal machine accept this trade-off explicitly.

| Measure | Requirement | Version | Module |
|---|---|---|---|
| Telegram authorization | All bot commands validate sender ID against `TELEGRAM_CHAT_ID`; unauthorized senders silently discarded | v1 | `telegram_bot.py` |
| Log redaction | `RedactionFilter` applied to all log handlers; API keys and Telegram token never written in plaintext | v1 | Shared logger |
| Prompt sanitization | All `AppConfig` string fields sanitized via `sanitize_for_prompt()` before LLM prompt inclusion | v1 | `prompts.py` |
| File permissions (Unix) | `0o600` applied to `.env`, `config.yaml`, `history.json` via `os.chmod()` during `init` | v1 | `platform_utils.py` |
| File permissions (Windows) | Windows ACLs applied via `pywin32` (preferred) or `icacls` subprocess (fallback) during `init` | v1 | `platform_utils.py` |
| API key format validation | Format regex checks on startup; warnings emitted for suspicious key shapes; non-blocking | v1 | `config.py` |
| Dependency scanning | `pip-audit` runs during `init`; standalone `scripts/audit_deps.py` for manual and scheduled audits | v1 | `scripts/audit_deps.py` |

> **v0 security posture:** API keys stored in `.env` excluded from version control via `.gitignore`. No other hardening applied. Suitable for single-user personal machines only. Users on shared machines should upgrade to v1 before storing real API credentials.

---

## 9. Dependencies & Assumptions

### 9.1 External Dependencies

| Dependency | Type | Risk if Unavailable |
|---|---|---|
| LiteLLM library | Runtime | Critical — entire generation pipeline blocked |
| Chosen LLM provider API | Runtime (cloud) | Critical — generation blocked; mitigated by local model support |
| Ollama / LM Studio | Runtime (local, optional) | Generation blocked for local-model users only |
| Telegram Bot API | Runtime | Critical — delivery blocked even if generation succeeds |
| python-telegram-bot | Runtime | Critical — bot and delivery code cannot function |
| pip-audit | Dev / init-time optional | Non-critical — dependency audit skipped with warning |
| pywin32 | Init-time optional (Windows) | Non-critical — falls back to `icacls` |

### 9.2 Assumptions

| Assumption | Risk if False | Mitigation |
|---|---|---|
| User has Python 3.10+ installed | Cannot run Postware at all | Document clearly in README; `init` checks Python version and exits with clear error if below 3.10 |
| User has created a Telegram bot via BotFather and knows their chat ID | Delivery impossible | `init` checklist step 4 provides BotFather setup instructions |
| User is comfortable editing YAML and `.env` files | Setup abandoned | `init` command and checklist minimise required edits; placeholder values and inline comments in generated `config.yaml` |
| Chosen LLM provider API is available and the key is valid | Generation fails on every run | API key format validation + clear error messaging on first failure |
| For local models: Ollama is installed and the target model is pulled | Generation fails | Error message explicitly advises `ollama serve` and `ollama pull <model>` |
| Single-user machine or user accepts shared-machine security trade-offs | API keys readable by other local users | File permission hardening via `init` mitigates; documented in README |

---

## 10. Open Questions

| # | Question | Impact | Owner | Resolution Path |
|---|---|---|---|---|
| OQ-01 | Should Postware support multiple project profiles (e.g., generating posts for two different products from one installation)? | Medium — architecture impact on config schema and history isolation | Product decision | Deferred to v1.1; current design assumes single project per installation |
| OQ-02 | Should the 80/20 promotional ratio be user-configurable, or is the 20% ceiling a fixed product constraint? | Low — config schema change only | Product decision | Current spec treats 20% as a fixed ceiling; configurable ratio deferred to v1.1 |
| OQ-03 | Should the weekly pillar schedule be user-configurable (e.g., swap Wednesday's Opinions for more Build in Public)? | Low — config schema addition | Product decision | Fixed schedule ships in v1.0; user-configurable schedule deferred to v1.1 |
| OQ-04 | What is the correct behaviour when `/generate` is called multiple times in one day via the Telegram bot — should subsequent runs be blocked, warned, or allowed silently? | Low — UX decision | Product decision | Current spec allows repeated runs; user warned via info message |
| OQ-05 | Should `errors.log` be rotated or capped at a maximum file size to prevent unbounded growth? | Low — operational hygiene | Engineering decision | Deferred to v1.1; current spec has no log rotation |

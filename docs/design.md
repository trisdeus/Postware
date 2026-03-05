# Design Document

---

```
Project Name:   Postware
Document Type:  Design Document
Version:        0.1
Date:           2025-03-05
Status:         Draft
```

---

## Foreword — Design Scope for a CLI + Telegram Tool

Postware has no graphical UI in the conventional sense. Its two interfaces are the terminal (styled via the Rich library) and the Telegram chat client. This document therefore departs from a standard mobile/web design system and instead specifies: a terminal design language (token system, output patterns, component states), a Telegram message design system (layout, typography, symbol language), and the interaction design of the bot command flows. Where platform-specific guidance exists for terminal rendering and Telegram formatting, it is noted explicitly.

---

## Phase 1: Design Style Foundation

### 1.1 User Persona & Context

| Attribute | Value |
|---|---|
| **Product** | Postware — Python CLI tool for automated social content generation |
| **Category** | Developer tool / CLI utility |
| **Primary User** | Solo developer or indie hacker, 25–40 years old, high technical literacy, comfort with terminal environments |
| **Vibe — Three Adjectives** | **Precise, Trustworthy, Efficient** |
| **Usage Context** | Sitting at a desk or glancing at a phone; running commands from a terminal; reading the Telegram bundle over morning coffee. No outdoor/sunlight constraint. Terminal is often dark-themed. |
| **Usage Frequency** | Daily — the tool must feel fast and unobtrusive, never demanding attention beyond a glance |
| **Primary Interface** | Terminal (macOS/Linux/Windows) + Telegram mobile client |

**Vibe rationale:**
- **Precise** — a developer trusts a tool that is exact and unambiguous. Every output line means something specific.
- **Trustworthy** — the tool handles API keys, writes files, and makes API calls on the user's behalf. Visual calm and consistency build confidence.
- **Efficient** — no ceremony, no noise. Output is minimal by default; detail is surfaced only on failure or when explicitly requested.

### 1.2 Competitive Audit

**Direct Comparators — CLI Developer Tools**

| Tool | Dominant Design Patterns | Does Well | Weakness |
|---|---|---|---|
| **GitHub CLI (`gh`)** | Monochromatic with sparse color; status icons (✓, ✗, !); compact single-line outputs; progressive detail on `--verbose` | Information hierarchy is excellent — success states are quiet, errors are prominent | Long outputs can feel unscannable without grouping |
| **Vercel CLI** | Bold brand color (black/white), Rich-style spinner animations, prominent success/failure banners | Celebratory success states build positive reinforcement | Verbose by default; too much output for automated/cron contexts |
| **Stripe CLI** | Clean sans-serif, cyan accent for events, structured JSON output for logs | Excellent at distinguishing user-facing messages from raw data | Event stream output not optimized for non-power users |

**Indirect Comparators — Adjacent Behavioral Need**

| Tool | Connection to Postware |
|---|---|
| **Datasette** | Developer-facing tool that must communicate complex data in a clean, immediately legible format — same cognitive challenge as Postware's status output |
| **Telegram Bot API bots (e.g., @ControllerBot)** | Shares the Telegram-as-UI paradigm: inline keyboards, formatted messages, emoji as visual anchors — establishes user expectations for the /regenerate flow |

**Pattern Opportunities:**
1. **Adopt: Status icon prefix system** (`✓`, `✗`, `⚠`, `ℹ`) — used consistently by `gh` and Stripe CLI; developers read the icon before the text. Zero learning curve.
2. **Adopt: Quiet success, loud failure** — successful operations should produce minimal output (one summary line); failures should be visually distinct and immediately actionable.
3. **Avoid: Verbose default output** — Vercel CLI's approach is appropriate for interactive sessions but breaks cron/daemon contexts where output goes to system logs. Postware's cron mode must default to silent-on-success.

### 1.3 Moodboard Direction

| Attribute | Direction |
|---|---|
| **Visual Style Label** | Terminal Minimalism |
| **Color Mood** | Deep charcoal backgrounds (#1C1C1E) · Bright semantic greens and reds for state · Muted cool-grey for secondary text |
| **Typography Mood** | Monospace for data and code values; sans-serif for prose labels. The combination signals: "this is a tool that respects what it's showing you." |
| **Shape Language** | No shapes in the traditional sense. Structure is created by whitespace, box-drawing characters, and consistent column alignment. |
| **Imagery Style** | Iconography-driven — emoji as semantic anchors in Telegram; Rich-rendered Unicode symbols in terminal |
| **Micro-interaction Tone** | Subtle and functional — spinner on generation, progress indication on retries, clean confirmation on success. No animations for their own sake. |
| **Reference Tools** | `gh` (GitHub CLI) · Charm's `glow` and `bubbletea` ecosystem · Linear's keyboard-first interaction philosophy · Telegram's own `@BotFather` for message formatting conventions |

**Design direction summary:** Based on this foundation, the design system will target a **Terminal Minimalism** aesthetic optimised for **daily automated use in dark terminal environments** by **a high-literacy solo developer who values signal over noise**.

---

## Phase 2: Patterns & Themes

### 2.1 Design Language Selection

**Custom/Terminal-Native Design Language**

Neither Material Design nor Apple HIG is applicable to a CLI + Telegram interface. The design language is derived from three sources:

1. **Rich library's component model** — panels, tables, progress bars, and text styles are the primitive building blocks. Design decisions must be expressible as Rich API calls.
2. **Telegram Bot API message formatting** — MarkdownV2 and emoji are the only formatting primitives available. The design must work within Telegram's constraints.
3. **UNIX CLI conventions** — exit codes, stderr vs stdout, signal handling, and standard output patterns are part of the design, not just implementation details.

### 2.2 Navigation Architecture

Postware has two navigation contexts, each with a distinct pattern.

**Terminal — Flat Subcommand Model (Hub-and-Spoke)**

```
python -m postware
├── generate     → runs full pipeline, outputs summary, exits
├── start        → enters daemon loop, blocks until SIGINT
├── status       → outputs status panel, exits
└── init         → scaffolds files, outputs checklist, exits
```

No persistent state between invocations (except `start`). Each command is self-contained. This mirrors the `git`, `gh`, and `docker` subcommand model — zero learning curve for the target persona.

**Telegram — Linear Command Flow**

```
Bot commands
├── /generate    → triggers pipeline → delivers bundle (no further interaction)
├── /status      → returns status message (no further interaction)
└── /regenerate  → presents inline keyboard → user picks platform → delivers post
                   └── [X] [LinkedIn] [Threads]  (single-level hub-and-spoke)
```

The deepest interaction is two steps: command → button tap. This is intentional. The bot is a remote control, not an application. Every interaction must resolve within two steps maximum.

### 2.3 Color System

Postware's color system operates in two environments with different rendering capabilities.

#### Terminal Color System (Rich library — ANSI colors)

Postware targets 256-color and True Color terminal support (the default on modern macOS/Linux terminal emulators). The system uses semantic color tokens mapped to Rich style strings.

**60-30-10 Rule Application:**
- **60% Dominant (Neutral):** Default terminal background — no explicit color set; inherits from user's terminal theme. Text color: `--term-text-primary`.
- **30% Secondary:** Structural elements — borders, dividers, labels, metadata. Uses muted grey tones.
- **10% Primary (Accent):** Status indicators and key values. Semantic colors only — no decorative accent.

| Token | Rich Style String | Hex (True Color) | Usage | WCAG Contrast vs Dark BG (#1C1C1E) |
|---|---|---|---|---|
| `--term-text-primary` | `white` | `#F5F5F5` | Primary message text | 18.1:1 — AAA |
| `--term-text-secondary` | `bright_black` | `#6E6E6E` | Metadata, secondary labels | 3.2:1 — AA Large |
| `--term-text-muted` | `grey50` | `#808080` | Timestamps, version strings | 4.6:1 — AA |
| `--term-success` | `bright_green` | `#34C759` | ✓ Success states | 8.2:1 — AAA |
| `--term-error` | `bright_red` | `#FF453A` | ✗ Failure states | 5.1:1 — AA |
| `--term-warning` | `yellow` | `#FFD60A` | ⚠ Warning states | 12.4:1 — AAA |
| `--term-info` | `bright_blue` | `#0A84FF` | ℹ Informational | 4.7:1 — AA |
| `--term-border` | `grey30` | `#4D4D4D` | Panel borders, dividers | N/A (structural) |
| `--term-label` | `cyan` | `#32ADE6` | Field labels in tables | 6.3:1 — AA |
| `--term-highlight` | `bold white` | `#FFFFFF` | Key values, pillar names | 19.6:1 — AAA |

> **Note on light terminal themes:** Rich applies ANSI codes; rendering on light backgrounds is controlled by the user's terminal emulator. Postware does not attempt to detect or adapt to light themes. The semantic color choices (bright_green, bright_red, yellow) remain legible on light backgrounds due to their high saturation.

#### Dark Mode

Terminal dark mode is the assumed default (dark background, light text). The token values above are defined for dark-background terminals. No light mode variant is specified for terminal output — this is consistent with developer tool conventions and the target user's environment.

#### Telegram Color System

Telegram renders text with no custom color support in standard messages. Color is expressed entirely through emoji and Unicode symbols serving as semantic anchors. The "color system" for Telegram is therefore an emoji palette:

| Semantic Role | Symbol | Usage |
|---|---|---|
| X / Twitter | 🐦 | Platform section header |
| LinkedIn | 💼 | Platform section header |
| Threads | 🧵 | Platform section header |
| Image suggestion | 📸 | Image suggestion prefix |
| Date / metadata footer | 📅 | Footer prefix |
| Success (bot reply) | ✅ | Confirmation messages |
| Warning (bot reply) | ⚠️ | Non-fatal warnings |
| Error (bot reply) | ❌ | Failure messages |
| Divider | `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━` | Section separator |

### 2.4 Typography System

#### Terminal Typography

Rich renders styled text in the terminal. Postware's typographic hierarchy is achieved through weight, colour, and monospace formatting — not font size.

| Level | Rich Style | Usage | Example |
|---|---|---|---|
| **Heading / Product name** | `bold white` | Panel titles, section headers | `POSTWARE` |
| **Primary label** | `bold cyan` | Field names in status output | `Today's pillar:` |
| **Primary value** | `bold white` | Key data values | `P1 · Build in Public` |
| **Secondary value** | `white` | Standard output text | `Posts delivered to Telegram.` |
| **Muted value** | `bright_black` | Timestamps, metadata | `2025-03-05 08:03:11` |
| **Success message** | `bold bright_green` | Completion confirmations | `✓ Posts delivered to Telegram.` |
| **Error message** | `bold bright_red` | Failure messages | `✗ LLM failed after 3 attempts.` |
| **Warning message** | `bold yellow` | Non-fatal warnings | `⚠ Promo ratio at 22%. Forcing value-driven content.` |
| **Info message** | `bright_blue` | Auto-recovery notices | `ℹ history.json not found. Creating fresh history.` |
| **Code / path** | `` `backtick` `` via Rich `markup` | File paths, command names | `` `config.yaml` `` |

**Monospace rule:** All file paths, command names, JSON keys, and config field names are rendered in Rich's inline code style (`markup` backtick notation). This creates a clear visual distinction between prose and technical identifiers.

#### Telegram Typography

Telegram supports **bold**, _italic_, `inline code`, and `code blocks` via MarkdownV2. Postware's Telegram messages use a minimal subset:

| Style | Markdown | Usage |
|---|---|---|
| Platform header | `*🐦 X (TWITTER)*` (bold) | Section titles |
| Metadata line | `_Pillar: P1 · Build in Public | Format: Progress Update_` (italic) | Post metadata |
| Post body | Plain text | The post itself — no formatting applied, preserving copy-paste fidelity |
| Image suggestion | `📸 _Screenshot of terminal output_` (italic) | Visual suggestion line |
| Footer | `_📅 2025-03-05 · Build in Public · Promo: 14%_` (italic) | Generation metadata |
| Bot error/warning | Plain text with emoji prefix | `❌ Regeneration failed after 3 attempts.` |

**Copy-paste fidelity principle:** Post body text must be rendered as plain text with no Markdown formatting characters. A developer copying the post to paste into X, LinkedIn, or Threads must get clean text with no stray asterisks, underscores, or backticks.

### 2.5 Spacing & Layout System

#### Terminal Spacing

Rich panels and tables manage spacing automatically. Postware's conventions:

| Token | Value | Usage |
|---|---|---|
| `--term-panel-padding` | `1, 2` (Rich pad: top/bottom=1, left/right=2) | All output panels |
| `--term-section-gap` | 1 blank line | Between unrelated output blocks |
| `--term-label-value-gap` | Rich table `pad_edge=False`, column gap = 2 spaces | Status table label-value pairs |
| `--term-divider` | Rich `Rule()` with `--term-border` style | Between major sections |
| `--term-indent` | 2 spaces | Checklist items, sub-items in init output |

**Max terminal width:** Rich output uses `Console(width=80)` as a safe default. This ensures output is legible on narrower terminal windows (common in tiled window manager setups) and does not wrap awkwardly on wider terminals.

#### Telegram Spacing

Telegram messages use `━` (U+2501) repeated 30 times as section dividers. One blank line separates the metadata line from the post body, and one blank line separates the post body from the image suggestion. Footer is separated from the last platform section by a full divider.

### 2.6 Iconography & Symbol System

#### Terminal Status Icons

These icons prefix every output line. They are the primary scanning affordance — a developer reads the icon in <100ms before reading the text.

| Icon | Meaning | Rich Style | Usage Rule |
|---|---|---|---|
| `✓` | Success | `bold bright_green` | Generation complete, delivery confirmed, file created |
| `✗` | Fatal failure | `bold bright_red` | Exit-code-1 events; always followed by an actionable message |
| `⚠` | Warning (non-fatal) | `bold yellow` | Auto-recovered events; system continued |
| `ℹ` | Informational | `bright_blue` | State changes that require no user action |
| `↻` | Retrying | `yellow` | Shown during retry attempts with attempt counter |
| `…` | In progress | `bright_black` | Long-running operations (LLM call, delivery) |

**Rule:** Every terminal output line begins with exactly one status icon, a single space, then the message. No line is emitted without an icon. This enforces consistent scanning behaviour.

#### Telegram Emoji Anchors

Used as structural anchors, not decoration. Each emoji has one fixed semantic role and is never used outside that role.

| Emoji | Fixed Role |
|---|---|
| 🐦 | X section header only |
| 💼 | LinkedIn section header only |
| 🧵 | Threads section header only |
| 📸 | Image suggestion prefix only |
| 📅 | Footer metadata prefix only |
| ✅ | Bot success reply only |
| ⚠️ | Bot warning reply only |
| ❌ | Bot error reply only |

---

## Phase 3: Component Specifications

### Component 1 — Generation Success Panel (Terminal)

**Trigger:** Successful end-to-end pipeline run.

```
┌─────────────────────────────────────────────────────────────┐
│  POSTWARE                                                   │
│─────────────────────────────────────────────────────────────│
│  ✓ Posts generated and delivered to Telegram                │
│                                                             │
│  Date           Monday, 2025-03-05                          │
│  Pillar         P1 · Build in Public                        │
│  Promo ratio    14%  (target: ≤20%)                         │
│  LLM            claude-3-5-sonnet (anthropic)               │
│  Duration       12.4s                                       │
└─────────────────────────────────────────────────────────────┘
```

| State | Visual Treatment |
|---|---|
| **Default (success)** | Green `✓` prefix on confirmation line; bold white panel title; cyan labels; white values |
| **With promo override** | Adds `⚠ Promo ratio forced to value-driven` line in yellow before the panel |
| **With retry** | Adds `↻ LLM retry 2/3…` line in yellow before the panel (retry resolved successfully) |

**Rich tokens used:** `bold white` (title), `cyan` (labels), `white` (values), `bold bright_green` (success line), `bright_black` (duration/metadata), `Panel` with `--term-panel-padding`.

---

### Component 2 — Error Output (Terminal)

**Trigger:** Any exit-code-1 event.

```
✗ LLM failed after 3 attempts. See errors.log for details.

  Provider:   anthropic
  Model:      claude-3-5-sonnet-20241022
  Last error: Connection timeout after 30s
  Log file:   ./errors.log
```

| State | Visual Treatment |
|---|---|
| **Config error** | `✗` prefix; lists each missing/invalid field on its own indented line |
| **LLM failure** | `✗` prefix; shows provider, model, last error type; references `errors.log` |
| **Telegram failure** | `✗` prefix; distinguishes credential errors (no retry) from network errors (retry exhausted) |
| **Permission error** | `✗` prefix; shows affected path; suggests `chmod` or directory change |

**Design rule:** Error messages must always answer three questions: (1) what failed, (2) why it failed (or where to find out), (3) what the user can do next. No error message ends without an actionable hint.

---

### Component 3 — Status Panel (Terminal)

**Trigger:** `python -m postware status`

```
┌─────────────────────────────────────────────────────────────┐
│  POSTWARE STATUS                                            │
│─────────────────────────────────────────────────────────────│
│  Today's pillar      P1 · Build in Public                   │
│  Promo ratio (14d)   14%  ████░░░░░░  (target: 20%)         │
│  Total posts         87                                     │
│  Last generated      2025-03-04 08:03:11                    │
│                                                             │
│  Pillar distribution (30d)                                  │
│  ─────────────────────────────────────────────────────────  │
│  P1 Build in Public   ██████████  33%  (target 30%)  ↑      │
│  P2 Teaching          ████████    27%  (target 25%)  ↑      │
│  P3 Opinions          █████       17%  (target 15%)  ↑      │
│  P4 Data & Results    █████       13%  (target 15%)  ↓      │
│  P5 Community         ████        10%  (target 15%)  ↓      │
└─────────────────────────────────────────────────────────────┘
```

| Element | Specification |
|---|---|
| Progress bar | Rich `Progress` bar, width 10 chars; filled chars = `█`, empty = `░` |
| Over-target pillar | `↑` suffix in `bright_green`; value shown in `bold white` |
| Under-target pillar | `↓` suffix in `yellow`; value shown in `yellow` |
| Within-target pillar | No arrow; value shown in `white` |
| No history | Renders panel with `ℹ No generation history found. Run \`postware generate\` to begin.` |
| Last generated > 24h ago | `Last generated` value rendered in `yellow` as a soft reminder |

---

### Component 4 — Init Checklist (Terminal)

**Trigger:** `python -m postware init`

```
✓ config.yaml created
✓ .env created from .env.example
✓ history.json created
✓ File permissions set (0o600)
✓ Dependency audit passed — no known vulnerabilities

  Next steps:
  ─────────────────────────────────────────────────────────
  [ ] 1. Open .env — add your LLM API key
  [ ] 2. Open .env — add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
  [ ] 3. Open config.yaml — fill in project name and description
  [ ] 4. Create a Telegram bot via @BotFather if you haven't
  [ ] 5. Run `python -m postware generate` to test your setup
```

| State | Visual Treatment |
|---|---|
| **File already exists (skipped)** | `ℹ config.yaml already exists — skipped` in blue instead of green `✓` |
| **File already exists (overwritten)** | `✓ config.yaml overwritten` in green |
| **Permission set failed (Unix)** | `⚠ Could not set file permissions on config.yaml` in yellow; checklist continues |
| **Windows — pywin32 method** | `✓ Windows ACLs applied (pywin32)` |
| **Windows — icacls fallback** | `✓ Windows ACLs applied (icacls)` |
| **Windows — no method available** | `⚠ File permissions could not be set on Windows — protect .env manually` |
| **pip-audit not installed** | `⚠ pip-audit not installed — dependency audit skipped` in yellow |
| **pip-audit finds HIGH/CRITICAL CVE** | `⚠ 1 HIGH vulnerability found in litellm` + Rich table of affected packages |
| **All steps complete** | Checklist items rendered as `[ ] N.` — plain text, not interactive (terminal only) |

---

### Component 5 — Retry Progress (Terminal)

**Trigger:** LLM or Telegram API call fails; system is retrying.

```
↻ LLM call failed (attempt 1/3). Retrying in 1s…
↻ LLM call failed (attempt 2/3). Retrying in 2s…
✗ LLM failed after 3 attempts. See errors.log for details.
```

```
↻ LLM call failed (attempt 1/3). Retrying in 1s…
✓ Posts generated and delivered to Telegram.   ← success on retry
```

| State | Visual Treatment |
|---|---|
| **Retrying** | `↻` in `yellow`; attempt counter `(N/3)` in `bright_black`; delay value in `bright_black` |
| **Retry succeeded** | Normal success panel follows immediately after retry lines |
| **All retries exhausted** | `✗` error line follows retry lines; no blank line between last retry and error |

---

### Component 6 — Telegram Daily Bundle Message

**Trigger:** Successful generation run (CLI, cron, or `/generate` bot command).

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*🐦 X \(TWITTER\)*
_Pillar: P1 · Build in Public | Format: Progress Update_

[Post text — plain, ≤280 chars, no Markdown formatting]

📸 _Screenshot of git commit history showing feature branch_
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*💼 LINKEDIN*
_Pillar: P1 · Build in Public | Format: Behind\-the\-Scenes_

[Post text — plain, ≤1500 chars]

📸 _Terminal output showing test suite passing_
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*🧵 THREADS*
_Pillar: P1 · Build in Public | Format: Quick Update_

[Post text — plain, ≤500 chars]

📸 _Side\-by\-side before\/after code screenshot_
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_📅 2025\-03\-05 · Build in Public · Promo: 14%_
```

| State | Visual Treatment |
|---|---|
| **Standard delivery** | As above — single message |
| **Message split (>4,096 chars)** | Three separate messages, each containing one platform section + its dividers; footer appended to the Threads message only |
| **Promotional post** | Footer reads `Promo: 14% 🔔` — bell emoji added as a soft visual flag that this run contains a promotional post |
| **Promo ratio forced** | Footer reads `Promo: 22% → forced value-driven` |

**Telegram MarkdownV2 escaping rule:** All special characters in the structural template (`(`, `)`, `-`, `.`, `!`, `>`, `#`, `+`, `=`, `|`, `{`, `}`) must be escaped with a preceding `\`. Post body text must be sent as plain text (no Markdown parse mode applied to the post body segment) to preserve copy-paste fidelity. The structural wrapper uses MarkdownV2; post body text does not.

---

### Component 7 — Telegram /status Reply

**Trigger:** User sends `/status` in Telegram chat.

```
*📊 Postware Status*

*Today's pillar:* P1 · Build in Public
*Promo ratio \(14d\):* 14% ✅ \(target: ≤20%\)
*Total posts:* 87
*Last generated:* 2025\-03\-04 08:03:11

*Pillar distribution \(30d\):*
P1 Build in Public ░░░░░░ 33% ↑
P2 Teaching ░░░░░ 27% ↑
P3 Data & Results ░░░ 13% ↓
P4 Opinions ░░░ 17% ↑
P5 Community ░░ 10% ↓
```

| State | Visual Treatment |
|---|---|
| **Promo ratio ≤20%** | `14% ✅` — green check communicates on-target |
| **Promo ratio >20%** | `22% ⚠️` — warning emoji communicates over-target |
| **No history** | `ℹ No generation history yet\. Run /generate to begin\.` |
| **Not generated today** | `Last generated:` value shows date + `(not yet today)` in parentheses |

---

### Component 8 — Telegram /regenerate Inline Keyboard

**Trigger:** User sends `/regenerate` after today's posts have been generated.

```
Which platform would you like to regenerate?

[ X (Twitter) ]  [ LinkedIn ]  [ Threads ]
```

| State | Visual Treatment |
|---|---|
| **Default (picker shown)** | Three inline buttons in a single row. Button labels: `🐦 X`, `💼 LinkedIn`, `🧵 Threads` |
| **Button tapped** | Keyboard removed; "⏳ Regenerating your LinkedIn post…" confirmation message replaces the prompt |
| **No generation today** | Keyboard never shown; bot replies: `❌ No posts generated today yet\. Use /generate first\.` |
| **LLM failure during regeneration** | `❌ Regeneration failed after 3 attempts\. Please try again later\.` |
| **Success** | Regenerated post delivered as a single-platform message using the same format as a bundle section (minus other platform sections) |

**Inline keyboard design rule:** All three buttons appear in a single row. No vertical stacking — the choice is a simple three-way selection, not a list. Button emoji matches the platform emoji used in the bundle message for visual consistency.

---

### Component 9 — Telegram Regenerated Single-Post Message

**Trigger:** User selects a platform in the /regenerate inline keyboard and generation succeeds.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*💼 LINKEDIN \(REGENERATED\)*
_Pillar: P1 · Build in Public | Format: Thought Leadership_

[Regenerated post text — plain]

📸 _Diagram showing architecture decision flow_
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_📅 2025\-03\-05 · Regenerated_
```

| Difference from Bundle | Specification |
|---|---|
| Header suffix | Platform header reads `(REGENERATED)` to distinguish from original bundle |
| Footer | Reads `📅 [date] · Regenerated` — no pillar or promo ratio repeated (visible in /status) |
| Single section | No other platform sections; no section dividers before or after |

---

### Component 10 — Bot Command Error / Warning Reply

**Trigger:** Any bot command results in a non-fatal or fatal error.

| Error Type | Message Format |
|---|---|
| Not generated today | `❌ No posts generated today yet\. Use /generate first\.` |
| LLM failure | `❌ Generation failed after 3 attempts\. Please try again later\.` |
| Config invalid | `❌ Configuration error\. Please check config\.yaml and restart the bot\.` |
| History write failed | `✅ Post delivered\. ⚠️ History not updated \(file write error\)\.` |

**Design rule:** Bot error messages are never raw exception strings. They are human-readable, action-oriented, and end with a suggested next step wherever possible. Technical details go to `errors.log`, not to the Telegram chat.

---

### Component 11 — Terminal Inline Progress Indicator

**Trigger:** Long-running operations (LLM call, Telegram send).

```
… Calling anthropic/claude-3-5-sonnet…
```

```
… Delivering to Telegram…
```

| State | Visual Treatment |
|---|---|
| **In progress** | `…` prefix in `bright_black`; single-line, no spinner animation (spinner is optional for interactive sessions only; disabled in cron/daemon mode to avoid polluting logs) |
| **Cron / daemon mode** | Progress lines suppressed entirely; only the final success or error line is emitted |
| **Interactive mode** | Rich `Spinner` component may be used for the LLM call duration; reverts to single-line completion message on success |

**Cron-safe output rule:** When Postware detects it is running non-interactively (stdout is not a TTY, detectable via `sys.stdout.isatty()`), all progress and spinner output is suppressed. Only the final outcome line is emitted. This prevents log file pollution in cron and systemd journal contexts.

---

### Component 12 — `config.yaml` Starter File Design

**Trigger:** `python -m postware init`

The generated `config.yaml` is itself a designed artifact. Its structure, comments, and placeholder values must guide the user to a correct first configuration without needing to read external documentation.

**Design principles for the starter file:**
- Every required field has a comment explaining its purpose and an example value
- Optional fields are present but commented out with a `# Optional:` prefix
- Placeholder values use ALL_CAPS convention (e.g., `YOUR_PROJECT_NAME`) to be visually distinct from real values
- Sections are separated by a blank line and a comment header

```yaml
# ─────────────────────────────────────────
# POSTWARE CONFIGURATION
# ─────────────────────────────────────────
# Fill in all required fields before running `postware generate`.
# Optional fields are commented out — uncomment and fill as needed.

project:
  name: "YOUR_PROJECT_NAME"          # Required. Used in all generated posts.
  description: "YOUR_PROJECT_DESCRIPTION"  # Required. Gives the LLM context.
  # url: "https://yourproject.com"   # Optional. Included in promotional posts.

author:
  name: "YOUR_NAME"                  # Required. Attributed in post content.
  # bio: "YOUR_ONE_LINE_BIO"         # Optional. Shapes post tone and voice.

# Recent milestones — used as LLM context for relevant post topics.
# milestones:
#   - "Launched public beta"
#   - "Reached 100 GitHub stars"

# Recent changelog entries — used to generate Data & Results posts.
# changelog:
#   - "Added CSV export feature"
#   - "Fixed authentication bug"

llm:
  provider: "anthropic"              # Required. See supported providers in README.
  model: "claude-3-5-sonnet-20241022" # Required.
  # base_url: "http://localhost:11434" # Required only for ollama/lmstudio/custom.
  # temperature: 0.8                 # Optional. Default: 0.8
  # max_tokens: 2000                 # Optional. Default: 2000

schedule:
  time: "08:00"                      # Required for daemon mode. Format: HH:MM.
```

---

### Component 13 — `.env.example` File Design

**Trigger:** Shipped with the repository; copied to `.env` by `init`.

```bash
# ─────────────────────────────────────────
# POSTWARE ENVIRONMENT VARIABLES
# ─────────────────────────────────────────
# Copy this file to .env and fill in your values.
# NEVER commit .env to version control.

# Telegram Bot (required)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# LLM Providers — add the key for your configured provider only
ANTHROPIC_API_KEY=your_anthropic_key_here
# OPENAI_API_KEY=your_openai_key_here
# GROQ_API_KEY=your_groq_key_here
# GOOGLE_API_KEY=your_google_key_here
# DEEPSEEK_API_KEY=your_deepseek_key_here
# QWEN_API_KEY=your_qwen_key_here
# MINIMAX_API_KEY=your_minimax_key_here
# KIMI_API_KEY=your_kimi_key_here
# ZAI_API_KEY=your_zai_key_here
# (No key needed for ollama/lmstudio/custom — set base_url in config.yaml)
```

---

### Component 14 — Accessibility & Platform Compatibility Notes

**Terminal accessibility:**

| Concern | Specification |
|---|---|
| Screen readers | Rich outputs plain text when `TERM=dumb` or `NO_COLOR=1` env vars are set; all emoji degrade to their Unicode text descriptions in screen-reader-friendly terminals |
| Colour blindness | Status icons (`✓`, `✗`, `⚠`, `ℹ`) carry semantic meaning independent of colour; the system is fully functional in `NO_COLOR` mode |
| `NO_COLOR` support | Postware respects the `NO_COLOR` environment variable standard; when set, all Rich colour output is suppressed and pure text output is used |
| Windows terminal | Rich supports Windows Terminal and PowerShell 7+ natively; legacy `cmd.exe` may not render box-drawing characters — `init` output degrades to plain ASCII borders on detection |

**Telegram accessibility:**

| Concern | Specification |
|---|---|
| Screen readers (mobile) | Telegram's mobile apps support VoiceOver (iOS) and TalkBack (Android) natively; plain text post bodies and MarkdownV2 bold/italic are fully accessible |
| Message length | No post body exceeds platform character limits; no Telegram message exceeds 4,096 characters (auto-split handles this) |
| Inline keyboard (mobile) | Three buttons in one row; minimum tap target enforced by Telegram's own UI (44pt iOS / 48dp Android) |

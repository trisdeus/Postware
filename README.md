# Postware

> Auto-generate platform-optimized social media posts and deliver them to your Telegram — without leaving the terminal.

Postware is a Python CLI tool built for solo developers and indie hackers who are **building in public**. Each run produces three ready-to-copy posts — one each for **X (Twitter)**, **LinkedIn**, and **Threads** — bundled and sent to your Telegram chat. A five-pillar weekly content strategy, an 80/20 value-to-promotion ratio, and local topic deduplication are enforced automatically; you just paste and ship.

- **No social media API keys required** — Postware sends the bundle to Telegram; you post manually.
- **No cloud costs beyond LLM credits** — runs entirely on your local machine.
- **BYOK (Bring Your Own Key)** — plug in any provider: Anthropic, OpenAI, Groq, Google, DeepSeek, Qwen, Ollama, LM Studio, and more via [LiteLLM](https://docs.litellm.ai/).

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Configuration](#configuration)
  - [config.yaml](#configyaml)
  - [.env](#env)
- [Content Strategy](#content-strategy)
- [Project Structure](#project-structure)
- [Development](#development)
- [Contributing](#contributing)

---

## Requirements

| Requirement | Version |
|-------|-------|
| Python | ≥ 3.10 |
| Operating System | macOS, Linux, Windows |

A **Telegram bot token** and **chat ID** are required for delivery. See [Telegram Bot Setup](#env) below.

---

## Installation

### From PyPI (recommended)

```bash
pip install postware
```

### From source

```bash
git clone https://github.com/postware/postware.git
cd postware
pip install -e .
```

### Development install (includes testing tools)

```bash
pip install -e ".[dev]"
```

On **Windows**, optionally install enhanced file permission support:

```bash
pip install -e ".[windows]"
```

---

## Quick Start

**1. Scaffold your configuration files:**

```bash
python -m postware init
```

This creates `config.yaml`, `.env`, and `history.json` in the current directory, then prints a numbered setup checklist.

**2. Fill in your credentials** (open `.env` in any editor):

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

**3. Fill in your project details** (open `config.yaml` in any editor):

```yaml
project:
  name: "My SaaS"
  description: "A tool that helps developers ship faster."

author:
  bio: "Indie hacker building in public. Ex-big-tech."
```

**4. Generate your first post bundle:**

```bash
python -m postware generate
```

A formatted bundle is delivered to your Telegram chat within 60 seconds. ✓

---

## CLI Usage

Postware exposes four subcommands through `python -m postware` (or the `postware` script after installation):

```text
postware <command> [options]
```

### `generate`

Run the full pipeline once: resolve today's content pillar, build prompts, call the LLM, and deliver the bundle to Telegram.

```bash
python -m postware generate
```

Output includes: date, pillar used, promotional ratio, LLM provider, and duration.  
Exit code `0` on success; `1` on any failure (config error, LLM failure, delivery failure).

### `status`

Display a terminal panel showing content statistics from local history — no LLM calls, no Telegram calls.

```bash
python -m postware status
```

Shows: today's pillar, 14-day promotional ratio, total posts generated, last generation timestamp.  
Completes in ≤ 2 seconds.

### `start`

Launch Postware as a scheduling daemon using APScheduler. Posts are generated automatically at the time configured in `config.yaml` under `schedule.time`.

```bash
python -m postware start
```

Register SIGINT/SIGTERM for graceful shutdown. For persistent operation, run under a process manager (systemd, supervisor, or macOS launchd). See [Deployment](#deployment).

### `init`

Scaffold configuration files and print the setup checklist.

```bash
python -m postware init
```

- Creates `config.yaml` (prompts for overwrite confirmation if it already exists)
- Creates `.env` and `history.json` if absent; skips both if already present
- Idempotent — safe to re-run

---

## Configuration

Postware reads configuration from two files in the project root:

| File | Purpose | Committed? |
|-------|-------|-------|
| `config.yaml` | Project details, LLM settings, schedule | ❌ No — user-maintained |
| `.env` | API keys and Telegram credentials | ❌ No — secrets |
| `.env.example` | Placeholder template for credentials | ✅ Yes |

Both files are excluded from version control via `.gitignore`.  
Use `python -m postware init` to create them with placeholder values.

### config.yaml

```yaml
project:
  name: "Your Project Name"
  description: "A short description of what you're building."

author:
  bio: "Your one-line author bio."

milestones:
  - "Launched beta in January"
  - "Hit 100 users in February"

changelog:
  - "Added dark mode"
  - "Fixed login bug"

llm:
  provider: "anthropic"          # See supported providers below
  model: "claude-3-5-haiku-20241022"
  # base_url: "http://localhost:11434"  # Required for ollama / lmstudio / custom

schedule:
  time: "08:00"                  # HH:MM — used by the `start` daemon command
```

**Supported LLM providers** (via LiteLLM): `anthropic`, `openai`, `groq`, `google`, `deepseek`, `qwen`, `minimax`, `kimi`, `z.ai`, `ollama`, `lmstudio`, `custom`.

For local models (Ollama, LM Studio), set `llm.base_url` to your server's endpoint.

### .env

```env
# Telegram delivery credentials
TELEGRAM_BOT_TOKEN=your_bot_token_here   # From @BotFather
TELEGRAM_CHAT_ID=your_chat_id_here       # Your personal chat ID

# LLM provider API key — add the key for the provider you configured in config.yaml
ANTHROPIC_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
# GROQ_API_KEY=your_key_here
# GOOGLE_API_KEY=your_key_here
```

**Getting a Telegram bot token and chat ID:**

1. Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` → copy the token.
2. Message [@userinfobot](https://t.me/userinfobot) → copy your numeric chat ID.
3. Start a conversation with your new bot (send it any message) so it can send to you.

---

## Content Strategy

Postware enforces a structured weekly schedule. Each day maps to one of five content pillars:

| Day | Pillar | Focus |
|-------|-------|-------|
| Monday | Build in Public | Progress, decisions, what you shipped |
| Tuesday | Teaching | Tutorials, tips, how-tos |
| Wednesday | Opinions | Hot takes, contrarian views |
| Thursday | Data & Results | Metrics, growth, screenshots |
| Friday | Community | Shoutouts, questions, discussions |
| Saturday | Build in Public | Weekend progress update |
| Sunday | Teaching | Sunday learning content |

**80/20 rule:** If your 14-day history shows more than 20% promotional posts, the next generation is automatically forced to be value-driven. An info message is logged when this override activates.

**Topic deduplication:** The last 10 post topics from `history.json` are injected as context into the LLM prompt to avoid repetition.

---

## Project Structure

```
postware/
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
├── AGENTS.md                   # Agent roles, coding standards, architecture
├── src/
│   └── postware/
│       ├── __init__.py
│       ├── main.py             # CLI entrypoint, composition root, logger setup
│       ├── config.py           # config.yaml + .env loader, Pydantic validation
│       ├── models.py           # All Pydantic data models (dependency floor)
│       ├── generator.py        # Content generation engine, LiteLLM calls
│       ├── prompts.py          # Prompt builder
│       ├── history.py          # history.json read/write/query/prune
│       ├── telegram_bot.py     # Telegram delivery and bot command handlers
│       ├── scheduler.py        # APScheduler daemon
│       └── platform_utils.py   # File permission hardening
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
└── scripts/
    └── audit_deps.py           # Dependency vulnerability scanner
```

Runtime files (`config.yaml`, `history.json`, `.env`, `errors.log`) live in the project root and are excluded from version control.

---

## Development

### Setup

```bash
git clone https://github.com/postware/postware.git
cd postware
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -e ".[dev]"
```

### Running tests

```bash
pytest
```

All tests mock LiteLLM and Telegram API calls — no real credentials needed to run the test suite.

### Code quality

```bash
# Format
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy --strict src/

# Dependency audit
python scripts/audit_deps.py
```

All four commands must pass with zero warnings before submitting changes.

---

## Deployment

### One-shot via cron

```cron
0 8 * * * cd /path/to/postware && python -m postware generate
```

In cron mode, progress indicators are suppressed automatically; only the final outcome line is emitted.

### Daemon via systemd

```ini
[Unit]
Description=Postware social media scheduler
After=network.target

[Service]
WorkingDirectory=/path/to/postware
ExecStart=/path/to/.venv/bin/python -m postware start
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable with `systemctl enable --now postware`.

---

## Contributing

See [AGENTS.md](AGENTS.md) for the full development guide, including agent roles, module dependency rules, coding standards, and the task format used for all contributions.

---

## License

MIT — see `pyproject.toml` for details.

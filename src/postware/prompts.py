"""
LLM prompt construction and output format contract.

This module handles all prompt construction for the LLM content generation.
It defines the system prompt with JSON schema contract and user prompts with
project context. This module has ZERO imports from other src/postware modules
— it imports only from models.py as the dependency floor.

Functions:
    build_system_prompt: Returns the system prompt defining LLM role and output schema
    build_user_prompt: Constructs user prompt with config, pillar, and dedup context
    sanitize_for_prompt: Sanitizes user input to prevent prompt injection

No network calls and no file I/O in this module.
"""

import re
from postware.models import AppConfig, Pillar, PlatformPost, PLATFORM_CHAR_LIMITS


# =============================================================================
# CONTENT PILLAR DEFINITIONS
# =============================================================================

# Pillar definitions with their focus areas for prompt construction.
# These match the PRD FR-003 content pillar specifications.
PILLAR_DEFINITIONS: dict[Pillar, str] = {
    Pillar.P1: (
        "Build in Public - Share progress, wins, struggles, and learnings. "
        "Focus on authentic updates about what you're building, failures "
        "and how you're overcoming them, and milestones achieved."
    ),
    Pillar.P2: (
        "Teaching - Share knowledge, tutorials, and how-tos. "
        "Focus on explaining concepts, sharing code snippets, "
        "solving problems, and educating your audience."
    ),
    Pillar.P3: (
        "Opinions - Hot takes, industry commentary, and contrarian views. "
        "Share your perspective on trends, tools, practices, "
        "and challenge conventional wisdom when appropriate."
    ),
    Pillar.P4: (
        "Data & Results - Metrics, A/B tests, and performance data. "
        "Share experiments, results, what worked and what didn't, "
        "and real numbers that validate your claims."
    ),
    Pillar.P5: (
        "Community - Questions, polls, and engagement prompts. "
        "Ask your audience for input, run polls, celebrate others, "
        "and build engagement through interaction."
    ),
}


# =============================================================================
# SYSTEM PROMPT
# =============================================================================


def build_system_prompt() -> str:
    """
    Build the system prompt that defines the LLM's role and output contract.

    The system prompt instructs the LLM to act as a social media content
    generator with specific platform constraints and output format requirements.

    Returns:
        The complete system prompt string containing role definition,
        platform rules, and JSON output schema.

    Example:
        >>> prompt = build_system_prompt()
        >>> "social media content generator" in prompt
        True
    """
    x_limit = PLATFORM_CHAR_LIMITS["x"]
    linkedin_limit = PLATFORM_CHAR_LIMITS["linkedin"]
    threads_limit = PLATFORM_CHAR_LIMITS["threads"]

    return f"""You are a social media content generator for solo developers and indie hackers.

Your task is to generate three versions of a social media post—one for each platform:
- X (Twitter): ≤{x_limit} characters, casual tone,可以使用emoji
- LinkedIn: ≤{linkedin_limit} characters, professional tone, business-focused
- Threads: ≤{threads_limit} characters, conversational tone, engaging

## Output Format

You MUST output ONLY valid JSON in the exact format below. No additional text.

```json
{{
  "platform_posts": {{
    "x": {{
      "text": "...",
      "format_type": "text|thread|poll|image",
      "image_suggestion": "optional description of suggested image"
    }},
    "linkedin": {{
      "text": "...",
      "format_type": "text|article|poll|image",
      "image_suggestion": "optional description of suggested image"
    }},
    "threads": {{
      "text": "...",
      "format_type": "text|thread|poll|image",
      "image_suggestion": "optional description of suggested image"
    }}
  }},
  "is_promotional": true|false
}}
```

## Platform-Specific Guidelines

### X (Twitter)
- Keep it short and punchy
- Use casual language and may include emojis
- Can use thread format for longer content
- Ask a question or end with engagement hook

### LinkedIn
- Professional tone, avoid slang
- Structure with clear value proposition
- Can be longer but stay under limit
- Professional image suggestions preferred

### Threads
- Conversational and friendly
- Can be casual but professional
- Use line breaks for readability
- Encouraging engagement

## Content Rules

1. Value-first: Focus on providing value to your audience
2. Authentic: Sound genuine, not salesy
3. Platform-appropriate: Match tone to each platform
4. Character limits: Stay within each platform's limits
5. One clear message: Each post should have one main point

Now generate the content based on the user prompt."""


# =============================================================================
# USER PROMPT
# =============================================================================


def build_user_prompt(
    config: AppConfig,
    pillar: Pillar,
    force_value_driven: bool,
    dedup_context: list[str],
) -> str:
    """
    Build the user prompt with project context, pillar info, and constraints.

    Constructs a prompt that provides the LLM with all necessary context
    to generate relevant content, including project details, current pillar,
    promotional constraints, and topic deduplication context.

    Args:
        config: Application configuration containing project details.
        pillar: The content pillar for this generation.
        force_value_driven: If True, must generate value-driven content (80/20 enforcement).
        dedup_context: List of recent topic strings to avoid duplication.

    Returns:
        The complete user prompt string.

    Example:
        >>> config = AppConfig(
        ...     project=ProjectConfig(name="My App", description="A cool tool"),
        ...     author=AuthorConfig(bio="Developer"),
        ...     milestones=["Launched v1"],
        ...     changelog=["Added feature"],
        ...     llm=LLMConfig(provider="anthropic", model="claude-3"),
        ...     schedule=ScheduleConfig(time="08:00")
        ... )
        >>> prompt = build_user_prompt(config, Pillar.P1, False, [])
        >>> "My App" in prompt
        True
    """
    # Sanitize all config values before embedding in prompt
    project_name = sanitize_for_prompt(config.project.name)
    project_description = sanitize_for_prompt(config.project.description)
    author_bio = sanitize_for_prompt(config.author.bio)

    # Sanitize milestones and changelog
    milestones = [sanitize_for_prompt(m) for m in config.milestones]
    changelog = [sanitize_for_prompt(c) for c in config.changelog]

    # Get pillar definition
    pillar_definition = PILLAR_DEFINITIONS[pillar]
    pillar_name = pillar.value

    # Build prompt sections
    prompt_parts = []

    # Project Context
    prompt_parts.append("## Project Context")
    prompt_parts.append(f"Project Name: {project_name}")
    prompt_parts.append(f"Description: {project_description}")
    prompt_parts.append(f"Author: {author_bio}")

    # Milestones
    if milestones:
        prompt_parts.append("\n## Recent Milestones")
        for m in milestones:
            prompt_parts.append(f"- {m}")

    # Changelog
    if changelog:
        prompt_parts.append("\n## Recent Changes")
        for c in changelog:
            prompt_parts.append(f"- {c}")

    # Content Pillar
    prompt_parts.append(f"\n## Content Pillar: {pillar_name}")
    prompt_parts.append(pillar_definition)

    # Promotional constraint
    if force_value_driven:
        prompt_parts.append(
            "\n## Content Constraint"
            "\nThis post MUST be value-driven content (educational, "
            "informative, or helpful). Do NOT create promotional content. "
            "Focus on teaching, sharing insights, or providing value."
        )

    # Deduplication context
    if dedup_context:
        prompt_parts.append("\n## Recent Topics to Avoid")
        prompt_parts.append("The following topics have been covered recently. ")
        prompt_parts.append("Do NOT repeat these topics or create similar content:")
        for topic in dedup_context:
            prompt_parts.append(f"- {topic}")

    # Final instruction
    prompt_parts.append("\n## Task")
    prompt_parts.append(
        f"Generate three versions of a social media post for the "
        f"'{pillar_name}' content pillar. Follow the platform guidelines "
        f"and output ONLY the JSON format specified in the system prompt."
    )

    return "\n".join(prompt_parts)


# =============================================================================
# PROMPT SANITIZATION
# =============================================================================

# Maximum length for any single config field in prompts.
# This prevents excessively long inputs from affecting LLM behavior.
MAX_FIELD_LENGTH: int = 500

# Injection patterns that could manipulate LLM behavior.
# These are replaced with [removed] to prevent prompt injection.
INJECTION_PATTERNS: list[re.Pattern[str]] = [
    # JSON/Code injection attempts
    re.compile(r'```[\s\S]*?```', re.IGNORECASE),  # Code blocks
    re.compile(r'\{[\s\S]*\}', re.IGNORECASE),      # JSON objects
    # System prompt bypass attempts
    re.compile(r'ignore\s+(previous|above|system)', re.IGNORECASE),
    re.compile(r'directive', re.IGNORECASE),
    re.compile(r'system\s*:\s*', re.IGNORECASE),
    # Role manipulation
    re.compile(r'you\s+are\s+now', re.IGNORECASE),
    re.compile(r'pretend\s+to\s+be', re.IGNORECASE),
    re.compile(r'roleplay', re.IGNORECASE),
]


def sanitize_for_prompt(value: str) -> str:
    """
    Sanitize a string value to prevent prompt injection.

    Applies four sanitization rules:
    1. Strip leading/trailing whitespace
    2. Truncate to MAX_FIELD_LENGTH characters
    3. Replace injection patterns with [removed]
    4. Escape template delimiters ({{ }}) to prevent template injection

    Args:
        value: The raw string value from config to sanitize.

    Returns:
        The sanitized string safe for embedding in prompts.

    Example:
        >>> sanitize_for_prompt("  hello world  ")
        'hello world'
        >>> sanitize_for_prompt("a" * 1000)[:10]
        'aaaaaaaaaa'
        >>> "[ignore previous instructions]" in sanitize_for_prompt("test [ignore previous instructions] test")
        False
    """
    if not value:
        return ""

    # Step 1: Strip whitespace
    sanitized = value.strip()

    # Step 2: Replace injection patterns with [removed]
    for pattern in INJECTION_PATTERNS:
        sanitized = pattern.sub("[removed]", sanitized)

    # Step 3: Escape template delimiters
    sanitized = sanitized.replace("{{", "\\{\\{").replace("}}", "\\}\\}")

    # Step 4: Truncate to max length
    if len(sanitized) > MAX_FIELD_LENGTH:
        sanitized = sanitized[:MAX_FIELD_LENGTH] + "..."

    return sanitized


# =============================================================================
# LLM OUTPUT SCHEMA
# =============================================================================

# JSON schema for validating LLM output.
# This is used by the generator to parse and validate LLM responses.
LLM_OUTPUT_SCHEMA: str = """{
  "platform_posts": {
    "x": {
      "text": "string (max 280 characters)",
      "format_type": "string (text|thread|poll|image)",
      "image_suggestion": "string | null"
    },
    "linkedin": {
      "text": "string (max 1500 characters)",
      "format_type": "string (text|article|poll|image)",
      "image_suggestion": "string | null"
    },
    "threads": {
      "text": "string (max 500 characters)",
      "format_type": "string (text|thread|poll|image)",
      "image_suggestion": "string | null"
    }
  },
  "is_promotional": "boolean"
}"""


def validate_post_length(post: PlatformPost, platform: str) -> bool:
    """
    Validate that a platform post is within character limits.

    Args:
        post: The PlatformPost to validate.
        platform: The platform identifier ('x', 'linkedin', or 'threads').

    Returns:
        True if the post text is within the platform's character limit.

    Example:
        >>> post = PlatformPost(text="Hello world!", format_type="text")
        >>> validate_post_length(post, "x")
        True
    """
    limit = PLATFORM_CHAR_LIMITS.get(platform)
    if limit is None:
        return False
    return len(post.text) <= limit

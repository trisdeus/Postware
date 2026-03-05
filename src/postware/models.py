"""
Pydantic data models for Postware.

This module is the dependency floor - it has ZERO internal imports from other
src/postware/ modules. All data shapes used throughout the application are
defined here.

Models defined:
    - Pillar: Content pillar enum (P1-P5)
    - DayOfWeek: Day of week enum (Mon-Sun)
    - PlatformPost: Single platform post with text, format, and image suggestion
    - PlatformPosts: Container for posts across X, LinkedIn, and Threads
    - GeneratedBundle: Complete generation output with metadata
    - GenerationRecord: Storage-equivalent record for history.json
    - ProjectConfig: Project name and description
    - AuthorConfig: Author biography
    - LLMConfig: LLM provider, model, and optional base URL
    - ScheduleConfig: Schedule time in HH:MM format
    - AppConfig: Complete application configuration
    - EnvConfig: Environment variables (credentials)
    - PostwareError: Base exception class
    - ConfigError: Configuration validation errors
    - HistoryError: Base for history-related errors
    - HistoryWriteError: History.json write failures
    - GenerationError: Base for generation-related errors
    - LLMCallError: LLM API call errors
    - LLMOutputError: LLM output parsing/validation errors
    - GenerationFailedError: Retry exhaustion errors
    - DeliveryError: Base for delivery-related errors
    - DeliveryCredentialError: Invalid Telegram credentials (401/400)
    - DeliveryFailedError: Telegram delivery failures

Constants defined:
    - PILLAR_SCHEDULE: Maps DayOfWeek → Pillar per PRD FR-003
    - PLATFORM_CHAR_LIMITS: Character limits per platform
    - MAX_HISTORY_RECORDS: Maximum records retained in history.json
    - SUPPORTED_PROVIDERS: Valid LLM provider names
"""

import re
from enum import Enum

from pydantic import BaseModel, field_validator


# =============================================================================
# ENUMS
# =============================================================================


class Pillar(str, Enum):
    """
    Content pillar enum representing the five content strategy pillars.

    Each pillar represents a distinct content type for the weekly posting
    strategy. The pillars are weighted and scheduled across the week to
    ensure content variety and engagement.

    Attributes:
        P1: Build in Public - Sharing progress, wins, and setbacks
        P2: Teaching - Educational content and how-tos
        P3: Opinions - Hot takes, debates, and thought leadership
        P4: Data & Results - Metrics, experiments, and case studies
        P5: Community - Engagement, questions, and shoutouts
    """

    P1 = "Build in Public"
    P2 = "Teaching"
    P3 = "Opinions"
    P4 = "Data & Results"
    P5 = "Community"


class DayOfWeek(str, Enum):
    """
    Day of week enum for pillar scheduling.

    Used to map days to content pillars in the weekly schedule and to
    track which pillar should be used for a given generation request.

    Attributes:
        MON: Monday
        TUE: Tuesday
        WED: Wednesday
        THU: Thursday
        FRI: Friday
        SAT: Saturday
        SUN: Sunday
    """

    MON = "Mon"
    TUE = "Tue"
    WED = "Wed"
    THU = "Thu"
    FRI = "Fri"
    SAT = "Sat"
    SUN = "Sun"


# =============================================================================
# GENERATION MODELS
# =============================================================================


class PlatformPost(BaseModel):
    """
    A single social media post for a specific platform.

    Contains the post text, format type identifier, and an optional
    image suggestion. This model is used for all three platforms
    (X, LinkedIn, Threads) with platform-specific character limits
    enforced elsewhere.

    Attributes:
        text: The post content text.
        format_type: Format identifier (e.g., "text", "thread", "poll").
        image_suggestion: Optional suggestion for an accompanying image.

    Example:
        >>> post = PlatformPost(
        ...     text="Just shipped a new feature! 🚀",
        ...     format_type="text",
        ...     image_suggestion="Screenshot of the new feature"
        ... )
    """

    text: str
    format_type: str
    image_suggestion: str | None = None


class PlatformPosts(BaseModel):
    """
    Container for posts across all three social media platforms.

    Holds PlatformPost instances for X (Twitter), LinkedIn, and Threads.
    Each platform has different character limits and tone expectations:
    - X: ≤280 chars, casual tone
    - LinkedIn: ≤1,500 chars, professional tone
    - Threads: ≤500 chars, conversational tone

    Attributes:
        x: Post for X (Twitter).
        linkedin: Post for LinkedIn.
        threads: Post for Threads.

    Example:
        >>> posts = PlatformPosts(
        ...     x=PlatformPost(text="Short post", format_type="text"),
        ...     linkedin=PlatformPost(text="Longer professional post...", format_type="text"),
        ...     threads=PlatformPost(text="Conversational post", format_type="text"),
        ... )
    """

    x: PlatformPost
    linkedin: PlatformPost
    threads: PlatformPost


class GeneratedBundle(BaseModel):
    """
    Complete generation output containing posts and metadata.

    This model represents the full output of a content generation run,
    including the generated posts for all platforms, the content pillar
    used, promotional status, and LLM provider information.

    Attributes:
        date: ISO date string (YYYY-MM-DD) for the generation date.
        day_of_week: Day of the week for pillar scheduling.
        pillar: Content pillar used for this generation.
        is_promotional: Whether this is promotional content (for 80/20 ratio).
        platform_posts: Posts for all three platforms.
        generated_at: ISO timestamp of when generation occurred.
        llm_provider: LLM provider used (e.g., "anthropic", "openai").
        llm_model: Specific model used (e.g., "claude-3-opus-20240229").

    Example:
        >>> bundle = GeneratedBundle(
        ...     date="2024-01-15",
        ...     day_of_week=DayOfWeek.MON,
        ...     pillar=Pillar.P1,
        ...     is_promotional=False,
        ...     platform_posts=PlatformPosts(...),
        ...     generated_at="2024-01-15T08:30:00Z",
        ...     llm_provider="anthropic",
        ...     llm_model="claude-3-opus-20240229",
        ... )
    """

    date: str
    day_of_week: DayOfWeek
    pillar: Pillar
    is_promotional: bool
    platform_posts: PlatformPosts
    generated_at: str
    llm_provider: str
    llm_model: str


class GenerationRecord(BaseModel):
    """
    Storage-equivalent record for history.json persistence.

    This model has the same fields as GeneratedBundle and is used for
    serializing/deserializing generation history to/from history.json.
    The history file maintains up to 30 records for pillar rotation,
    promotional ratio tracking, and topic deduplication.

    Attributes:
        date: ISO date string (YYYY-MM-DD) for the generation date.
        day_of_week: Day of the week for pillar scheduling.
        pillar: Content pillar used for this generation.
        is_promotional: Whether this is promotional content.
        platform_posts: Posts for all three platforms.
        generated_at: ISO timestamp of when generation occurred.
        llm_provider: LLM provider used.
        llm_model: Specific model used.

    Example:
        >>> record = GenerationRecord(
        ...     date="2024-01-15",
        ...     day_of_week=DayOfWeek.MON,
        ...     pillar=Pillar.P1,
        ...     is_promotional=False,
        ...     platform_posts=PlatformPosts(...),
        ...     generated_at="2024-01-15T08:30:00Z",
        ...     llm_provider="anthropic",
        ...     llm_model="claude-3-opus-20240229",
        ... )
    """

    date: str
    day_of_week: DayOfWeek
    pillar: Pillar
    is_promotional: bool
    platform_posts: PlatformPosts
    generated_at: str
    llm_provider: str
    llm_model: str


# =============================================================================
# CONFIGURATION MODELS
# =============================================================================


class ProjectConfig(BaseModel):
    """
    Project configuration for content generation context.

    Contains basic project information that is used to personalize
    the generated content. This information is embedded in the LLM
    prompt to ensure generated posts are relevant to the project.

    Attributes:
        name: The project name.
        description: Brief description of the project.

    Example:
        >>> project = ProjectConfig(
        ...     name="My SaaS App",
        ...     description="A task management tool for remote teams"
        ... )
    """

    name: str
    description: str


class AuthorConfig(BaseModel):
    """
    Author configuration for content generation context.

    Contains author information that is used to personalize the
    generated content and establish the author's voice and expertise.

    Attributes:
        bio: Author biography or professional background.

    Example:
        >>> author = AuthorConfig(
        ...     bio="Full-stack developer building in public"
        ... )
    """

    bio: str


class LLMConfig(BaseModel):
    """
    LLM provider configuration.

    Configures which LLM provider and model to use for content generation.
    The provider must be one of the supported providers. For local models
    (ollama, lmstudio, custom), a base_url can be specified.

    Attributes:
        provider: LLM provider name (must be in SUPPORTED_PROVIDERS).
        model: Model identifier (e.g., "claude-3-opus-20240229").
        base_url: Optional custom endpoint URL for local models.

    Example:
        >>> llm = LLMConfig(
        ...     provider="anthropic",
        ...     model="claude-3-opus-20240229"
        ... )
        >>> local_llm = LLMConfig(
        ...     provider="ollama",
        ...     model="llama2",
        ...     base_url="http://localhost:11434"
        ... )
    """

    provider: str
    model: str
    base_url: str | None = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """
        Validate that the provider is in the supported providers list.

        Args:
            v: The provider name to validate.

        Returns:
            The validated provider name.

        Raises:
            ValueError: If the provider is not supported.
        """
        if v not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {v}. "
                f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}"
            )
        return v


class ScheduleConfig(BaseModel):
    """
    Schedule configuration for automated content generation.

    Configures when the scheduler should trigger content generation.
    The time is specified in 24-hour HH:MM format.

    Attributes:
        time: Schedule time in HH:MM format (e.g., "08:00").

    Example:
        >>> schedule = ScheduleConfig(time="08:00")
    """

    time: str

    @field_validator("time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """
        Validate that the time matches HH:MM format.

        Args:
            v: The time string to validate.

        Returns:
            The validated time string.

        Raises:
            ValueError: If the time format is invalid.
        """
        if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", v):
            raise ValueError(
                f"Invalid time format: {v}. Expected HH:MM format (24-hour, e.g., '08:00')"
            )
        return v


class AppConfig(BaseModel):
    """
    Complete application configuration.

    Composes all configuration sections needed for the application to run.
    This includes project details, author info, LLM settings, and schedule.

    Attributes:
        project: Project configuration.
        author: Author configuration.
        milestones: List of milestone descriptions for context.
        changelog: List of recent changelog entries.
        llm: LLM provider configuration.
        schedule: Schedule configuration.

    Example:
        >>> config = AppConfig(
        ...     project=ProjectConfig(name="My App", description="..."),
        ...     author=AuthorConfig(bio="..."),
        ...     milestones=["v1.0 launched", "100 users"],
        ...     changelog=["Added dark mode", "Fixed login bug"],
        ...     llm=LLMConfig(provider="anthropic", model="..."),
        ...     schedule=ScheduleConfig(time="08:00"),
        ... )
    """

    project: ProjectConfig
    author: AuthorConfig
    milestones: list[str]
    changelog: list[str]
    llm: LLMConfig
    schedule: ScheduleConfig


class EnvConfig(BaseModel):
    """
    Environment configuration containing credentials.

    Contains all sensitive credentials needed for the application to
    communicate with external services (Telegram and LLM providers).

    Note: For v0, this uses plain strings. SecretStr upgrade is a v1 (P1) task.

    Attributes:
        telegram_bot_token: Telegram bot token from BotFather.
        telegram_chat_id: Telegram chat ID for delivery.
        api_keys: Mapping of provider names to API keys.

    Example:
        >>> env = EnvConfig(
        ...     telegram_bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        ...     telegram_chat_id="123456789",
        ...     api_keys={"anthropic": "sk-ant-...", "openai": "sk-..."},
        ... )
    """

    telegram_bot_token: str
    telegram_chat_id: str
    api_keys: dict[str, str]


# =============================================================================
# ERROR HIERARCHY
# =============================================================================


class PostwareError(Exception):
    """
    Base exception class for all Postware errors.

    All custom exceptions in the application inherit from this class.
    Provides a consistent error interface across the application.

    Attributes:
        message: Human-readable error message.
    """

    def __init__(self, message: str) -> None:
        """
        Initialize the exception with a message.

        Args:
            message: Human-readable error description.
        """
        self.message = message
        super().__init__(message)


class ConfigError(PostwareError):
    """
    Configuration validation error.

    Raised when configuration is invalid, missing, or fails validation.
    This includes missing required fields, invalid values, or
    configuration that doesn't meet business rules.
    """

    pass


class HistoryError(PostwareError):
    """
    History-related error.

    Raised when operations on history.json fail, including read, write,
    parse errors, or corruption recovery.
    """

    pass


class HistoryWriteError(HistoryError):
    """
    History write error.

    Raised when writing to history.json fails. This includes atomic
    write failures, permission errors, and disk space issues.
    """

    pass


class GenerationError(PostwareError):
    """
    Content generation error.

    Base class for all content generation-related errors, including
    LLM API calls, output parsing, and retry exhaustion.
    """

    pass


class LLMCallError(GenerationError):
    """
    LLM API call error.

    Raised when an LLM API call fails. This wraps provider-specific
    errors into a unified error type. Includes retry logic for
    transient failures.
    """

    pass


class LLMOutputError(GenerationError):
    """
    LLM output parsing error.

    Raised when the LLM response cannot be parsed or validated.
    This includes malformed JSON, missing required fields, and
    invalid content that doesn't match the expected schema.
    """

    pass


class GenerationFailedError(GenerationError):
    """
    Generation failure error.

    Raised when all retry attempts for content generation have been
    exhausted. This indicates a permanent failure that requires manual
    investigation.
    """

    pass


class DeliveryError(PostwareError):
    """
    Message delivery error.

    Raised when Telegram message delivery fails. This includes
    network errors, invalid credentials, and rate limiting.
    """

    pass


class DeliveryCredentialError(DeliveryError):
    """
    Delivery credential error.

    Raised when Telegram credentials are invalid (401/400 response).
    These errors should not be retried as they indicate permanent
    authentication failures.
    """

    pass


class DeliveryFailedError(DeliveryError):
    """
    Telegram delivery failure error.

    Raised when Telegram message delivery fails after all retry attempts.
    This includes network errors, rate limiting, and other delivery issues
    that are not related to invalid credentials.
    """

    pass


# =============================================================================
# CONSTANTS
# =============================================================================

# Maximum number of records retained in history.json.
#
# Per AGENTS.md and implementation plan, the history file is capped at 30
# records to support pillar rotation, promotional ratio tracking, and topic
# deduplication while keeping the file size manageable. The save() function
# in history.py enforces this invariant by pruning the oldest records when
# the limit is exceeded.
#
# This constant is used by:
# - history.py save() to prune records before writing
# - Tests to verify the pruning invariant (T-05)
MAX_HISTORY_RECORDS: int = 30

# Weekly pillar schedule mapping days to content pillars.
#
# Per PRD FR-003, this schedule ensures content variety across the week:
# - Monday: Build in Public (P1) - Start the week with progress sharing
# - Tuesday: Teaching (P2) - Educational content mid-week
# - Wednesday: Opinions (P3) - Thought leadership for hump day
# - Thursday: Data & Results (P4) - Metrics and experiments
# - Friday: Community (P5) - Engagement to end the work week
# - Saturday: Build in Public (P1) - Weekend progress update
# - Sunday: Opinions (P3) - Thought leadership for the new week
#
# This schedule is used by the generator to determine which pillar
# to use for a given day's content generation.
PILLAR_SCHEDULE: dict[DayOfWeek, Pillar] = {
    DayOfWeek.MON: Pillar.P1,
    DayOfWeek.TUE: Pillar.P2,
    DayOfWeek.WED: Pillar.P3,
    DayOfWeek.THU: Pillar.P4,
    DayOfWeek.FRI: Pillar.P5,
    DayOfWeek.SAT: Pillar.P1,
    DayOfWeek.SUN: Pillar.P3,
}

# Character limits per social media platform.
#
# These limits are enforced during content generation to ensure
# posts fit within each platform's constraints:
# - X (Twitter): 280 characters maximum
# - LinkedIn: 1,500 characters maximum
# - Threads: 500 characters maximum
#
# The generator uses these limits to validate post length before
# delivery and to provide feedback to the LLM during generation.
PLATFORM_CHAR_LIMITS: dict[str, int] = {
    "x": 280,
    "linkedin": 1500,
    "threads": 500,
}

# Supported LLM providers.
#
# This list defines all valid LLM provider names that can be used
# in the LLMConfig.provider field. Providers are categorized as:
# - Cloud providers: anthropic, openai, groq, google, deepseek, qwen, minimax, kimi, z.ai
# - Local providers: ollama, lmstudio, custom
#
# The LLMConfig.provider field uses a field_validator to enforce
# that only these values are accepted.
SUPPORTED_PROVIDERS: tuple[str, ...] = (
    # Cloud providers
    "anthropic",
    "openai",
    "groq",
    "google",
    "deepseek",
    "qwen",
    "minimax",
    "kimi",
    "z.ai",
    # Local providers
    "ollama",
    "lmstudio",
    "custom",
)

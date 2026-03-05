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

Constants defined:
    - PILLAR_SCHEDULE: Maps DayOfWeek → Pillar per PRD FR-003
    - PLATFORM_CHAR_LIMITS: Character limits per platform
    - MAX_HISTORY_RECORDS: Maximum records retained in history.json
"""

from enum import Enum

from pydantic import BaseModel


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

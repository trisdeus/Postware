"""
LiteLLM call wrapper with error normalisation and JSON response parsing.

This module provides the core LLM integration functions:
- call_llm: Makes API calls to LiteLLM with error wrapping
- parse_response: Strips markdown fences and parses JSON
- validate_output: Validates LLM response against GeneratedBundle schema
- resolve_pillar: Resolves content pillar based on day of week and recent history
- calculate_promo_constraint: Determines if value-driven content is required
- generate: Main orchestration function for content generation

This module imports from models.py, history.py, and prompts.py following
the dependency layering rules.
"""

import json
import logging
import re
from datetime import date, datetime
from typing import Any

import litellm

from postware.history import (
    get_deduplication_context,
    get_promo_ratio,
    get_recent_pillars,
)
from postware.models import (
    AppConfig,
    DayOfWeek,
    EnvConfig,
    GeneratedBundle,
    GenerationFailedError,
    GenerationRecord,
    LLMCallError,
    LLMConfig,
    LLMOutputError,
    Pillar,
    PILLAR_SCHEDULE,
)
from postware.prompts import build_system_prompt, build_user_prompt

# Get the module logger
logger = logging.getLogger("postware")


def call_llm(
    system_prompt: str,
    user_prompt: str,
    llm_config: LLMConfig,
    env: EnvConfig,
) -> str:
    """
    Call the LLM API via LiteLLM and return the raw response text.

    Constructs the model string from provider and model, retrieves the API key
    from env.api_keys, handles base_url for local models, and wraps all
    LiteLLM exceptions into LLMCallError.

    Args:
        system_prompt: The system prompt defining the LLM's role.
        user_prompt: The user prompt with generation context.
        llm_config: LLM provider and model configuration.
        env: Environment config containing API keys.

    Returns:
        The raw response text from the LLM.

    Raises:
        LLMCallError: If the LLM API call fails for any reason.
    """
    # Construct model string: "{provider}/{model}" for most providers
    model_string = f"{llm_config.provider}/{llm_config.model}"

    # Get API key for the provider
    api_key: str | None = env.api_keys.get(llm_config.provider)

    # Log the attempt at DEBUG level (no sensitive data)
    logger.debug(
        "Calling LLM: provider=%s, model=%s",
        llm_config.provider,
        llm_config.model,
    )

    try:
        # Build the completion call kwargs
        completion_kwargs: dict[str, Any] = {
            "model": model_string,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        # Add API key if provided
        if api_key is not None:
            completion_kwargs["api_key"] = api_key

        # Add base_url for local models (Ollama, LM Studio, custom)
        if llm_config.base_url is not None:
            completion_kwargs["base_url"] = llm_config.base_url

        # Make the LLM call
        response = litellm.completion(**completion_kwargs)

        # Extract the raw content from the response
        raw_content = response.choices[0].message.content

        if raw_content is None:
            raise LLMCallError("LLM returned empty response content")

        logger.debug("LLM call successful, response length: %d", len(raw_content))

        return raw_content

    # Catch all LiteLLM exceptions and wrap them
    except litellm.exceptions.AuthenticationError as e:
        logger.error("LLM authentication error: %s", str(e))
        raise LLMCallError(f"LLM authentication failed: {e}") from e
    except litellm.exceptions.RateLimitError as e:
        logger.error("LLM rate limit error: %s", str(e))
        raise LLMCallError(f"LLM rate limit exceeded: {e}") from e
    except litellm.exceptions.ServiceUnavailableError as e:
        logger.error("LLM service unavailable: %s", str(e))
        raise LLMCallError(f"LLM service unavailable: {e}") from e
    except litellm.exceptions.APIError as e:
        logger.error("LLM API error: %s", str(e))
        raise LLMCallError(f"LLM API error: {e}") from e
    except litellm.exceptions.Timeout as e:
        logger.error("LLM timeout: %s", str(e))
        raise LLMCallError(f"LLM request timed out: {e}") from e
    except litellm.exceptions.APIConnectionError as e:
        logger.error("LLM connection error: %s", str(e))
        raise LLMCallError(f"LLM connection failed: {e}") from e
    except Exception as e:
        # Catch any other unexpected errors and wrap them
        logger.error("Unexpected LLM error: %s", str(e))
        raise LLMCallError(f"Unexpected LLM error: {e}") from e


def resolve_pillar(day_of_week: DayOfWeek, recent_pillars: list[Pillar]) -> Pillar:
    """
    Resolve the content pillar for a given day of week.

    Uses PILLAR_SCHEDULE to get the default pillar for the day, then adjusts
    for pillar rotation if the same pillar was used recently. When the default
    pillar has been used in the last 3 generations, cycles to the next pillar
    in the schedule.

    Args:
        day_of_week: The day of the week to resolve the pillar for.
        recent_pillars: List of recent pillar names (strings) from history,
            ordered from most recent to oldest.

    Returns:
        The resolved Pillar enum value for today's content.

    Example:
        >>> resolve_pillar(DayOfWeek.MON, ["Build in Public", "Teaching"])
        <Pillar.P2: 'Teaching'>
    """
    # Get the default pillar from the schedule
    default_pillar = PILLAR_SCHEDULE[day_of_week]

    # If no recent pillars, use the default
    if not recent_pillars:
        return default_pillar

    # Check if the default pillar was used in recent generations
    # Use last 3 to allow some repetition but avoid back-to-back
    recent_limit = 3
    recent_check = recent_pillars[:recent_limit]
    default_pillar_name = default_pillar.value

    if default_pillar_name not in recent_check:
        return default_pillar

    # Default pillar was used recently, need to rotate
    # Find next available pillar that's not in recent history
    all_pillars = list(Pillar)
    current_index = all_pillars.index(default_pillar)

    # Try the next pillar, then keep cycling
    for offset in range(1, len(all_pillars)):
        next_index = (current_index + offset) % len(all_pillars)
        next_pillar = all_pillars[next_index]
        if next_pillar.value not in recent_check:
            logger.debug(
                "Rotating pillar from %s to %s due to recent usage",
                default_pillar_name,
                next_pillar.value,
            )
            return next_pillar

    # All pillars used recently, just return the default
    return default_pillar


def calculate_promo_constraint(promo_ratio: float) -> bool:
    """
    Calculate whether to enforce value-driven content based on promotional ratio.

    Enforces the 80/20 value-to-promotion ratio by returning True (forcing
    value-driven content) when the promotional ratio >= 20%.

    Args:
        promo_ratio: The current promotional ratio (0.0 to 1.0).

    Returns:
        True if value-driven content should be enforced (promo_ratio >= 0.20).
        False if promotional content is allowed (promo_ratio < 0.20).

    Example:
        >>> calculate_promo_constraint(0.15)
        False
        >>> calculate_promo_constraint(0.25)
        True
    """
    return promo_ratio >= 0.20


def generate(
    config: AppConfig,
    env: EnvConfig,
    records: list[GenerationRecord],
) -> GeneratedBundle:
    """
    Generate content bundle by orchestrating the full generation pipeline.

    This is the main orchestration function that:
    1. Gets today's date and day of week
    2. Resolves the content pillar using PILLAR_SCHEDULE and recent history
    3. Calculates promotional constraint from history
    4. Gets deduplication context from history
    5. Builds prompts using prompts.py
    6. Calls the LLM via call_llm()
    7. Parses the response via parse_response()
    8. Validates output via validate_output()
    9. Returns a complete GeneratedBundle with all metadata

    For v0: Single attempt only - any failure raises GenerationFailedError
    immediately without retry (retry is a v1/P1 feature).

    Args:
        config: Application configuration containing project details and LLM settings.
        env: Environment configuration containing API keys.
        records: List of GenerationRecord objects from history.

    Returns:
        A complete GeneratedBundle with all metadata fields populated.

    Raises:
        GenerationFailedError: If the generation pipeline fails at any step.
    """
    # Step 1: Get today's date and day of week
    today = date.today()
    day_of_week = DayOfWeek(today.strftime("%a"))  # Converts Mon, Tue, etc.

    # Step 2: Resolve today's pillar
    recent_pillar_names = get_recent_pillars(records, n=7)
    pillar = resolve_pillar(day_of_week, recent_pillar_names)

    logger.debug(
        "Resolved pillar for %s: %s (recent: %s)",
        day_of_week.value,
        pillar.value,
        recent_pillar_names[:3] if recent_pillar_names else [],
    )

    # Step 3: Calculate promotional constraint
    promo_ratio = get_promo_ratio(records, window_days=14)
    force_value_driven = calculate_promo_constraint(promo_ratio)

    if force_value_driven:
        logger.info(
            "Promo ratio %.1f%% >= 20%% - enforcing value-driven content",
            promo_ratio * 100,
        )

    # Step 4: Get deduplication context
    dedup_context = get_deduplication_context(records, n=10)

    # Step 5: Build prompts
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(
        config=config,
        pillar=pillar,
        force_value_driven=force_value_driven,
        dedup_context=dedup_context,
    )

    # Step 6: Call LLM (single attempt for v0)
    try:
        raw_response = call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_config=config.llm,
            env=env,
        )
    except LLMCallError as e:
        logger.error("LLM call failed: %s", e.message)
        raise GenerationFailedError(f"LLM call failed: {e.message}") from e

    # Step 7: Parse response
    try:
        parsed = parse_response(raw_response)
    except LLMOutputError as e:
        logger.error("Failed to parse LLM response: %s", e.message)
        raise GenerationFailedError(f"Failed to parse LLM response: {e.message}") from e

    # Step 8: Validate output
    try:
        bundle = validate_output(parsed)
    except LLMOutputError as e:
        logger.error("Failed to validate LLM output: %s", e.message)
        raise GenerationFailedError(f"Failed to validate LLM output: {e.message}") from e

    # Step 9: Populate metadata fields that couldn't be set by validate_output
    # Create a new bundle with all required fields
    generated_at = datetime.now().isoformat() + "Z"

    final_bundle = GeneratedBundle(
        date=today.isoformat(),
        day_of_week=day_of_week,
        pillar=pillar,
        is_promotional=bundle.is_promotional,
        platform_posts=bundle.platform_posts,
        generated_at=generated_at,
        llm_provider=config.llm.provider,
        llm_model=config.llm.model,
    )

    logger.info(
        "Generated bundle: date=%s, pillar=%s, is_promotional=%s, provider=%s",
        final_bundle.date,
        final_bundle.pillar.value,
        final_bundle.is_promotional,
        final_bundle.llm_provider,
    )

    return final_bundle


def parse_response(raw: str) -> dict[str, Any]:
    """
    Parse the LLM response by stripping markdown code fences and extracting JSON.

    Handles these patterns:
    - ```json\\n{...}\\n```
    - ```\\n{...}\\n```
    - Raw JSON without fences

    Args:
        raw: The raw string response from the LLM.

    Returns:
        The parsed JSON as a Python dictionary.

    Raises:
        LLMOutputError: If the response cannot be parsed as valid JSON.
    """
    if not raw or not raw.strip():
        raise LLMOutputError("LLM returned empty response")

    # Try to extract JSON from markdown code fences
    # Pattern 1: ```json\n{...}\n```
    json_fence_pattern = re.compile(
        r"```json\s*\n(.*?)\n```",
        re.DOTALL | re.IGNORECASE,
    )
    match = json_fence_pattern.search(raw)
    if match:
        json_str = match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise LLMOutputError(
                f"Failed to parse JSON from ```json fence: {e}"
            ) from e

    # Pattern 2: ```\n{...}\n``` (generic code fence)
    generic_fence_pattern = re.compile(
        r"```\s*\n(.*?)\n```",
        re.DOTALL,
    )
    match = generic_fence_pattern.search(raw)
    if match:
        json_str = match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise LLMOutputError(
                f"Failed to parse JSON from ``` fence: {e}"
            ) from e

    # Pattern 3: Try parsing the raw string as JSON
    # First, try stripping any leading/trailing whitespace
    stripped = raw.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as e:
        # Provide detailed error message with context
        preview = stripped[:200] + "..." if len(stripped) > 200 else stripped
        raise LLMOutputError(
            f"Failed to parse JSON response: {e}. "
            f"Response preview: {preview}"
        ) from e


def validate_output(parsed: dict[str, Any]) -> GeneratedBundle:
    """
    Validate the parsed LLM response against the GeneratedBundle schema.

    The LLM response contains only platform_posts and is_promotional.
    This function validates those fields and returns a bundle that can be
    enriched with metadata (date, day_of_week, pillar, generated_at,
    llm_provider, llm_model) by the caller.

    Args:
        parsed: The parsed dictionary from the LLM response.

    Returns:
        A GeneratedBundle with the validated platform posts and promotional flag.
        Note: The caller must set date, day_of_week, pillar, generated_at,
        llm_provider, and llm_model fields after calling this function.

    Raises:
        LLMOutputError: If validation fails due to missing fields or invalid types.
    """
    # Validate using Pydantic - this will raise ValidationError if invalid
    try:
        bundle = GeneratedBundle.model_validate(parsed)
        return bundle
    except Exception as e:
        raise LLMOutputError(
            f"Failed to validate LLM output against schema: {e}"
        ) from e

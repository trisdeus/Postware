"""
LiteLLM call wrapper with error normalisation and JSON response parsing.

This module provides the core LLM integration functions:
- call_llm: Makes API calls to LiteLLM with error wrapping
- parse_response: Strips markdown fences and parses JSON
- validate_output: Validates LLM response against GeneratedBundle schema

This module imports from models.py (the dependency floor) and litellm.
No other src/postware modules are imported here to maintain layering.
"""

import json
import logging
import re
from typing import Any

import litellm

from postware.models import (
    EnvConfig,
    GeneratedBundle,
    LLMCallError,
    LLMConfig,
    LLMOutputError,
)

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

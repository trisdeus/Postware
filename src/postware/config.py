"""
Configuration loading and validation for Postware.

This module provides functions to load and validate configuration from config.yaml
and environment variables from .env file. All configuration is validated using
Pydantic models defined in models.py.

Functions:
    load_config: Load and validate config.yaml
    load_env: Load and validate .env file

Imports:
    This module follows the dependency layering rule - it imports ONLY from
    models.py. No other src/postware/ modules are imported.

Error Handling:
    All errors are converted to ConfigError with human-readable messages:
    - Missing config.yaml -> "config.yaml not found"
    - Invalid YAML -> includes line number if available
    - Pydantic validation errors -> lists each failed field
    - Missing required env vars -> lists each missing field
"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import SecretStr, ValidationError

from postware.models import AppConfig, ConfigError, EnvConfig


def load_config(path: Path) -> AppConfig:
    """
    Load and validate configuration from a YAML file.

    Reads the configuration file at the given path, parses it as YAML,
    and validates it against the AppConfig Pydantic model.

    Args:
        path: Path to the config.yaml file.

    Returns:
        Validated AppConfig instance.

    Raises:
        ConfigError: If the file cannot be read, parsed, or validated.
            - FileNotFoundError: "config.yaml not found. Run 'postware init' first."
            - yaml.YAMLError: Includes line number if available.
            - ValidationError: Lists each failed field with error message.
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigError(
            f"config.yaml not found. Run 'postware init' first to create "
            f"the configuration file."
        )
    except yaml.YAMLError as e:
        # Extract line number if available from YAML error
        if hasattr(e, "problem_mark") and e.problem_mark:
            line = e.problem_mark.line + 1  # 1-based line number
            raise ConfigError(f"Invalid YAML at line {line}: {e.problem}")
        raise ConfigError(f"Invalid YAML: {e}")

    # Validate against Pydantic model
    try:
        return AppConfig(**data)
    except ValidationError as e:
        # Build a human-readable error message listing each failed field
        errors: list[str] = []
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            msg = error["msg"]
            errors.append(f"  - {field}: {msg}")
        error_details = "\n".join(errors)
        raise ConfigError(f"Configuration validation failed:\n{error_details}")


def load_env() -> EnvConfig:
    """
    Load and validate environment variables from .env file.

    Reads the .env file using python-dotenv and validates the required
    environment variables against the EnvConfig Pydantic model.

    Note:
        The .env file is loaded from the current working directory.
        This is typically the project root where postware is run.

    Returns:
        Validated EnvConfig instance with SecretStr-wrapped credentials.

    Raises:
        ConfigError: If the .env file cannot be loaded or validated.
            - Missing required fields: Lists each missing required field.
            - ValidationError: Lists each failed field with error message.
    """
    # Load .env file from current working directory
    loaded = load_dotenv()

    if not loaded:
        # .env file not found - check if it exists
        env_path = Path(".env")
        if not env_path.exists():
            raise ConfigError(
                ".env file not found. Run 'postware init' first to create "
                "the environment configuration file."
            )

    # Check for required fields before Pydantic validation
    # This provides more specific error messages
    required_fields = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    missing_fields: list[str] = []

    for field in required_fields:
        value = os.environ.get(field)
        if not value or value == "":
            missing_fields.append(field)

    if missing_fields:
        raise ConfigError(
            f"Missing required environment variables: {', '.join(missing_fields)}"
        )

    # Build api_keys dict from known provider environment variables.
    #
    # Cloud providers (anthropic, openai, groq, google, deepseek, qwen, minimax,
    # kimi, z.ai) require API keys set via environment variables.
    #
    # Local model providers (ollama, lmstudio, custom) do NOT use API keys.
    # They are configured via config.yaml using the llm.base_url field.
    # These providers are intentionally excluded from this mapping.
    api_keys: dict[str, SecretStr] = {}

    # Cloud provider environment variable mappings
    provider_env_vars = {
        "ANTHROPIC_API_KEY": "anthropic",
        "OPENAI_API_KEY": "openai",
        "GROQ_API_KEY": "groq",
        "GOOGLE_API_KEY": "google",
        "DEEPSEEK_API_KEY": "deepseek",
        "QWEN_API_KEY": "qwen",
        "MINIMAX_API_KEY": "minimax",
        "KIMI_API_KEY": "kimi",
        "ZAI_API_KEY": "z.ai",
    }

    for env_var, provider in provider_env_vars.items():
        value = os.environ.get(env_var)
        if value:
            api_keys[provider] = SecretStr(value)

    # Validate with Pydantic
    try:
        return EnvConfig(
            telegram_bot_token=SecretStr(os.environ.get("TELEGRAM_BOT_TOKEN", "")),
            telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
            api_keys=api_keys,
        )
    except ValidationError as e:
        # Build a human-readable error message listing each failed field
        errors: list[str] = []
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            msg = error["msg"]
            errors.append(f"  - {field}: {msg}")
        error_details = "\n".join(errors)
        raise ConfigError(f"Environment validation failed:\n{error_details}")

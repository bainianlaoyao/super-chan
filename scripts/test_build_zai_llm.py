#!/usr/bin/env python3
"""Test script for build_zai_llm function.

This script demonstrates how to use the build_zai_llm function to create an LLM callable
and perform a real test call using actual configuration.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from superchan.utils.config import load_user_config
from superchan.utils.llm_providers import build_zai_llm


async def test_build_zai_llm(prompt: str = "Hello, how are you?"):
    """Test the build_zai_llm function with a real API call."""
    print("Testing build_zai_llm function...")

    # Load user configuration from config/user.toml
    user_config = load_user_config(str(project_root))
    cfg = user_config.llm

    # Validate that required config is present
    if not cfg.api_key:
        raise ValueError("API key not found in configuration. Please set [llm].api_key in config/user.toml")
    if not cfg.model:
        raise ValueError("Model not specified in configuration. Please set [llm].model in config/user.toml")

    try:
        # Build the LLM callable
        llm_callable = build_zai_llm(cfg)
        print("✓ Successfully built LLM callable")
        print(f"  Provider: {cfg.provider or 'default (zai)'}")
        print(f"  Model: {cfg.model}")

        # Perform the test call
        print(f"Calling LLM with prompt: '{prompt}'")
        response = await llm_callable(prompt)
        print("✓ LLM call successful")
        print(f"Response: {response}")

    except Exception as e:
        print(f"✗ Error during test: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Test build_zai_llm function with real API calls")
    parser.add_argument(
        "--prompt",
        type=str,
        default="Hello from Copilot. Say hi in one short sentence.",
        help="Prompt to send to the LLM"
    )

    args = parser.parse_args()

    try:
        asyncio.run(test_build_zai_llm(prompt=args.prompt))
        print("\nTest completed successfully!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

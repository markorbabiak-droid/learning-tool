"""
api_client.py — All communication with Claude's API lives here.

Every other file that needs to talk to Claude imports from this file.
If anything changes about how we call Claude (different model, settings,
or error handling), we change it in one place — here.
"""

import os
import sys
import anthropic
from dotenv import load_dotenv


def get_client():
    """
    Reads your API key from the .env file and creates a live connection to Claude.

    The .env file sits in the root of the learning-tool folder.
    It contains one line: ANTHROPIC_API_KEY=sk-ant-your-key-here

    What this function does, step by step:
      1. Calls load_dotenv() to read the .env file into memory
      2. Reads the API key out of the environment
      3. Checks that the key exists and isn't still the placeholder
      4. Creates and returns an Anthropic client object

    Returns: an anthropic.Anthropic object — the "phone line" to Claude's API.
    """

    # load_dotenv() opens the .env file and loads its contents so that
    # os.getenv() can read them. Without this line, the .env file is ignored.
    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY")

    # Check that the key exists and isn't still the placeholder we shipped
    if not api_key or api_key == "your-api-key-here":
        print()
        print("=" * 55)
        print("  ERROR: API key not found or not configured.")
        print("=" * 55)
        print()
        print("  To fix this:")
        print("  1. Open:  ~/Desktop/learning-tool/.env")
        print("  2. Replace 'your-api-key-here' with your real key")
        print("  3. Get a free key at: console.anthropic.com")
        print()
        sys.exit(1)

    return anthropic.Anthropic(api_key=api_key)


def call_claude(client, prompt, max_tokens=4000, model="claude-sonnet-4-6", system=None):
    """
    Sends a prompt to Claude and returns the response as a plain string.

    This function has exactly one job: make the API call and return the text.
    It does NOT parse the response, validate it, or process it in any way.
    That work happens in the functions that call this one.

    Arguments:
      client     — the connection object returned by get_client()
      prompt     — the user-turn text to send to Claude
      max_tokens — the maximum length Claude can respond with
                   (4000 tokens ≈ about 3,000 words — enough for rich notes)
      model      — which Claude model to use. Defaults to Sonnet for note
                   generation. Pass "claude-haiku-4-5-20251001" for cheaper
                   classification tasks like the Extra field audit.
      system     — optional system prompt. When provided, rules and instructions
                   go here and only the data goes in the user turn (prompt).
                   This prevents the model from confusing instructions with
                   the material it is supposed to process.

    Returns: Claude's response as a plain Python string.
    """

    # Build the API call kwargs — system is optional
    call_kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    if system:
        call_kwargs["system"] = system

    try:
        response = client.messages.create(**call_kwargs)

        # response.content is a list of content blocks.
        # For a text-only response, there's always exactly one block at index [0].
        # .text gives us the string inside that block.
        return response.content[0].text

    except anthropic.AuthenticationError:
        # This happens when the API key is wrong or expired
        print()
        print("  ERROR: API key was rejected by Claude.")
        print("  Double-check the key in your .env file.")
        print("  You can verify or regenerate it at: console.anthropic.com")
        sys.exit(1)

    except anthropic.RateLimitError:
        # This happens if you send too many requests in a short window
        print()
        print("  ERROR: Too many requests sent too quickly.")
        print("  Wait about 30 seconds and try again.")
        sys.exit(1)

    except anthropic.APIConnectionError:
        # This happens when there's no internet or the API is unreachable
        print()
        print("  ERROR: Could not reach the Claude API.")
        print("  Check your internet connection and try again.")
        print("  Your input.txt file was not modified.")
        sys.exit(1)

    except anthropic.APIStatusError as e:
        # Catch-all for unexpected API responses (server errors, etc.)
        print()
        print(f"  ERROR: Unexpected API response (status code: {e.status_code}).")
        print("  Try running again. If it keeps happening, check status.anthropic.com")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# QUICK CONNECTION TEST
#
# `if __name__ == "__main__":` is a Python idiom that means:
#   "Only run the code below if this specific file was launched directly
#    (e.g. python src/api_client.py). Do NOT run it when another file
#    imports this one."
#
# This lets us put a test at the bottom of the file that proves the API
# connection works, without that test running every time note_engine.py
# starts up.
#
# To run it:  python src/api_client.py
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("Testing Claude API connection...")
    print("(This will take a few seconds)")
    print()

    test_client = get_client()

    response = call_claude(
        test_client,
        "Please respond with exactly this sentence and nothing else: "
        "Connection test successful.",
        max_tokens=30
    )

    print(f"Claude responded: {response}")
    print()
    print("✓ API connection is working. Ready to build.")
    print()

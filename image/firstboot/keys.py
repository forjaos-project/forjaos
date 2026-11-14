#!/usr/bin/env python3
"""Store an API key through the Secret Service without putting it in argv or files."""

import argparse
import getpass
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("provider", choices=["anthropic", "openai", "openrouter", "nous"])
    args = parser.parse_args()
    secret = getpass.getpass(f"{args.provider} API key: ")
    if not secret:
        return 2
    try:
        result = subprocess.run(
            ["secret-tool", "store", "--label", f"ForjaOS {args.provider}",
             "application", "forjaos", "provider", args.provider],
            input=secret, text=True, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, check=False,
        )
    except OSError:
        return 1
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

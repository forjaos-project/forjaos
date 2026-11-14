#!/usr/bin/env python3
"""Run Nous Research's official noninteractive Linux installer for the user."""

from pathlib import Path
import subprocess
import tempfile
from urllib.request import urlopen


SOURCE = "https://hermes-agent.nousresearch.com/install.sh"


def main():
    with tempfile.TemporaryDirectory(prefix="forja-hermes-") as temporary:
        installer = Path(temporary) / "install.sh"
        with urlopen(SOURCE, timeout=30) as response, installer.open("wb") as output:
            output.write(response.read())
        return subprocess.run(["bash", str(installer), "--non-interactive",
                               "--skip-browser", "--skip-computer-use"],
                              check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())

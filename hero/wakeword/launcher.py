#!/usr/bin/env python3
"""Execute the pinned wake-word runtime without activating any voice model."""

import os
import sys


PYTHON = "/opt/forjaos/wakeword-runtime/.venv/bin/python"
WORKER = "/usr/share/forjaos/wakeword/worker.py"


if __name__ == "__main__":
    os.execv(PYTHON, [PYTHON, WORKER, *sys.argv[1:]])

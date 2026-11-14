#!/usr/bin/env python3
"""Install the vendor's Linux archive for the current user."""

import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import time
from urllib.request import urlopen


SOURCE = "https://dl.pstmn.io/download/latest/linux64"


def main():
    home = Path.home()
    destination = home / ".local" / "opt"
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="forja-postman-") as temporary:
        root = Path(temporary)
        archive = root / "postman.tar.gz"
        with urlopen(SOURCE, timeout=60) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
        unpacked = root / "unpacked"
        unpacked.mkdir()
        with tarfile.open(archive, "r:gz") as package:
            package.extractall(unpacked, filter="data")
        application = unpacked / "Postman" / "app" / "Postman"
        if not application.is_file():
            raise ValueError("Postman archive lacks the expected executable")
        target = destination / f"Postman-{int(time.time())}"
        os.replace(unpacked / "Postman", target)
    launchers = home / ".local" / "share" / "applications"
    launchers.mkdir(mode=0o700, parents=True, exist_ok=True)
    launcher = launchers / "forjaos-postman.desktop"
    launcher.write_text(
        "[Desktop Entry]\nType=Application\nName=Postman\n"
        f"Exec={target / 'app' / 'Postman'} %U\n"
        f"Icon={target / 'app' / 'resources' / 'app' / 'assets' / 'icon.png'}\n"
        "Terminal=false\nCategories=Development;\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

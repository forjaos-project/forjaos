#!/usr/bin/env python3
"""Install official export templates matching the installed Godot Flatpak."""

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.request import Request, urlopen
import zipfile


def main():
    result = subprocess.run(["flatpak", "run", "org.godotengine.Godot", "--headless", "--version"],
                            capture_output=True, text=True, check=False)
    if result.returncode:
        return 1
    match = re.search(r"(\d+\.\d+(?:\.\d+)?)\.stable", result.stdout)
    if not match:
        return 1
    version = match.group(1)
    tag = f"{version}-stable"
    asset_name = f"Godot_v{tag}_export_templates.tpz"
    request = Request(f"https://api.github.com/repos/godotengine/godot-builds/releases/tags/{tag}",
                      headers={"Accept": "application/vnd.github+json", "User-Agent": "ForjaOS"})
    with urlopen(request, timeout=30) as response:
        release = json.load(response)
    asset = next((item for item in release["assets"] if item["name"] == asset_name), None)
    if not asset or not asset.get("digest", "").startswith("sha256:"):
        return 1
    expected = asset["digest"].split(":", 1)[1]
    destination = Path.home() / ".var" / "app" / "org.godotengine.Godot" / "data" / "godot" / "export_templates"
    target = destination / f"{version}.stable"
    if target.is_dir():
        return 0
    with tempfile.TemporaryDirectory(prefix="forja-godot-") as temporary:
        archive = Path(temporary) / asset_name
        with urlopen(asset["browser_download_url"], timeout=60) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
        hasher = hashlib.sha256()
        with archive.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        if digest != expected:
            return 1
        with zipfile.ZipFile(archive) as package:
            for name in package.namelist():
                if not name.startswith("templates/") or ".." in Path(name).parts:
                    return 1
            package.extractall(temporary)
        destination.mkdir(parents=True, exist_ok=True)
        shutil.move(str(Path(temporary) / "templates"), str(target))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Install Google's official Chrome RPM inside a rootless Distrobox."""

import subprocess
import platform


BOX = "forja-web"
IMAGE = "registry.fedoraproject.org/fedora-toolbox:" + platform.freedesktop_os_release()["VERSION_ID"]
RPM = "https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm"


def run(*args):
    return subprocess.run(args, check=False).returncode


def main():
    if run("podman", "container", "exists", BOX):
        if run("distrobox", "create", "--yes", "--name", BOX, "--image", IMAGE):
            return 1
    if run("distrobox", "enter", "--no-tty", "--name", BOX, "--",
           "sudo", "-n", "dnf", "install", "-y", RPM):
        return 1
    return run("distrobox", "enter", "--no-tty", "--name", BOX, "--",
               "distrobox-export", "--app", "google-chrome")


if __name__ == "__main__":
    raise SystemExit(main())

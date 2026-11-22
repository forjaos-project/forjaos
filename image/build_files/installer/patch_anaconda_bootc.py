#!/usr/bin/env python3
"""Guard Anaconda bootc cleanup against unmounted Btrfs subvolumes."""

from pathlib import Path


ANCHOR = '''            if os.path.ismount(path):
                log.debug("Unmounting %s", path)
                safe_exec_program("umount", ["-l", path])

            safe_exec_program("rm", ["-rf", path])'''

REPLACEMENT = '''            if os.path.ismount(path):
                # os.path.ismount() also returns True for Btrfs subvolumes that
                # are not mounted. Do not unmount or remove an existing one.
                if blivet.util.get_mount_device(path) is None:
                    raise PayloadInstallationError(
                        "Existing unmounted Btrfs subvolume at %s. "
                        "Select it as a mount point or explicitly reformat "
                        "the target filesystem before installing." % path
                    )
                log.debug("Unmounting %s", path)
                safe_exec_program("umount", ["-l", path])

            safe_exec_program("rm", ["-rf", path])'''


def patch(source: str) -> str:
    if source.count(ANCHOR) != 1:
        raise ValueError("expected exactly one Anaconda bootc cleanup block")
    return source.replace(ANCHOR, REPLACEMENT)


def main() -> None:
    candidates = list(Path("/usr/lib64").glob(
        "python*/site-packages/pyanaconda/modules/payloads/payload/rpm_ostree/installation.py"
    ))
    if len(candidates) != 1:
        raise ValueError("expected exactly one installed Anaconda bootc module")
    module = candidates[0]
    source = module.read_text(encoding="utf-8")
    updated = patch(source)
    compile(updated, str(module), "exec")
    module.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()

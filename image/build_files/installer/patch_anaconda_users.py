#!/usr/bin/env python3
"""Relabel target account files before Anaconda sets a bootc user password."""

from pathlib import Path


ANCHOR = '        proc = util.startProgram(["chpasswd", "-e"] + rootargs, stdin=subprocess.PIPE)'
RESTORE = '''        if root != "/":
            status = util.execWithRedirect(
                "restorecon", ["/etc/passwd", "/etc/shadow"], root=root
            )
            if status != 0:
                raise OSError(
                    "Unable to restore target account SELinux labels: status=%s" % status
                )

'''


def patch(source: str) -> str:
    if source.count(ANCHOR) != 1:
        raise ValueError("expected exactly one Anaconda chpasswd call")
    return source.replace(ANCHOR, RESTORE + ANCHOR)


def main() -> None:
    candidates = list(Path("/usr/lib64").glob("python*/site-packages/pyanaconda/core/users.py"))
    if len(candidates) != 1:
        raise ValueError("expected exactly one installed Anaconda users.py")
    users = candidates[0]
    source = users.read_text(encoding="utf-8")
    updated = patch(source)
    compile(updated, str(users), "exec")
    users.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Relabel target account files before Anaconda sets a bootc user password."""

from pathlib import Path


ANCHOR = '        proc = util.startProgram(["chpasswd", "-e"] + rootargs, stdin=subprocess.PIPE)'
RESTORE = '''        if root != "/":
            # restorecon inside this chroot silently succeeds when /sys/fs/selinux
            # is unavailable. Run setfiles in the live installer instead.
            policy = os.path.join(
                root, "etc/selinux/targeted/contexts/files/file_contexts"
            )
            account_files = [
                (os.path.join(root, "etc/passwd"), "passwd_file_t"),
                (os.path.join(root, "etc/shadow"), "shadow_t"),
            ]
            if not os.path.isfile(policy):
                raise OSError("Target SELinux file contexts not found: %s" % policy)
            status = util.execWithRedirect(
                "setfiles", ["-F", "-r", root, policy]
                + [path for path, _ in account_files]
            )
            if status != 0:
                raise OSError(
                    "Unable to label target account files: status=%s" % status
                )
            for path, expected_type in account_files:
                label = os.getxattr(path, "security.selinux").decode("ascii").rstrip("\\x00")
                if label.split(":")[2] != expected_type:
                    raise OSError(
                        "Wrong SELinux type for %s: %s (expected %s)"
                        % (path, label, expected_type)
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

#!/usr/bin/env python3
"""Relabel target account files before Anaconda sets a bootc user password."""

from pathlib import Path


ANCHOR = '        proc = util.startProgram(["chpasswd", "-e"] + rootargs, stdin=subprocess.PIPE)'
RESTORE = '''        if root != "/":
            # restorecon inside this chroot silently succeeds when /sys/fs/selinux
            # is unavailable. Run setfiles in the live installer instead.
            # setfiles refuses symbolic-link ancestors; /mnt points to /var/mnt
            # in the bootc installer. Resolve the prefix before building paths.
            label_root = os.path.realpath(root)
            policy = os.path.join(
                label_root, "etc/selinux/targeted/contexts/files/file_contexts"
            )
            account_files = [
                (os.path.join(label_root, "etc/passwd"), "passwd_file_t"),
                (os.path.join(label_root, "etc/shadow"), "shadow_t"),
            ]
            # chpasswd replaces the backups too; an etc_t shadow- blocks unlink.
            for name, expected_type in (
                ("group", "passwd_file_t"), ("gshadow", "shadow_t"),
                ("passwd-", "passwd_file_t"), ("shadow-", "shadow_t"),
                ("group-", "passwd_file_t"), ("gshadow-", "shadow_t"),
                (".pwd.lock", "passwd_file_t"),
            ):
                path = os.path.join(label_root, "etc", name)
                if os.path.isfile(path):
                    account_files.append((path, expected_type))
            if not os.path.isfile(policy):
                raise OSError("Target SELinux file contexts not found: %s" % policy)
            # The target can define types absent from the live installer (for
            # example mysql-selinux). Validate against its compiled policy.
            policy_dir = os.path.join(label_root, "etc/selinux/targeted/policy")
            binary_policies = [
                os.path.join(policy_dir, name)
                for name in os.listdir(policy_dir)
                if name.startswith("policy.") and name[7:].isdigit()
                and os.path.isfile(os.path.join(policy_dir, name))
            ]
            if not binary_policies:
                raise OSError("Target SELinux binary policy not found: %s" % policy_dir)
            binary_policy = max(
                binary_policies, key=lambda path: int(path.rsplit(".", 1)[1])
            )
            status = util.execWithRedirect(
                "setfiles", ["-F", "-r", label_root, "-c", binary_policy, policy]
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

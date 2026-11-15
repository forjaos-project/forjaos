#!/usr/bin/env python3
"""List installed Python distributions and their declared license metadata."""

from importlib.metadata import distributions


def cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|").replace("`", "\\`")


def main() -> None:
    packages = sorted(
        distributions(),
        key=lambda distribution: (
            distribution.metadata.get("Name") or ""
        ).casefold(),
    )
    print("# Third-party Python licenses\n")
    print(f"Inventory: {len(packages)} installed Python distributions.\n")
    print(
        "This report reproduces license metadata declared by installed Python "
        "distributions. It does not certify legal compatibility. License files "
        "included in each distribution remain under its `.dist-info/licenses/` "
        "directory when provided.\n"
    )
    print("| Distribution | Version | License metadata | License files |")
    print("| --- | --- | --- | --- |")
    for distribution in packages:
        name = distribution.metadata.get("Name") or "unknown"
        license_name = (
            distribution.metadata.get("License-Expression")
            or distribution.metadata.get("License")
            or "unspecified in package metadata"
        )
        license_files = sorted(
            {
                str(path).replace("\\", "/").rsplit("/", 1)[-1]
                for path in distribution.files or ()
                if ".dist-info/licenses/" in str(path).replace("\\", "/")
            }
        )
        print(
            f"| {cell(name)} | {cell(distribution.version)} | "
            f"{cell(license_name)} | "
            f"{cell(', '.join(license_files) or 'none')} |"
        )


if __name__ == "__main__":
    main()

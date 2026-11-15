#!/usr/bin/env python3
"""Classify critical Trivy findings as image-specific or inherited from its base."""

import argparse
import json
from pathlib import Path


def critical_findings(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read Trivy report {path}: {exc}") from exc
    if not isinstance(report, dict):
        raise ValueError(f"invalid Trivy report: {path}")
    results = report.get("Results") or []
    if not isinstance(results, list):
        raise ValueError(f"invalid Trivy report: {path}")

    findings = {}
    for result in results:
        if not isinstance(result, dict):
            continue
        for vulnerability in result.get("Vulnerabilities") or []:
            if not isinstance(vulnerability, dict):
                continue
            if str(vulnerability.get("Severity", "")).upper() != "CRITICAL":
                continue
            vulnerability_id = str(vulnerability.get("VulnerabilityID", "")).strip()
            package = str(vulnerability.get("PkgName", "")).strip()
            if not vulnerability_id or not package:
                continue
            key = (vulnerability_id, package)
            findings[key] = {
                "id": vulnerability_id,
                "package": package,
                "installed_version": str(vulnerability.get("InstalledVersion", "")),
                "fixed_version": str(vulnerability.get("FixedVersion", "")),
                "target": str(result.get("Target", "")),
            }
    return findings


def classify(image: dict, base: dict) -> dict[str, list[dict[str, str]]]:
    inherited = []
    new = []
    for key, finding in sorted(image.items()):
        (inherited if key in base else new).append(finding)
    return {"inherited": inherited, "new": new}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-report", type=Path, required=True)
    parser.add_argument("--base-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = classify(
            critical_findings(args.image_report), critical_findings(args.base_report)
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps({key: len(value) for key, value in result.items()}))
    if result["new"]:
        print("Trivy: critical vulnerabilities introduced by the ForjaOS image", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

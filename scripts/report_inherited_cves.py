#!/usr/bin/env python3
"""Create or update GitHub issues for critical CVEs inherited from Bazzite."""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def github_request(method: str, url: str, payload: dict | None = None) -> object:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "ForjaOS-Trivy-Reporter",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API returned HTTP {exc.code}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API request failed: {exc.reason}") from None


def safe_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ").replace("`", "'")


def report_for_variant(path: Path, repository: str, variant: str, run_url: str) -> bool:
    try:
        findings = json.loads(path.read_text(encoding="utf-8")).get("inherited", [])
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        raise RuntimeError(f"cannot read inherited CVE report {path}: {exc}") from exc
    if not findings:
        return False

    title = f"[NFR-026] CVEs críticas herdadas — {variant}"
    lines = [
        "A imagem ForjaOS contém CVEs críticas já presentes na imagem-base Bazzite.",
        "Este registro não bloqueou a publicação: o gate bloqueia somente CVEs críticas novas.",
        "",
        f"Run: {run_url}",
        f"Variante: `{variant}`",
        "",
        "| CVE | Pacote | Versão instalada | Correção disponível | Alvo |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in findings:
        lines.append(
            "| " + " | ".join(
                safe_cell(item.get(field, ""))
                for field in ("id", "package", "installed_version", "fixed_version", "target")
            ) + " |"
        )
    body = "\n".join(lines)

    encoded_repo = urllib.parse.quote(repository, safe="/")
    issues_url = f"https://api.github.com/repos/{encoded_repo}/issues?state=open&per_page=100&page="
    open_issues = []
    page = 1
    while True:
        issues = github_request("GET", f"{issues_url}{page}")
        if not isinstance(issues, list):
            raise RuntimeError("GitHub returned an unexpected issue list")
        open_issues.extend(issues)
        if len(issues) < 100:
            break
        page += 1
    existing = next(
        (
            issue for issue in open_issues
            if isinstance(issue, dict)
            and not issue.get("pull_request")
            and issue.get("title") == title
        ),
        None,
    )
    if existing:
        number = int(existing["number"])
        issue_url = f"https://api.github.com/repos/{encoded_repo}/issues/{number}"
        github_request("PATCH", issue_url, {"body": body})
        print(f"Atualizada issue #{number} para {variant}.")
    else:
        created = github_request(
            "POST",
            f"https://api.github.com/repos/{encoded_repo}/issues",
            {"title": title, "body": body},
        )
        print(f"Criada issue #{created['number']} para {variant}.")
    return True


def main() -> int:
    report_dir = Path(os.environ.get("TRIVY_REPORT_DIR", ""))
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    if not report_dir.is_dir():
        print("Nenhum relatório Trivy disponível; nada a notificar.")
        return 0
    if not repository or not run_id:
        print("GITHUB_REPOSITORY e GITHUB_RUN_ID são obrigatórios.", file=sys.stderr)
        return 1
    run_url = f"{server_url}/{repository}/actions/runs/{run_id}"

    try:
        reports = sorted(report_dir.glob("**/classified.json"))
        for path in reports:
            report_for_variant(path, repository, path.parent.name, run_url)
    except (RuntimeError, KeyError, TypeError) as exc:
        print(f"Trivy issue reporter: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

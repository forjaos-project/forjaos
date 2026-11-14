# forja CLI — English

Output generated from the `forja` binary using `--help`.

## `forja`

```text
forja 0.1.0
ForjaOS: diagnostics, installation, and assistant in one command

Usage: forja [OPTIONS] <COMMAND>

Commands:
  doctor   Check the system and report critical failures
  install  Install optional development tools for the current user

Options:
      --lang <LANG>  Help language: pt-br or en [default: en] [possible values: pt-br, en]
  -h, --help         Print help
  -V, --version      Print version
```

## `forja doctor`

```text
Check the system and report critical failures

Usage: forja doctor [OPTIONS]

Options:
      --json         Output JSON for scripts
      --lang <LANG>  Help language: pt-br or en [default: en] [possible values: pt-br, en]
  -h, --help         Print help
```

## Official installer documentation

- [Install Unity Hub on Linux](https://docs.unity.com/en-us/hub/install-hub-linux)
- [Install Claude Code](https://code.claude.com/docs/en/getting-started)

## `forja install`

```text
Install optional development tools for the current user

Usage: forja install [OPTIONS] <COMMAND>

Commands:
  unity        Download the official Unity Hub AppImage into ~/.local
  claude-code  Install Claude Code with Anthropic's official installer

Options:
      --lang <LANG>  Help language: pt-br or en [default: en] [possible values: pt-br, en]
  -h, --help         Print help
```

## `forja install unity`

```text
Download the official Unity Hub AppImage into ~/.local

Usage: forja install unity [OPTIONS]

Options:
      --lang <LANG>  Help language: pt-br or en [default: en] [possible values: pt-br, en]
  -y, --yes          Confirm installation without interaction
      --json         Output only the structured JSON result
  -h, --help         Print help
```

## `forja install claude-code`

```text
Install Claude Code with Anthropic's official installer

Usage: forja install claude-code [OPTIONS]

Options:
      --lang <LANG>  Help language: pt-br or en [default: en] [possible values: pt-br, en]
  -y, --yes          Confirm installation without interaction
      --json         Output only the structured JSON result
  -h, --help         Print help
```

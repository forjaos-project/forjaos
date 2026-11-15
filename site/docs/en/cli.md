# forja CLI — English

Output generated from the `forja` binary using `--help`.

## `forja`

```text
forja 0.1.0
ForjaOS: diagnostics, installation, and assistant in one command

Usage: forja [OPTIONS] <COMMAND>

Commands:
  ai       Send a question to the local HERO assistant
  keys     Store API keys in KWallet
  setup    Apply a first-boot profile and mascot
  doctor   Check the system and report critical failures
  install  Install optional development tools for the current user
  box      Create rootless Distrobox environments with Podman
  docker   Install and configure Docker CE rootless
  game-mode Control per-user Game Mode
  up       Start current project Compose services
  down     Stop current project Compose services
  logs     Show current project Compose logs
  report   Create a sanitized diagnostic report
  completions Generate shell completion script
  update   Download and queue a bootc update
  rollback Queue the previous deployment for next boot

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

## `forja ai`

`forja ai "<question>" [--json]` sends the question to HERO over the session D-Bus. Conversation replies use local Ollama with Qwen3 8B or 4B based on free VRAM and Game Mode, and keep the model loaded for up to five minutes. System actions are refused until the action catalog and Policy Engine are available.

## Official installer documentation

- [Install Unity Hub on Linux](https://docs.unity.com/en-us/hub/install-hub-linux)
- [Install Claude Code](https://code.claude.com/docs/en/getting-started)
- [Install Homebrew on Linux](https://docs.brew.sh/Homebrew-on-Linux)
- [VS Code for Linux](https://code.visualstudio.com/docs/setup/linux)
- [Dev Containers CLI](https://github.com/devcontainers/cli)

## `forja install`

```text
Install optional development tools for the current user

Usage: forja install [OPTIONS] <COMMAND>

Commands:
  unity        Download the official Unity Hub AppImage into ~/.local
  claude-code  Install Claude Code with Anthropic's official installer
  homebrew              Install Homebrew in the user's directory
  devcontainers         Install the official Dev Containers CLI for the user
  vscode-devcontainers  Install VS Code and the Dev Containers extension for the user

Options:
      --lang <LANG>  Help language: pt-br or en [default: en] [possible values: pt-br, en]
  -h, --help         Print help
```

## `forja box`

`forja box create ubuntu|arch|fedora [--name <NAME>]` creates and enters a rootless Podman Distrobox. With `--json`, it creates the container without entering and returns the enter command as JSON.

## `forja game-mode`

`forja game-mode on|off|status [--json]` controls per-user Game Mode. Starting Steam or gamescope also activates `hero-game.target` automatically; exiting stops it. `on` holds the mode manually. `off` suppresses automatic reactivation until the current game exits.

While active, the target requests the `performance` power profile and Plasma Do Not Disturb. If the hardware does not offer that profile or the notification service is unavailable, the target remains active and logs the limitation. HERO/Memory integration and FPS measurements belong to F4-004.

## `forja docker`

`forja docker install` asks for confirmation, configures the official source and installs Docker CE via `rpm-ostree`; a reboot is required. Then `forja docker setup-rootless` configures the user service without enabling the privileged daemon.

## Compose and reports

`forja up`, `forja down` and `forja logs` use `podman compose` and look for `compose.yaml`, `compose.yml`, `docker-compose.yaml` or `docker-compose.yml` in the current directory. `up` starts services in the background. Each command accepts `--json`, returning only status and exit code.

`forja report [--json]` collects the same checks as `doctor` and prints a report without environment variables or personal paths. Review the details before attaching it to an issue.

`forja completions bash|zsh|fish` prints a completion script for the selected shell. The image installs all three scripts in the standard Bash, Zsh and Fish directories.

`forja update` downloads and queues a bootc update; `forja rollback` queues the previous deployment for the next boot and discards a staged update, if present. Both show the route and context and ask for `[s/N]` confirmation; `--yes` confirms explicitly and `--json` returns only the result.

The `ai`, `mascot` and `memory` commands depend on HERO and Memory backends that are not available in this stage.

## Optional VS Code installation

`forja install vscode-devcontainers` installs Homebrew, Node.js, Dev Containers CLI, official VS Code and the extension for the current user. Confirmation is required (`--yes` for automation); proprietary VS Code is not included in the image.

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

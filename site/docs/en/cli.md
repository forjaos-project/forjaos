# forja CLI — English

Output generated from the `forja` binary using `--help`.

## `forja`

```text
forja 0.1.0
ForjaOS: diagnostics, installation, and assistant in one command

Usage: forja [OPTIONS] <COMMAND>

Commands:
  ai       Send a question to the local HERO assistant
  memory   Search and maintain the local ForjaOS vault
  mascot   Configure the HERO mascot name, voice, and training
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

`forja ai "<question>" [--json]` sends the question and current directory to HERO over the session D-Bus. Conversation uses local Ollama with Qwen3 8B or 4B based on free VRAM and Game Mode. `alter` actions show the route/context and prompt `[y/N]`; `blocked` actions are refused. In JSON mode, a pending confirmation returns an ID that can be approved with `forja ai --confirm <id>`.

## `forja memory`

- `forja memory search "<terms>" [--limit N] [--json]`
- `forja memory timeline [--days N] [--limit N] [--json]`
- `forja memory remember "<note>" [--json]`
- `forja memory rebuild [--json]`
- `forja memory viewer [--json]` opens the local QML viewer.
- `forja memory graph [path] [--json]` builds a code graph with the bundled local Graphify AST runtime; the `code` collector must be enabled, and the result is merged into the Memory graph.
- `forja memory mcp` starts the stdio MCP transport for registration in a compatible client.
- `forja memory collectors status|enable <source>|disable <source>` lists or changes `shell`, `git`, `hero`, `windows`, `code`, and `notes`. `windows`, `code`, and `notes` are disabled by default. The `windows` collector records only the active window's application and title every 30 seconds, without window contents or screenshots. `notes` indexes Markdown under `vault/notes/`; `code` only builds a graph when `forja memory graph` runs and does not send code to remote models.
- `forja memory retention <source> <days>` sets retention; `0` means unlimited. `forja memory purge` applies the configured retention.
- `forja memory collect shell|git [--json]` reads a command from stdin or records the current commit; `--json` emits the structured result. First boot installs the shell hook; run `forja memory hook install` in each Git repo to install its `post-commit` hook. Existing hooks are preserved.
- `forja memory git register [path]` explicitly adds a repo to the daily scan, starting at its current HEAD. `unregister <path>` removes a repo. `forja memory git scan [--json]` runs a manual scan, and a user timer repeats it daily. Disabling the Git collector advances cursors to the current HEAD, skipping the disabled period.

Events store the command/commit, directory, exit code, and duration; known secret patterns are redacted before writing. Set `FORJA_MEMORY_COLLECTOR=0` in the shell to skip commands in that session. The viewer's Collectors menu controls every available source. Enabling or disabling `notes` rebuilds the index without deleting files.

## `forja mascot`

- `forja mascot status [--json]` shows the configured name and whether local wake word and voice files are installed.
- `forja mascot name "Guará" [--json]` changes the name in `~/.config/hero/persona.toml`.
- `forja mascot voice <id> [--json]` selects an installed Piper voice with `<id>.onnx` and `<id>.onnx.json` in `~/.local/share/hero/voices/`.
- `forja mascot voices list [--json]` lists the curated Cadu and Jeff Brazilian Portuguese voices and their install status. `forja mascot voices download <id> [--json]` downloads an immutable revision and verifies file sizes and SHA-256 before installation. CC0 was verified for these voices and their training bases in Piper's [official commercial-use list](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/COMMERCIAL_USE.md).
- `forja mascot train "Name" [--json]` queues the local trainer as a transient user service; if the trainer is not installed, it reports that no training was started. Follow progress with `journalctl --user -u forja-wakeword-train.service`.

These commands use `memd` over the session D-Bus. The vault lives in
`~/ForjaOS/vault/`; its FTS5 index is derived and can be rebuilt from Markdown.

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

`forja completions bash|zsh|fish` prints a completion script for the selected shell. With `--json`, it returns the script in the `script` field. The image installs all three scripts in the standard Bash, Zsh and Fish directories.

`forja update` downloads and queues a bootc update; `forja rollback` queues the previous deployment for the next boot and discards a staged update, if present. Both show the route and context and ask for `[s/N]` confirmation; `--yes` confirms explicitly and `--json` returns only the result.

`ai` and `memory` use the local HERO and Memory services. The `mascot` interface writes local preferences; wake word training and speech synthesis depend on models and services not yet included.

## `forja keys`

- `forja keys set <provider>` prompts without echo and stores the key in KWallet through Secret Service.
- `eval "$(forja keys env --shell bash)"` loads configured keys only into the current Bash shell. Use `--shell zsh` for Zsh or `eval (forja keys env --shell fish)` for Fish.
- `forja keys env --json` reports configured provider names only; it never emits secret values.
- `forja keys ssh-add` prompts through KWallet and loads SSH keys into the user agent.

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

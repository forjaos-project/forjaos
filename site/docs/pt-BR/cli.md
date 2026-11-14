# forja CLI — pt-BR

Saída gerada pelo binário `forja` a partir de `--help`.

## `forja`

```text
forja 0.1.0
ForjaOS: diagnóstico, instalação e assistente em um comando

Uso: forja [OPÇÕES] <COMANDO>

Comandos:
  doctor   Verifica o sistema (kernel, GPU, Docker, Git, IA, serviços, portas) e sai com código ≠ 0 se algo crítico falhar
  install  Instala ferramentas de desenvolvimento no espaço do usuário

Opções:
      --lang <LANG>  Idioma da ajuda: pt-br ou en [default: pt-br] [possible values: pt-br, en]
  -h, --help         Exibe ajuda
  -V, --version      Exibe a versão
```

## `forja doctor`

```text
Verifica o sistema (kernel, GPU, Docker, Git, IA, serviços, portas) e sai com código ≠ 0 se algo crítico falhar

Uso: forja doctor [OPÇÕES]

Opções:
      --json  Saída em JSON para scripts
  -h, --help  Exibe ajuda
```

## Fontes oficiais dos instaladores

- [Instalação do Unity Hub para Linux](https://docs.unity.com/en-us/hub/install-hub-linux)
- [Instalação do Claude Code](https://code.claude.com/docs/en/getting-started)

## `forja install`

```text
Instala ferramentas de desenvolvimento no espaço do usuário

Uso: forja install <COMANDO>

Comandos:
  unity        Baixa o Unity Hub oficial como AppImage em ~/.local
  claude-code  Instala Claude Code pelo instalador oficial da Anthropic

Opções:
  -h, --help  Exibe ajuda
```

## `forja install unity`

```text
Baixa o Unity Hub oficial como AppImage em ~/.local

Uso: forja install unity [OPÇÕES]

Opções:
  -y, --yes   Confirma a instalação sem interação
      --json  Emite somente o resultado estruturado em JSON
  -h, --help  Exibe ajuda
```

## `forja install claude-code`

```text
Instala Claude Code pelo instalador oficial da Anthropic

Uso: forja install claude-code [OPÇÕES]

Opções:
  -y, --yes   Confirma a instalação sem interação
      --json  Emite somente o resultado estruturado em JSON
  -h, --help  Exibe ajuda
```

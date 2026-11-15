# forja CLI — pt-BR

Saída gerada pelo binário `forja` a partir de `--help`.

## `forja`

```text
forja 0.1.0
ForjaOS: diagnóstico, instalação e assistente em um comando

Uso: forja [OPÇÕES] <COMANDO>

Comandos:
  ai       Envia uma pergunta ao assistente local HERO
  keys     Gerencia chaves de API no KWallet
  setup    Aplica um perfil de primeiro boot e o nome do mascote
  doctor   Verifica o sistema (kernel, GPU, Docker, Git, IA, serviços, portas) e sai com código ≠ 0 se algo crítico falhar
  install  Instala ferramentas de desenvolvimento no espaço do usuário
  box      Cria ambientes Distrobox rootless usando Podman
  docker   Instala e configura Docker CE em modo rootless
  game-mode Controla o Modo Jogo do usuário
  up       Inicia os serviços Compose do projeto atual
  down     Para os serviços Compose do projeto atual
  logs     Exibe os logs Compose do projeto atual
  report   Gera um relatório de diagnóstico sanitizado
  completions Gera script de completion do shell
  update   Baixa e prepara a atualização bootc
  rollback Agenda a implantação anterior para o próximo boot

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

## `forja ai`

`forja ai "<pergunta>" [--json]` envia a pergunta ao HERO pela sessão D-Bus. Respostas de conversa usam Ollama local, Qwen3 8B ou 4B conforme VRAM livre e Modo Jogo, e mantêm o modelo por até cinco minutos. Ações de sistema ainda são recusadas enquanto o catálogo e o Policy Engine não estiverem disponíveis.

## Fontes oficiais dos instaladores

- [Instalação do Unity Hub para Linux](https://docs.unity.com/en-us/hub/install-hub-linux)
- [Instalação do Claude Code](https://code.claude.com/docs/en/getting-started)
- [Instalação do Homebrew no Linux](https://docs.brew.sh/Homebrew-on-Linux)
- [Documentação do VS Code para Linux](https://code.visualstudio.com/docs/setup/linux)
- [Dev Containers CLI](https://github.com/devcontainers/cli)

## `forja install`

```text
Instala ferramentas de desenvolvimento no espaço do usuário

Uso: forja install <COMANDO>

Comandos:
  unity        Baixa o Unity Hub oficial como AppImage em ~/.local
  claude-code  Instala Claude Code pelo instalador oficial da Anthropic
  homebrew              Instala Homebrew no diretório do usuário
  devcontainers         Instala o CLI oficial Dev Containers no usuário
  vscode-devcontainers  Instala VS Code e a extensão Dev Containers para o usuário

Opções:
  -h, --help  Exibe ajuda
```

## `forja box`

`forja box create ubuntu|arch|fedora [--name <NOME>]` cria uma Distrobox rootless usando Podman e entra no ambiente. Com `--json`, cria sem entrar e retorna o comando de entrada em JSON.

## `forja game-mode`

`forja game-mode on|off|status [--json]` controla o Modo Jogo do usuário. O início de Steam ou gamescope também ativa automaticamente `hero-game.target`; ao sair, o modo desliga. `on` mantém o modo ativo manualmente. `off` impede a reativação automática até o jogo atual sair.

O alvo solicita o perfil de energia `performance` e Não perturbe no Plasma enquanto está ativo. Se o hardware não oferecer esse perfil ou o serviço de notificações não estiver disponível, o alvo continua ativo e registra a limitação no journal. A integração com HERO/Memória e a medição de FPS pertencem a F4-004.

## `forja docker`

`forja docker install` solicita confirmação, configura a fonte oficial e instala Docker CE via `rpm-ostree`; exige reinicialização. Depois, `forja docker setup-rootless` configura o serviço do usuário sem ativar o daemon privilegiado.

## Compose e relatório

`forja up`, `forja down` e `forja logs` usam `podman compose` e procuram um dos arquivos `compose.yaml`, `compose.yml`, `docker-compose.yaml` ou `docker-compose.yml` no diretório atual. `up` inicia os serviços em segundo plano. Cada comando aceita `--json`, que retorna apenas status e código de saída.

`forja report [--json]` coleta as mesmas verificações do `doctor` e mostra um relatório sem variáveis de ambiente ou caminhos pessoais. Revise os detalhes antes de anexar a uma issue.

`forja completions bash|zsh|fish` imprime o script de completion para o shell indicado. A imagem instala os três scripts nos diretórios padrão de Bash, Zsh e Fish.

`forja update` baixa e prepara uma atualização bootc; `forja rollback` agenda a implantação anterior para o próximo boot e descarta uma atualização staged, se houver. Ambos mostram rota e contexto e pedem confirmação `[s/N]`; `--yes` confirma explicitamente e `--json` retorna somente o resultado.

Os comandos `ai`, `mascot` e `memory` dependem dos backends HERO e Memória que ainda não estão disponíveis nesta etapa.

## Instalação opcional de VS Code

`forja install vscode-devcontainers` instala Homebrew, Node.js, Dev Containers CLI, VS Code oficial e a extensão Dev Containers para o usuário atual. A instalação requer confirmação (`--yes` para automação); o VS Code proprietário não é incluído na imagem.

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

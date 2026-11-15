# forja CLI — pt-BR

Saída gerada pelo binário `forja` a partir de `--help`.

## `forja`

```text
forja 0.1.0
ForjaOS: diagnóstico, instalação e assistente em um comando

Uso: forja [OPÇÕES] <COMANDO>

Comandos:
  ai       Envia uma pergunta ao assistente local HERO
  memory   Busca e mantém o vault local ForjaOS
  mascot   Configura nome, voz e treino do mascote HERO
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

`forja ai "<pergunta>" [--json]` envia a pergunta e o diretório atual ao HERO pela sessão D-Bus. Conversa usa Ollama local, Qwen3 8B ou 4B conforme VRAM livre e Modo Jogo. Ações `alterar` mostram rota/contexto e pedem `[s/N]`; ações `bloqueado` são recusadas. Em modo JSON, uma confirmação pendente devolve um identificador que pode ser aprovado com `forja ai --confirm <id>`.

## `forja memory`

- `forja memory search "<termos>" [--limit N] [--json]`
- `forja memory timeline [--days N] [--limit N] [--json]`
- `forja memory remember "<nota>" [--json]`
- `forja memory rebuild [--json]`
- `forja memory viewer [--json]` abre o visualizador local QML em modo somente leitura.
- `forja memory mcp` inicia o transporte MCP por stdio para registro em clientes compatíveis.
- `forja memory collectors status|enable <origem>|disable <origem>` consulta ou altera os coletores disponíveis (`shell`, `git`, `hero`, `windows`). O coletor `windows` é opcional e registra somente aplicativo e título da janela ativa a cada 30 segundos, sem conteúdo nem captura de tela.
- `forja memory retention <origem> <dias>` define retenção; `0` significa indefinida. `forja memory purge` aplica as retenções.
- `forja memory collect shell` lê o comando do stdin; `forja memory collect git` registra o commit atual. O shell recebe hook no primeiro boot; em cada repo Git, execute `forja memory hook install` para registrar `post-commit`. Um hook existente é preservado.
- `forja memory git register [caminho]` inclui explicitamente um repo na varredura diária; ela começa no HEAD atual. `unregister <caminho>` remove um repo. `forja memory git scan [--json]` executa a varredura manual, e um timer de usuário a repete diariamente. Desativar o coletor Git avança os cursores para o HEAD atual, sem buscar o período desativado.

Os eventos guardam comando/commit, diretório, código de saída e duração; padrões conhecidos de segredos são redigidos antes da gravação. Defina `FORJA_MEMORY_COLLECTOR=0` no shell para não registrar comandos daquela sessão. Para habilitar o plugin de janelas do KWin, use `forja memory collectors enable windows`; a configuração é recarregada na sessão ativa quando possível. Coletores de código e notas ainda não estão disponíveis.

## `forja mascot`

- `forja mascot status [--json]` mostra o nome configurado e se os arquivos locais de wake word e voz estão instalados.
- `forja mascot name "Guará" [--json]` altera o nome salvo em `~/.config/hero/persona.toml`.
- `forja mascot voice <id> [--json]` seleciona uma voz Piper cujos arquivos `<id>.onnx` e `<id>.onnx.json` já estejam em `~/.local/share/hero/voices/`.
- `forja mascot train "Nome" [--json]` enfileira o treinador local como serviço transitório do usuário; se o treinador não estiver instalado, informa que nenhum treino foi iniciado. Acompanhe a execução com `journalctl --user -u forja-wakeword-train.service`.

Os comandos usam `memd` pela sessão D-Bus. O vault fica em `~/ForjaOS/vault/`;
o índice FTS5 é derivável e pode ser reconstruído a partir dos arquivos Markdown.

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

`ai` e `memory` usam os serviços locais HERO e Memória. A interface `mascot` grava preferências locais; treino de wake word e síntese de voz dependem dos respectivos modelos e serviços ainda não incluídos.

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

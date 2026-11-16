# Servidores MCP locais do HERO

O pacote `hero-mcp` compila três executáveis MCP independentes em Rust com `rmcp` 3.10 e transporte stdio: `hero-system`, `hero-desktop` e `hero-dev`. Eles não abrem portas de rede. Cada ferramenta informa o tier na descrição MCP e está listada com schema em `manifests/*.json`; o container instala os executáveis em `/usr/libexec/forjaos/` e os manifestos em `/usr/share/forjaos/mcp-manifests/`.

`hero-system` oferece consultas de serviços, journald, firewall, sensores, rede e Ollama, além das ações declaradas no PRD. `firewall.toggle_zone` sempre recusa. `hero-desktop` expõe janelas, notificações, Modo Não Perturbe, mídia, clipboard, captura com aviso, apps e URLs. `hero-dev` limita operações a projetos cadastrados em `~/.config/hero/projects.toml` ou detectados sob `~/proj`, `~/dev` e `~/code`.

Formato de cadastro explícito:

```toml
[[projects]]
name = "forjaos"
path = "/home/usuario/dev/forjaos"
```

Com `hero-dev`, Git, Compose e testes recebem o nome do projeto, nunca um caminho arbitrário. Compose aceita apenas `podman` ou `docker`; os arquivos precisam estar na raiz conhecida. `git.commit` inclui somente conteúdo já staged. Saídas de teste não são devolvidas ao cliente.

Todas as ferramentas que alteram estado estão anotadas como `alterar` e indicam ao cliente MCP que solicite aprovação. Isso eleva algumas ferramentas originalmente `livre` no PRD, conforme `hero-mcp/AGENTS.md`, que proíbe efeitos colaterais no tier livre. A implementação de `terminal.spawn_agent` retorna bloqueio e não inicia um agente autônomo.

Build local:

```sh
cargo build --locked --release --manifest-path hero-mcp/Cargo.toml --bins
```

O build da imagem passou localmente. `mcp-inspector` confirmou o handshake stdio e os catálogos dos três executáveis; os schemas e tiers coincidem com `manifests/*.json`. A validação de chamadas de ação e em hardware continua no build final local.

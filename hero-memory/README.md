# Memória ForjaOS

`memd` é um serviço da sessão do usuário. O vault Markdown compatível com
Obsidian e Logseq fica em `~/ForjaOS/vault/`; o índice reconstruível fica em
`~/.local/share/hero/memory.db` (ou em `$XDG_DATA_HOME/hero/memory.db`).

O serviço publica `org.forjaos.Memory` no D-Bus da sessão:

- `Search(query, limit) -> JSON`
- `Timeline(days, limit) -> JSON`
- `Rebuild() -> JSON`
- `Remember(note) -> JSON`
- `Collectors()`, `SetCollector(source, enabled)`, `SetRetention(source, days)`
- `CollectEvent(source, detail, cwd, exit_code, duration_ms)`,
  `CollectWindow(app, title)`, `Purge()`

O transporte MCP por stdio está disponível em `forja memory mcp`. Ele expõe
`memory_search`, `memory_timeline`, `memory_related`, `memory_remember` e
`memory_forget`. O último remove permanentemente uma nota Markdown pelo ID
relativo do vault e rejeita caminho absoluto, traversal e symlink.

O índice usa FTS5 e `sqlite-vec` com embeddings locais via Ollama quando
`nomic-embed-text:latest` estiver instalado. A reconstrução percorre apenas arquivos Markdown,
ignora diretórios ocultos e links simbólicos, redige padrões comuns de segredos
antes da indexação e exporta `graph/graph.json` no formato de nós e links do
Graphify. O vault e o banco recebem permissões restritas ao usuário.

O serviço não baixa modelos automaticamente. Sem `nomic-embed-text`, as buscas
continuam funcionando por FTS5 e `forja memory rebuild` informa esse estado.

Comandos disponíveis pela CLI incluem `search`, `timeline`, `remember`,
`rebuild`, `viewer`, `collectors`, `retention`, `purge`, `graph <repo>` e
`git register|unregister|scan`. `forja memory graph <repo>` exige o coletor
`code` ativo e chama o executável Graphify com `--code-only --no-viz`, sem
envio do código a um modelo remoto. O coletor só aparece como disponível se o
pacote oficial [`graphifyy`](https://github.com/Graphify-Labs/graphify) estiver
instalado no usuário com uv. O resultado fica isolado em `vault/graph/code/` e
não é mesclado ao grafo de notas.

Os coletores shell e HERO são automáticos. O Git oferece hook post-commit e
varredura diária somente nos repositórios cadastrados com `forja memory git
register`; o registro começa no HEAD atual e não importa histórico anterior.
Use `unregister` para remover um repo. Ao desativar o coletor Git, os cursores
avançam ao HEAD atual para não coletar o período desativado. A configuração fica
em `~/.config/hero/memory.toml`; shell, Git e HERO começam ativos, enquanto
janelas, código e notas começam desativados. O coletor de janelas está
disponível como plugin de script do KWin e registra somente aplicativo,
título e intervalo de 30 segundos, sem conteúdo ou captura de tela. Ative
ou desative com `forja memory collectors enable|disable windows`; a
configuração do KWin é recarregada na sessão ativa quando possível. O coletor
`notes`, desligado por padrão, inclui no índice apenas Markdown em
`vault/notes/`; ativar ou desativar reconstrói o índice, sem remover arquivos.
O coletor `code`, também desligado por padrão, executa a análise por comando e
requer a raiz Git do repositório. Todos os toggles aparecem no menu Coletores
do visualizador; `code` fica desabilitado quando Graphify não está instalado.
O purge remove arquivos de eventos antigos pelas retenções configuradas.
Defina `FORJA_MEMORY_COLLECTOR=0` em uma sessão shell para ignorar comandos
daquela sessão.

O grafo de notas e eventos distingue comandos, commits, conversas, janelas,
repositórios e notas, e liga eventos da mesma janela de 15 minutos. O
visualizador usa arranjo radial com zoom, pan e filtros por tipo e período;
faltam layout força-dirigida, medir desempenho e atualizar o grafo
incrementalmente após cada evento. Grafos Graphify de código ainda ficam em
arquivos separados.

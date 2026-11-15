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
- `CollectEvent(source, detail, cwd, exit_code, duration_ms)`, `Purge()`

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
`rebuild`, `viewer`, `collectors`, `retention`, `purge` e `git
register|unregister|scan`. O visualizador QML abre timeline, grafo e busca local
em modo somente leitura.

Os coletores shell e HERO são automáticos. O Git oferece hook post-commit e
varredura diária somente nos repositórios cadastrados com `forja memory git
register`; o registro começa no HEAD atual e não importa histórico anterior.
Use `unregister` para remover um repo. Ao desativar o coletor Git, os cursores
avançam ao HEAD atual para não coletar o período desativado. A configuração fica
em `~/.config/hero/memory.toml`; shell, Git e HERO começam ativos, enquanto
janelas, código e notas ficam desativados e indisponíveis nesta versão. O purge
remove arquivos de eventos antigos pelas retenções configuradas.
Defina `FORJA_MEMORY_COLLECTOR=0` em uma sessão shell para ignorar comandos
daquela sessão.

O grafo usa um arranjo radial estático; faltam layout força-dirigida,
zoom/filtros, medição de desempenho, coletores de janelas/código/notas e
atualização incremental do grafo após cada evento.

# Memória ForjaOS

`memd` é um serviço da sessão do usuário. O vault Markdown compatível com
Obsidian e Logseq fica em `~/ForjaOS/vault/`; o índice reconstruível fica em
`~/.local/share/hero/memory.db` (ou em `$XDG_DATA_HOME/hero/memory.db`).

O serviço publica `org.forjaos.Memory` no D-Bus da sessão:

- `Search(query, limit) -> JSON`
- `Timeline(days, limit) -> JSON`
- `Rebuild() -> JSON`
- `Remember(note) -> JSON`

O índice usa FTS5 e `sqlite-vec` com embeddings locais via Ollama quando
`nomic-embed-text:latest` estiver instalado. A reconstrução percorre apenas arquivos Markdown,
ignora diretórios ocultos e links simbólicos, redige padrões comuns de segredos
antes da indexação e exporta `graph/graph.json` no formato de nós e links do
Graphify. O vault e o banco recebem permissões restritas ao usuário.

O serviço não baixa modelos automaticamente. Sem `nomic-embed-text`, as buscas
continuam funcionando por FTS5 e `forja memory rebuild` informa esse estado.

Comandos disponíveis pela CLI: `forja memory search`, `timeline`, `remember` e
`rebuild`. Os coletores automáticos, retenção e visualizador ainda não estão
ligados a este serviço.

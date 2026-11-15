# Serviço D-Bus do HERO

O daemon de sessão `herod` publica `org.forjaos.Hero` no barramento D-Bus do usuário, no objeto `/org/forjaos/Hero`.

## API atual

- Propriedade `State` (`s`): estado atual em português, conforme FR-071.
- Método `AskText(s) -> s`: recebe uma pergunta e retorna JSON com `status`, `route`, `context`, `tier`, `requires_confirmation`, `answer` e, quando disponível, `model`. A rota de conversa usa somente o Ollama em `127.0.0.1`; pedidos de ação são recusados enquanto o catálogo e o Policy Engine não estão prontos.
- Sinal `StateChanged(s)`: emitido depois de cada transição válida.

Estados aceitos: `desligado`, `ocioso`, `escutando`, `gravando`, `transcrevendo`, `pensando`, `falando`, `erro`. A transição inicia em `ocioso`. O chat inicia `ollama.service` sob demanda, fora do cgroup limitado de `herod`. Usa Qwen3 8B quando há pelo menos 6 GiB livres e Modo Jogo está desligado; caso contrário usa Qwen3 4B. Ollama recebe `keep_alive=5m` e a chamada expira em 60 segundos.

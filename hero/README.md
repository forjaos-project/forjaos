# Serviço D-Bus do HERO

O daemon de sessão `herod` publica `org.forjaos.Hero` no barramento D-Bus do usuário, no objeto `/org/forjaos/Hero`.

## API atual

- Propriedade `State` (`s`): estado atual em português, conforme FR-071.
- `org.freedesktop.DBus.Properties.PropertiesChanged`: notifica clientes de cada mudança na propriedade `State`.
- Sinal `StateChanged(s)`: publica o novo estado depois de cada transição válida.
- Socket Unix `$XDG_RUNTIME_DIR/forjaos/herod.sock`: endpoint local somente leitura. Ao conectar, envia uma linha JSON `{"state":"ocioso"}` com o estado atual. O diretório tem permissão `0700` e o socket `0600`.
- Método `AskText(s, s, s) -> s`: recebe pergunta, diretório atual e JSON `SnapshotDoApp`; retorna JSON com `status`, `route`, `context`, `tier`, `requires_confirmation`, `answer` e, quando disponível, `model`. A classificação usa regras e Qwen3 4B local; indisponibilidade do classificador seleciona `conversa-de-voz` local.
- Método `RouteProviders() -> s` lista os provedores configurados em JSON. `SetRouteProvider(s, s, s) -> s` atualiza rota, provedor e modelo em `~/.config/hero/routes.toml`; as rotas `conversa-de-voz` e `sistema` recusam qualquer provedor cloud.
- Métodos `Persona() -> s` e `SetPersonaInstructions(s) -> s` leem e atualizam as instruções editáveis em `~/.config/hero/persona.toml`. As instruções fixas de segurança são acrescentadas pelo daemon e não podem ser substituídas.
- Histórico das dez trocas mais recentes fica apenas em memória e desaparece ao encerrar `herod`. Chaves de provedores cloud são lidas do KWallet via Secret Service; não há fallback automático entre provedores.
- Método `ConfirmAction(s, b) -> s`: consome um identificador aleatório de confirmação, válido por 120 segundos e para uma única ação. A aprovação é aplicada pelo HERO e gera `AuditEvent` sem texto da pergunta.

Estados aceitos: `desligado`, `ocioso`, `escutando`, `gravando`, `transcrevendo`, `pensando`, `falando`, `erro`. A transição inicia em `ocioso`. A unit `herod.service` limita o daemon a 400 MiB, 50% de CPU e prioridade `Nice=5`; Ollama roda fora do cgroup do daemon. O turno de texto tem limite de 58 segundos, erros do provedor são sanitizados e não há fallback automático. Subprocessos de ação são cancelados com até 55 segundos. A integração de áudio e wake word pertence à Fase 4.

Exemplo de rota cloud opt-in:

```toml
[routes."pesquisa"]
provider = "openrouter"
model = "openrouter/auto-code"
```

Os outros provedores aceitos são `ollama`, `anthropic`, `openai` e `nous`. Provedores cloud precisam de `model` e da chave correspondente salva por `forja keys set <provedor>`. A configuração usa endpoints oficiais fixos; o usuário não pode apontar o daemon para um host arbitrário.

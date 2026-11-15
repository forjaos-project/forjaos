# Serviço D-Bus do HERO

O daemon de sessão `herod` publica `org.forjaos.Hero` no barramento D-Bus do usuário, no objeto `/org/forjaos/Hero`.

## API atual

- Propriedade `State` (`s`): estado atual em português, conforme FR-071.
- `org.freedesktop.DBus.Properties.PropertiesChanged`: notifica clientes de cada mudança na propriedade `State`.
- Sinal `StateChanged(s)`: publica o novo estado depois de cada transição válida.
- Socket Unix `$XDG_RUNTIME_DIR/forjaos/herod.sock`: endpoint local somente leitura. Ao conectar, envia uma linha JSON `{"state":"ocioso"}` com o estado atual. O diretório tem permissão `0700` e o socket `0600`.
- Método `AskText(s, s) -> s`: recebe pergunta e diretório atual; retorna JSON com `status`, `route`, `context`, `tier`, `requires_confirmation`, `answer` e, quando disponível, `model`. Conversa usa Ollama em loopback; ações passam pelo catálogo e Policy Engine.
- Método `ConfirmAction(s, b) -> s`: consome um identificador aleatório de confirmação, válido por 120 segundos e para uma única ação. A aprovação é aplicada pelo HERO e gera `AuditEvent` sem texto da pergunta.

Estados aceitos: `desligado`, `ocioso`, `escutando`, `gravando`, `transcrevendo`, `pensando`, `falando`, `erro`. A transição inicia em `ocioso`. A unit `herod.service` limita o daemon a 400 MiB, 50% de CPU e prioridade `Nice=5`; Ollama roda fora do cgroup do daemon. O turno de texto tem limite de 58 segundos e retorna uma mensagem local quando Ollama falha ou não responde. Subprocessos de ação são cancelados com até 55 segundos. A integração de áudio e wake word pertence à Fase 4.

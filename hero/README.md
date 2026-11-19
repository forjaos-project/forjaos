# Serviço D-Bus do HERO

O daemon de sessão `herod` publica `org.forjaos.Hero` no barramento D-Bus do usuário, no objeto `/org/forjaos/Hero`.

## API atual

- Propriedade `State` (`s`): estado atual em português, conforme FR-071.
- Propriedade `MicrophoneEnabled` (`b`, gravável): permissão local de captura do HERO. Inicia desligada, persiste em `~/.config/hero/microphone.state` com permissão privada e falha para desligado se o estado salvo for inválido. Mudanças geram `PropertiesChanged` e `AuditEvent` com gatilho `microphone`.
- `org.freedesktop.DBus.Properties.PropertiesChanged`: notifica clientes de cada mudança na propriedade `State`.
- Sinal `StateChanged(s)`: publica o novo estado depois de cada transição válida.
- Socket Unix `$XDG_RUNTIME_DIR/forjaos/herod.sock`: endpoint local somente leitura. Ao conectar, envia uma linha JSON `{"state":"ocioso"}` com o estado atual. O diretório tem permissão `0700` e o socket `0600`.
- Método `AskText(s, s, s) -> s`: recebe pergunta, diretório atual e JSON `SnapshotDoApp`; retorna JSON com `status`, `route`, `context`, `tier`, `requires_confirmation`, `answer` e, quando disponível, `model`; respostas de ação incluem também `tool`. A classificação usa regras e Qwen3 4B local; indisponibilidade do classificador seleciona `conversa-de-voz` local.
- `StartPushToTalk() -> s`, `StopPushToTalk() -> s` e `TogglePushToTalk() -> s`: controlam a captura mono PCM 16 kHz pelo nó `forjaos.hero.microphone` do PipeWire. `VoiceTranscribed(s)` inicia um turno na rota local `conversa-de-voz`; `VoiceAnswer(s)` entrega a resposta ao overlay e ao atalho global `Super+Shift+M`, e a voz Piper selecionada é reproduzida pelo `hero-speak`. Falhas de STT/LLM entregam uma frase fixa em `VoiceAnswer`; `VoiceFailed(s)` sinaliza falha de captura ou TTS, e `VoiceIgnored(s)` sinaliza gatilho ocupado. O áudio fica em memória por no máximo 30 s e é descartado após a transcrição; mutar o microfone cancela captura ou STT ativos. Durante a fala, outro PTT cancela a reprodução e inicia um novo turno.
- Método `RouteProviders() -> s` lista os provedores configurados em JSON. `SetRouteProvider(s, s, s) -> s` atualiza rota, provedor e modelo em `~/.config/hero/routes.toml`; as rotas `conversa-de-voz` e `sistema` recusam qualquer provedor cloud.
- Métodos `Persona() -> s` e `SetPersonaInstructions(s) -> s` leem e atualizam as instruções editáveis em `~/.config/hero/persona.toml`. As instruções fixas de segurança são acrescentadas pelo daemon e não podem ser substituídas.
- Métodos `ToolTiers() -> s` e `SetToolTier(s, s) -> s` listam tiers mínimo/efetivo do manifesto `tool-policy.toml` e permitem somente elevar o tier efetivo; overrides ficam em `~/.config/hero/policy.toml`.
- Método `SaveRoutine(s, s, s) -> s` recebe ID, JSON com IDs das ferramentas e tier máximo permitido; só persiste em `~/.config/hero/routines.toml` após validar cada ferramenta, recusando rotinas acima do limite ou com ferramentas bloqueadas.
- Histórico das dez trocas mais recentes fica apenas em memória e desaparece ao encerrar `herod`. Chaves de provedores cloud são lidas do KWallet via Secret Service; não há fallback automático entre provedores.
- Método `ConfirmAction(s, b) -> s`: consome um identificador aleatório de confirmação, válido por 120 segundos e para uma única ação. A aprovação é aplicada pelo HERO e gera `AuditEvent` JSON no journald (`SYSLOG_IDENTIFIER=hero-audit`) com timestamp, gatilho, rota, ferramenta, tier, decisão e duração, sem áudio nem texto da pergunta.

## Catálogo, delegação e diagnóstico

`hero/tool-policy.toml` espelha os tiers dos três manifestos MCP. O verificador `python3 scripts/check_hero_catalog.py` exige que as 49 ferramentas tenham schema e tier válido, e rejeita tier local abaixo do MCP. Os aliases exclusivos do `herod` também são declarados nesse arquivo.

A rota `código` reconhece pedidos explícitos para Claude Code, Codex CLI ou Hermes. Depois da confirmação, inicia o CLI no Konsole, usando um projeto Git cadastrado em `~/.config/hero/projects.toml` ou detectado sob `~/proj`, `~/dev` ou `~/code`. Quando há mais de um projeto, o nome citado no pedido ou no título da janela precisa resolver a seleção; sem seleção inequívoca, nada é executado. O diretório é o `cwd` do CLI. Codex inicia com `workspace-write` e aprovações `on-request`; Claude Code e Hermes mantêm a política configurada pelo usuário, sem uma camada adicional de sandbox do HERO. A saída segue ao vivo no terminal e por um FIFO temporário para o HERO devolver o código de saída e as últimas linhas. O FIFO não armazena os dados e é removido ao encerrar. A execução tem limite de 10 minutos. A ferramenta MCP `terminal.spawn_agent` continua bloqueada; essa delegação passa pelo Policy Engine do HERO e exige confirmação.

A rota `saúde-do-sistema` consulta erros do journald das últimas 24 horas, GPU, carga da CPU, memória, estado da rede, firewall, auditd, portas TCP em escuta, espaço em disco e sensores térmicos. Cada fonte indisponível aparece como indisponível, sem ser convertida em um valor normal.

Estados aceitos: `desligado`, `ocioso`, `escutando`, `gravando`, `transcrevendo`, `pensando`, `falando`, `erro`. A transição inicia em `ocioso`. A unit `herod.service` limita o daemon a 400 MiB, 50% de CPU e prioridade `Nice=5`; Ollama roda fora do cgroup do daemon. O turno de conversa textual tem limite de 58 segundos e subprocessos comuns de ação, até 55 segundos. O turno de voz tem limite total de 60 segundos desde o início do PTT; falhas de STT/LLM retornam frase fixa local. A delegação de código tem limite de 10 minutos. Erros do provedor são sanitizados e não há fallback automático. O PTT inicia somente a rota local `conversa-de-voz`; ações por voz e o respectivo fluxo de confirmação ainda não estão ligados. Barge-in via PTT durante TTS está implementado. O overlay só abre quando `org.freedesktop.ScreenSaver.GetActive` confirma a sessão desbloqueada e fecha no sinal `ActiveChanged`; notificações de PTT também são suprimidas sem essa confirmação. Wake word, supressão do próprio TTS, política de ações por voz em tela bloqueada, visemas e medição no Linux de referência ainda faltam.

Exemplo de rota cloud opt-in:

```toml
[routes."pesquisa"]
provider = "openrouter"
model = "openrouter/auto-code"
```

Os outros provedores aceitos são `ollama`, `anthropic`, `openai` e `nous`. Provedores cloud precisam de `model` e da chave correspondente salva por `forja keys set <provedor>`. A configuração usa endpoints oficiais fixos; o usuário não pode apontar o daemon para um host arbitrário.

## Overlay Central de Comando

`overlay/launcher.py` abre `overlay/main.qml` com `Meta+Space`, via `brand/shortcuts/org.forjaos.hero.desktop`. A janela fecha com `Esc`, clique fora ou segundo acionamento do atalho; o processo do overlay termina ao fechar. O histórico de conversa fica somente na memória do processo.

O campo de texto chama `AskText` pelo barramento D-Bus e encaminha o locale como `pt-BR` ou `en-US`; o daemon usa esse valor apenas para selecionar o idioma de resposta. A interface usa o catálogo Qt Linguist em `overlay/i18n/hero-overlay_en.ts`, compilado no build da imagem. Toda ação continua sujeita ao Policy Engine. Quando o daemon retorna `confirmation_required`, a pessoa pode aprovar ou recusar na janela ou na notificação `org.freedesktop.Notifications`.

As métricas de CPU, RAM e rede vêm de `/proc`; estado de rede, Bluetooth, Modo Jogo e firewall é consultado localmente a cada 2 s sem varredura de LAN. O tile de VPN mostra o perfil ativo e permite solicitar sua desconexão pelo Policy Engine. O estado de Não perturbe é lido da propriedade D-Bus `org.freedesktop.Notifications.Inhibited`; a alteração permanece nos controles do Plasma. Containers vêm de `podman ps`/`docker ps`, modelos de `ollama list` e auditoria de eventos locais do journald sem texto do pedido. Latência aparece como “sem teste ativo” e a LAN como “varredura desativada” até existir uma fonte autorizada para esses dados. O firewall não é alterável pelo HERO.

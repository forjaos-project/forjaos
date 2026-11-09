# Tela: Central de Comando HERO — overlay 520 px (canônica)

| Campo | Valor |
| --- | --- |
| Slug | `forjaos_central_de_comando_hero_corrigida` |
| Protótipo | `docs/telas/forjaos_central_de_comando_hero_corrigida/code.html` (sha256 `c0989394c570`) · `screen.png` |
| Requisitos | FR-121, FR-103, FR-093, FR-100 |
| Tema | dark (Cybernetic Forge) |
| Tecnologia-alvo | Overlay QML (Qt Quick + Kirigami) aberto por Super+Espaço, wake word ou clique no plasmoid; processo encerra ao fechar (só o plasmoid fica) |
| Pasta do monorepo | hero/overlay |
| Status | spec |

> Leia `docs/design-system/DESIGN-RULES.md` antes desta spec. Regra de precedência: **layout do protótipo, conteúdo do PRD** (ADR-028). Tokens só de `brand/palette.json` (ADR-027). Se o hash acima não bater com `sha256sum` do `code.html`, a spec está desatualizada — rode `python3 scripts/gen_tela_specs.py` e revise antes de implementar.

## Regiões (layout → copiar)

| Região | Medidas / tokens | FR |
| --- | --- | --- |
| Barra superior | altura 40 px (`dimensions.topbar_height`); fundo `glass-topbar` blur 14 px; borda inferior `rgba(0,229,255,0.12)`; esquerda: logo 20 px + dots de workspace + `Projeto: <repo> · branch <nome>`; centro: data/hora `code-md`; direita: chip HERO (estado), GPU + temperatura, Wi-Fi, BT, [Escudo], bateria | FR-052 |
| Janela Konsole | raio 12 px, borda `border-ghost`, fundo `konsole-bg` (#080b11) sem blur; barra de título 40 px com 3 dots (vermelho/amarelo/verde 12 px) + abas (`forja-term · zsh` ativa com borda ciano 1 px, `claude`, `codex`, `ollama`) `code-md` | FR-035 |
| Saída `forja doctor` | prompt `usuario@forjaos ~/proj/<repo> (main) $`; linhas de check em 2 colunas (≥ 1100 px) com ✓ verde (`success`) / ! âmbar (`warning`); link sublinhado ciano para ação sugerida | FR-036 |
| Saída `forja ai` | linha '↳ roteando: local (ollama) · contexto: …' `code-sm` muted; caixa de resposta `layer-1` raio 8 padding 12 px; termos de código em chip `code-sm` com fundo `layer-3`; pergunta final com `[s/N]` em âmbar | FR-061 |
| Overlay Central de Comando | coluna direita **520 px** (`dimensions.overlay_width`), 16 px da borda direita, altura = tela − 32 px; fundo `layer-2` 0,70 + blur 24 px; borda `border-active`; raio 16 px; cabeçalho `headline-sm` 'Central de Comando' + chip `Super + Espaço` | FR-121 |
| Card do assistente | topo do overlay; mascote 40 px à esquerda; linha 1 `label-sm` ciano '<Mascote> · ouvindo palavra de ativação (100 % local)'; linha 2 `body-md` com a frase ouvida entre aspas; linha 3 ações executadas `code-sm` com ✓ e tier + duração ('2,1 s'); waveform 8 barras 4–26 px abaixo | FR-103, FR-121 |
| Tiles 2×3 | grid 2 colunas, gap 8 px, cada tile `layer-1` raio 8, padding 12 px, altura 56 px: título `body-md` 600 + subtítulo `code-sm` muted + status dot 6 px à direita (ciano ligado, violeta BT, verde firewall, cinza desligado). Ordem: Wi-Fi, Bluetooth, VPN, Modo Jogo, Firewall, Não perturbe | FR-121 |
| Desempenho | card com 4 medidores (CPU, RAM, GPU, VRAM) em grid 4 col; valor `headline-sm` tabular; barra 4 px abaixo, cor por métrica (ciano/azul/violeta/laranja); label 'ao vivo' com dot pulsante; amostra 2 s; pausa ao fechar | FR-121 |
| Containers + IA | 2 cards lado a lado: lista nome `code-md` + chip estado 22 px (verde 'rodando', âmbar 'reiniciando'); IA lista Ollama/Hermes/Claude Code/Codex com chip `local` (ciano) ou `API` (cinza) | FR-121, FR-092 |
| Segurança e logs | card: 3 linhas `code-sm` (CrowdSec, Suricata, journald) com tempo à direita; **CrowdSec/Suricata só aparecem com Escudo instalado**; sem Escudo o card mostra firewalld + auditd + journald | FR-095, ADR-023 |
| Rede | card: interface/banda, download/upload, latência, dispositivos na LAN; valores `code-md` ciano à direita | FR-121 |
| Dock | centralizado, 12 px da borda inferior, altura 64 px, raio 12 px, `glass-dock` blur 24 px, borda `border-ghost-strong`; ícones 48 px raio 8, gap 8 px; ordem: Terminal, Code, Git, Docker, Unity*, Godot, HERO, Monitor, Navegador, Apps; ponto ativo 3 px ciano sob o ícone (`*Unity` só após instalação) | FR-052 |

## Conteúdo (PRD → substituir)

Ocorrências encontradas no `code.html` por `grep`; a coluna "Na implementação" é obrigatória.

| No protótipo | Ocorrências | Na implementação | Fonte |
| --- | --- | --- | --- |
| `Jarvis` | 6 | Guará (persona) / HERO (motor) | ADR-005, ADR-006 |
| `devos` | 10 | forja (CLI), forja-term (terminal) | ADR-020, FR-035, FR-060 |
| `rodrigo@` | 3 | usuario@forjaos ($USER@forjaos) | FR-003 |
| `nftables` | 1 | firewalld | ADR-022 |
| `RTX 4070` | 1 | RTX 5060 8 GB (desktop de referência) | §10.2 |
| `GameMode` | 1 | Modo Jogo (hero-game.target) | FR-043 |
| `Escudo ativo` | 1 | indicador só se `forja install escudo` executado | ADR-023, NFR-027 |
| `KWin Plasma 6` | 1 | remover rótulo decorativo | — |
| `GameMode on` | 1 | Modo Jogo · hero-game.target | FR-043 |
| `ATIVO` | 1 | chip 'ativo' `label-xs` em `accent-cyan` | FR-043 |

## Ícones

Protótipo usa Material Symbols; produto usa Breeze recolorido pelos tokens ou SVG próprio em `brand/icons/` (DESIGN-RULES §5).

| Material Symbol | Breeze / próprio |
| --- | --- |
| `crop_square` | `window-maximize` |
| `mic` | `audio-input-microphone` |
| `terminal` | `utilities-terminal` |
| `verified_user` | `security-high` |

## Checklist de fidelidade

- [ ] Largura exata 520 px; abre em ≤ 150 ms (NFR-010)
- [ ] Fecha com Esc/clique fora; lembra última aba
- [ ] Tier e resultado por ação ('✓ docker compose up · ✓ Godot aberto · 2,1 s') (FR-103)
- [ ] Desempenho amostra a cada 2 s e pausa ao fechar
- [ ] Consumo do overlay fechado = 0 processos além do plasmoid
- [ ] Card Segurança sem CrowdSec/Suricata quando Escudo ausente
- [ ] Tiles refletem estado real via D-Bus (NetworkManager, BlueZ, firewalld, hero-game.target, DnD)
- [ ] Captura lado a lado em `docs/design-system/telas/forjaos_central_de_comando_hero_corrigida/compare-AAAA-MM-DD.png` (mesma resolução)
- [ ] `scripts/check-tokens.sh` OK
- [ ] `grep -nE 'Jarvis|devos|nftables|24\.04|arm64|RTX 4070'` vazio no código da tela
- [ ] Revisor (contexto limpo, ADR-033) registrou `visual: fiel`

## Pendências e divergências conhecidas

- Card Segurança e logs mostra CrowdSec/Suricata como se fossem padrão; são opt-in (ADR-023). Sem Escudo: firewalld + auditd + journald.
- Tile `Firewall · nftables` → `Firewall · firewalld` (ADR-022).
- Card Rede lista dispositivos na LAN: exige varredura ativa — avaliar tier e consumo antes de implementar (princípio 5).

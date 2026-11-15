# Serviço D-Bus do HERO

O daemon de sessão `herod` publica `org.forjaos.Hero` no barramento D-Bus do usuário, no objeto `/org/forjaos/Hero`.

## API atual

- Propriedade `State` (`s`): estado atual em português, conforme FR-071.
- Método `TransitionState(s) -> b`: valida a transição de estado; retorna `true` quando muda e `false` quando já estava no destino. Transições inválidas retornam `InvalidArgs`.
- Sinal `StateChanged(s)`: emitido depois de cada transição válida.

Estados aceitos: `desligado`, `ocioso`, `escutando`, `gravando`, `transcrevendo`, `pensando`, `falando`, `erro`. A transição inicia em `ocioso`; regras e recursos de áudio e roteamento entram nos itens seguintes do HERO.

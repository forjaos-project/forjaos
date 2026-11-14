# Jogos e gamedev

O Steam e as regras `steam-devices` vêm da imagem base. Gamescope, MangoHud e BlueZ são instalados a partir dos repositórios já configurados na imagem. O perfil `gamedev` do primeiro boot instala Godot 4, Blender, Krita, Lutris, Heroic e ProtonPlus para o usuário via Flathub. Depois de instalar o Godot, o perfil baixa os templates oficiais de exportação da mesma versão, verifica SHA-256 e os coloca no diretório do Flatpak. Se você também escolher VS Code, o perfil instala a extensão Godot Tools.

Abra o ProtonPlus para instalar o Proton GE na conta do usuário. Ele não é incluído previamente na imagem. O Unity Hub é opcional e tem instalador separado (`forja install unity`).

O Modo Jogo começa ao detectar Steam ou gamescope na sessão, e também pode ser controlado por `forja game-mode on|off|status`. Durante o modo, o ForjaOS solicita o perfil de energia `performance` e Não perturbe. `off` suspende a ativação automática até que o processo de jogo atual termine. O serviço respeita uma escolha manual `on` mesmo após fechar o jogo.

No build final, validar com um jogo nativo e dois jogos Proton: lançamento, entrada e saída do Modo Jogo, perfil de energia, notificações, MangoHud, gamescope e três controles (Xbox, DualSense e 8BitDo) por USB e Bluetooth. Para exportar o projeto Godot de exemplo para Linux e Web, executar `bash scripts/validate-godot-exports.sh <diretório-de-saída>` em uma sessão com o perfil gamedev instalado. O desempenho com HERO/Memória ligados será medido em F4-004.

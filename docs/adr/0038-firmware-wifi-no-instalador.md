# ADR-0038 — Firmware Wi‑Fi no ambiente do instalador

**Status:** aceito · **Data:** 2026-11-12 · **Aprovação:** mantenedor, 2026-11-12 · **Relacionados:** F1-002, FR-010, FR-014, ADR-0035, ADR-0036

## Contexto

No teste físico da candidata `forjaos-nvidia-open.iso` no Dell Inspiron 15, o Anaconda iniciou, mas não listou Wi‑Fi. O log do kernel registrou ausência de `iwlwifi-5000-*.ucode`. O hardware é Intel Wireless WiFi Link 5100; ele requer firmware Intel DVM disponibilizado separadamente do driver. A imagem customizada do instalador não instala um pacote de firmware Wi‑Fi. Como a ISO usa payload remoto (ADR-0035) e este notebook não oferece Ethernet utilizável, sem Wi‑Fi a instalação não pode avançar nesse equipamento.

O Fedora publica `iwlwifi-dvm-firmware` para dispositivos Intel com driver DVM e classifica a licença como `LicenseRef-Fedora-Firmware`. A licença Intel permite redistribuição do binário sem modificação sob condições, incluindo preservar o aviso de copyright e a isenção de garantias, não sugerir endosso Intel e não fazer engenharia reversa. Isso não se enquadra na lista padrão G4 do repositório, que exige aprovação explícita para novas licenças.

## Decisão

1. O pacote Fedora `iwlwifi-dvm-firmware` pode ser incluído **somente no ambiente live da ISO do instalador**, para que o driver Intel carregue a placa Wi‑Fi durante a instalação por rede. Ele não será adicionado à imagem bootc instalada.
2. O mantenedor aprova explicitamente a exceção G4 para esta licença e este pacote em 2026-11-12. O binário será redistribuído sem modificação. A ISO conservará o arquivo de licença fornecido pelo RPM em `/usr/share/licenses/iwlwifi-dvm-firmware/LICENCE.iwlwifi_firmware`; os avisos de terceiros publicados para a candidata incluirão a mesma licença.
3. O build deve comprovar que `iwlwifi-5000-5.ucode` está no initramfs live, além de validar o carregamento do driver e a presença da interface Wi‑Fi no Dell. A aprovação da licença não representa aprovação geral para outros firmwares ou licenças.

## Consequências

- O notebook pode conectar à rede pela interface Wi‑Fi padrão do Anaconda sem cabo Ethernet.
- A ISO cresce pelo tamanho do pacote e dos arquivos de licença; CI mede novamente os limites de 2 GiB por asset e 6 GB por ISO.
- A redistribuição deve manter o firmware intacto e os avisos de licença acessíveis dentro da ISO e nos metadados da candidata.

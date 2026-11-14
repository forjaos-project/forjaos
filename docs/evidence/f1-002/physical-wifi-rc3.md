# Evidência física de Wi-Fi — F1-002

- Data: 2026-11-13
- Hardware: Dell Inspiron 15, Intel WiFi Link 5100 AGN (`wlp12s0`)
- Mídia: ISO de teste local rc3, variante `forjaos`
- Resultado: na tela de configuração de rede do Anaconda, o Wi-Fi apareceu e ficou conectado sem cabo Ethernet. O mantenedor confirmou por foto.
- Escopo: validação do Wi-Fi do instalador. A instalação no disco não foi iniciada.
- Privacidade: a foto original contém SSID, endereço IP e endereço MAC da rede doméstica; não foi incluída neste repositório nem anexada ao PR.
- Limite observado: a tela de particionamento mostrou o disco `sda` com partições NTFS existentes e apenas 4,2 MiB livres. A partição selecionada (`sda2`, 78,73 GiB, NTFS) não foi reformatada. Não houve escrita no disco.
- Próxima etapa: F1-003 cobre dual boot com Windows, Secure Boot e pós-instalação; este teste não comprova preservação ou inicialização do Windows.

## Identificação da ISO

- Arquivo: `D:\ForjaOS-local-test-rc3\forjaos.iso`
- SHA-256: `8d6cf40f5179c4ffd6633540ec33ea3c6351e17b61ea19fb25159505e59c53f3`
- Tamanho: 2.085.787.648 bytes

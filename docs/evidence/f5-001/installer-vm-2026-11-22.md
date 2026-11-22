# F5-001 — diagnóstico do instalador em VM

Data: 2026-11-22. Etapa de VM: [#116](https://github.com/forjaos-project/forjaos/issues/116). Retestes físicos: [#114](https://github.com/forjaos-project/forjaos/issues/114) e [#115](https://github.com/forjaos-project/forjaos/issues/115).

## Ambiente e reprodução

Hyper-V geração 2, quatro vCPUs, Secure Boot com `MicrosoftUEFICertificateAuthority` e disco virtual exclusivo de 80 GiB, particionado pelo Anaconda em Btrfs. A VM anterior `ForjaOS-Test` teve seu estado salvo e seu disco preservado. Nenhum disco físico foi anexado às VMs de instalação.

O Kickstart de teste seleciona somente o disco virtual e exercita senhas de contas de validação. As ISOs de distribuição mantêm o particionamento e as contas interativos. A RC12 usou o payload do teste no notebook, `sha256:4f43d1c009ccf145933df5d8e644d7291d81e92c3d6b906af80596e89eb6889d`. A tag `:testing` avançou durante a construção da RC13; ela fixou o novo digest assinado `sha256:b26ff461b3f9e44e372f8df939518b5c81d616d9fa2ec81dfd2041a8a4b8db76`.

| Execução | Resultado observado |
| --- | --- |
| RC9, ISO original do teste físico | Reproduziu `Unable to label target account files: status=1` na criação de usuário. [Captura](rc9-account-label-error.png). |
| RC11, caminhos reais e política binária do destino | `setfiles` retornou zero. `chpasswd` falhou porque o backup `shadow-` ainda tinha tipo `etc_t`. |
| Correção completa, ensaio no destino da RC11 | As funções reais do Anaconda definiram senhas de root e usuário existente e criaram outro usuário, com retorno zero e SELinux enforcing. |
| RC12, instalação limpa | Anaconda terminou sem erro; `setfiles` retornou 0 nas duas senhas. Boot com Secure Boot ligado parou em `bad shim signature` por falta de MOK. A importação manual da chave Universal Blue, seguida da confirmação no MokManager, permitiu boot, login gráfico e root, com SELinux enforcing. [Antes do MOK](rc12-before-mok.png), [boot com Secure Boot](rc12-secureboot-on.png), [estado](rc12-secureboot-state.png). |
| RC13, estágio automático inicial | Instalação limpa terminou; `setfiles` retornou 0 duas vezes, `chpasswd` executou e Anaconda registrou sucesso. O primeiro boot ainda parou em `bad shim signature`: `mokutil --test-key` imprimiu `is not enrolled` mas retornou 0, então o script não importou a chave. [Falha observada](rc13-bad-shim-signature.png). Importação manual e confirmação no MokManager permitiram boot com Secure Boot ligado. |
| RC14, solicitação idempotente de MOK | Instalação limpa terminou com dois `setfiles` de retorno 0 e `MOK_STAGE_IMPORT_OK`. No primeiro boot pelo disco, shim exibiu `Could not find MokManager` ([captura](rc14-mokmanager-missing.png)). Iniciar pela ISO apresentou [MokManager](rc14-mok-from-iso.png); após confirmar a chave, o disco iniciou com Secure Boot ligado. O ESP instalado tinha `EFI/fedora/mmx64.efi`, mas não `EFI/BOOT/mmx64.efi` ([inspeção](rc14-efi-missing-fallback-mok.png)). |
| RC15, cópia no ESP | A instalação limpa chegou às senhas sem erro, mas o `%post --erroronfail` interrompeu a instalação: `MOK_STAGE_MISSING_TARGET_MANAGER_OR_SHIM`. O ESP estava montado em `/var/mnt/sysroot/boot/efi`, porém outra montagem de `/boot` encobria seus arquivos nesse namespace. Montar `/dev/sda1` em um diretório temporário revelou `EFI/fedora/mmx64.efi` e o shim assinado. O script corrigido, executado nessa VM, registrou `MOK_STAGE_ESP_REMOUNTED`, `MOK_FALLBACK_MANAGER_INSTALLED`, `MOK_STAGE_IMPORT_OK` e comparação byte a byte com retorno zero. A RC15 não foi aprovada. |
| RC16, instalação limpa e primeiro boot | ISO de 2.085.705.728 bytes, SHA-256 `35b248191817121fd4fd955afc7b9bb195591ee80690143bc12b7bd9cc653381`. O Anaconda terminou com dois `setfiles` de retorno 0, executou `chpasswd` para root e usuário, registrou `MOK_STAGE_ESP_REMOUNTED`, `MOK_FALLBACK_MANAGER_INSTALLED`, `MOK_STAGE_IMPORT_OK` e `Installation successfully finished`. Com **as duas ISOs desconectadas**, o primeiro boot pelo disco abriu o [MokManager](rc16-mokmanager-from-disk.png). A chave pública Universal Blue foi confirmada e o sistema iniciou; o [login gráfico](rc16-user-login.png) e o login root funcionaram. O [estado](rc16-secureboot-state.png) mostrou Secure Boot ligado, SELinux enforcing e ambas as contas com senha ativa. `mokutil --test-key` confirmou a chave inscrita. O arquivo `EFI/BOOT/mmx64.efi` ficou byte a byte igual ao `EFI/fedora/mmx64.efi`. Um segundo boot sem ISO voltou ao [login gráfico](rc16-secondboot-login.png) e aceitou novamente a senha de validação. |

Na RC9, a RAM foi dinâmica e o disco começou no HDD antes da migração para o SSD. As RC11 a RC16 usaram 5 GiB e disco no SSD. Os tempos dessas execuções não constituem um benchmark comparável. Os discos da RC9, RC13, RC14 e RC15 foram copiados para D:, conferidos por SHA-256 e as VMs passaram a apontar para essas cópias; a VM anterior `ForjaOS-Test` não foi alterada.

A RC12 tem 2.085.701.632 bytes e SHA-256 `e3d34967c046afebf3a6336bebbf15b14e543bcbd5124518dc74fae19bae00f8`. A cópia no SSD foi comparada byte a byte por SHA-256 com a ISO do build. O trecho do patch foi extraído diretamente do SquashFS e comparado com o código-fonte.

A RC13 tem 2.085.705.728 bytes e SHA-256 `0f714d9607cea9ef37414c9060bba912afa721dc2837612335c5b3f337ccb8a0`. O certificado público embarcado, SHA-256 `4e5c68474cb133fd8984d9599762cece9100c3e6cd8a9709aeaabd85dd9e70d1`, corresponde ao certificado de assinatura do kernel no payload instalado.

Na RC16, a cópia da ISO no SSD e o arquivo de origem em D: tiveram o mesmo SHA-256. O script de estágio MOK foi extraído do SquashFS da ISO e comparado por SHA-256 com o código-fonte (`53d1828e67fcf8c5d17d5cd30953f77efdd22ed9884e9eef828047f5ed1f6d85`). O sistema instalado iniciou o payload fixado `sha256:b26ff461b3f9e44e372f8df939518b5c81d616d9fa2ec81dfd2041a8a4b8db76`.

## Causas confirmadas

1. A política do destino inclui tipos ausentes no ambiente live. Com a política exata extraída do payload, `setfiles` falhou com `context system_u:object_r:mysqld_etc_t:s0 is invalid`. A opção `-c` permite validar os contextos com a política binária do destino.
2. `/mnt` é um link para `/var/mnt` no instalador. `setfiles` recusou os caminhos com esse ancestral simbólico (`Not a directory`); resolver o prefixo real antes de montar os argumentos eliminou a falha.
3. O AVC da RC11 mostrou `comm="chpasswd"`, operação `{ unlink }`, arquivo `shadow-`, processo `passwd_t`, arquivo `etc_t`, `permissive=0`. Os backups e bancos de grupos também precisam dos seus rótulos específicos.
4. O `mokutil --test-key` da RC13 retorna 0 inclusive quando exibe `is not enrolled`; usar apenas esse código de saída omitiu a solicitação do MOK. `mokutil --import` confirmou ser idempotente na VM: certificado pendente ou já inscrito produz `SKIP` e retorna com sucesso.
5. Antes do primeiro boot, a VM ainda não tinha entrada UEFI Fedora; o firmware iniciou o shim `EFI/BOOT/BOOTX64.EFI`. O ESP criado pelo instalador tinha um shim idêntico em `EFI/fedora/shimx64.efi` e o MokManager assinado só em `EFI/fedora/mmx64.efi`. A solicitação feita no ambiente live dependia do MokManager no mesmo diretório do shim de fallback. A correção copia o gerenciador apenas quando o shim de fallback corresponde byte a byte ao shim Fedora, preservando outro carregador EFI.
6. Na RC15, a montagem posterior de `/boot` ocultou o ESP no caminho convencional do `%post`. O script agora identifica a montagem VFAT do ESP, monta o mesmo dispositivo em `/run`, copia e compara o MokManager e desmonta o acesso temporário.

A correção rotula `passwd` e `shadow`, os arquivos de grupos e os backups existentes, além do lock existente, usando a política binária do destino. Confere os tipos efetivos antes de executar `chpasswd` e interrompe se a política estiver ausente ou a rotulagem falhar. Não amplia permissões de `passwd_t` para `etc_t` nem altera enforcing.

O ensaio das funções completas foi executado com `system_u:system_r:unconfined_service_t:s0`, o contexto do serviço do Anaconda, e produziu:

```text
ROOT_PASSWORD_SET
USER_PASSWORD_SET
NEW_USER_CREATED_AND_PASSWORD_SET
status=0/SUCCESS
Enforcing
root P
validation P
```

Foram consultados somente estado das contas e rótulos, sem coletar o conteúdo de `shadow`. Os bancos e backups ficaram em `passwd_file_t` ou `shadow_t`, conforme a política do destino.

## Verificações locais

Os 25 testes Python do patch de usuários, do patch bootc/Btrfs, da configuração do instalador e do estágio MOK passaram no Linux; a parte compatível com Windows também passou. Os testes de regressão falharam antes das correções. O teste shell de construção da ISO passou. Os artefatos e logs operacionais ficam fora do Git em `D:\ForjaOS\validation\f5-001\`.

A instalação e o boot pelo disco com Secure Boot estão validados na VM. No primeiro boot, o wizard mostrou `Estado indisponível` para detecção de sistema e Secure Boot, apesar da confirmação direta por `mokutil`; esta tela não serviu como evidência de estado. A aceitação física F5-001, dual boot, MOK em hardware real e o segundo hardware continuam pendentes. Nenhum teste foi feito no notebook nesta etapa.

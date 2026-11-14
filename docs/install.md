# Instalação do ForjaOS por ISO

## Estado e escolha da imagem

F1-002 gera as variantes `forjaos.iso` (desktop genérico) e `forjaos-nvidia-open.iso` (NVIDIA open). Estas ISOs contêm o instalador Anaconda, não o sistema completo: a instalação exige **conexão com a internet** para baixar o payload ForjaOS do GHCR. O instalador referencia um digest imutável e deve verificar a assinatura do payload antes de instalá-lo; se a rede ou a verificação falhar, interrompa a instalação. Os artefatos de CI são para validação; só use uma versão publicada em GitHub Release após a validação de release. O fluxo de publicação e os testes físicos ainda precisam ser concluídos. Não confunda o arquivo de CI com uma versão `stable`.

Para validar em hardware antes da publicação, o mantenedor pode despachar `iso.yml` na branch F1-002 com `candidate_tag` no formato `vX.Y.Z-rc.N`. O fluxo constrói a partir de `:testing`, cria um GitHub Release em **rascunho** e pré-lançamento, baixa os assets de volta e confere checksum e assinatura. Essa candidata não é `:stable` e não substitui o release final, que exige `release_tag` em `main` e payload `:stable` após promoção.

Baixe a ISO desejada, o `SHA256SUMS` e o arquivo `<nome-da-iso>.sigstore.json` do **mesmo** build ou release. Guarde os três no mesmo diretório. Nos artefatos de CI, cada variante tem seu próprio manifesto; no Release, o `SHA256SUMS` é combinado e lista as duas ISOs. A opção `--ignore-missing` verifica apenas a ISO baixada. Obtenha também `cosign.pub` do commit associado à imagem. Antes de gravar o pendrive, confira:

```bash
sha256sum -c --ignore-missing SHA256SUMS
cosign verify-blob --key cosign.pub \
  --bundle forjaos.iso.sigstore.json forjaos.iso
```

Confira que a saída do `sha256sum` mostra `<nome-da-iso>: OK`. Para a variante NVIDIA, troque `forjaos.iso` por `forjaos-nvidia-open.iso` nos nomes do segundo comando. Interrompa se qualquer verificação falhar ou se nenhuma ISO for verificada. O PRD limita a ISO a 6 GB decimais; para publicar diretamente no GitHub Release, cada arquivo também precisa ter menos de 2 GiB. O CI mede ambos os limites.

## Pendrive e boot

Use um pendrive de pelo menos 8 GB, sem dados que precisem ser preservados, e uma conexão confiável com o GHCR durante a instalação. A gravação apaga ou substitui o conteúdo do dispositivo escolhido. Para validar FR-014, repita os três métodos abaixo em mídia de teste e registre o resultado separadamente. Mantenha Secure Boot no estado exigido pelo cenário de validação; a confirmação de MOK e dual boot pertence a F1-003.

## Dual boot com Windows e Secure Boot (FR-011, FR-012, FR-013)

Antes de instalar ao lado do Windows, faça backup dos arquivos e guarde a chave de recuperação do BitLocker em local acessível fora do computador. A Inicialização Rápida mantém o kernel do Windows em hibernação após o desligamento; o ForjaOS mantém NTFS em somente leitura para não gravar nesse estado ([documentação da Microsoft sobre Inicialização Rápida](https://learn.microsoft.com/en-us/troubleshoot/windows-client/setup-upgrade-and-drivers/fast-startup-causes-system-hibernation-shutdown-fail)). Mantenha BitLocker ativo; mudanças de firmware ou software de boot podem pedir a chave de recuperação ([documentação da Microsoft sobre BitLocker](https://support.microsoft.com/en-us/windows/security/encryption/bitlocker-overview)). Em dispositivos gerenciados, siga a orientação do administrador antes de alterar a proteção.

No Anaconda, escolha o disco que contém o Windows e use apenas o espaço livre ou a opção interativa de liberar espaço. Confira a tela de resumo antes de iniciar: as partições Windows, EFI e de recuperação precisam permanecer preservadas; não use uma opção que apague o disco inteiro. Na primeira inicialização UEFI, o serviço do ForjaOS instala o tema no `/boot` e regenera a configuração do GRUB. Confirme que Windows aparece no menu e inicialize-o para validar o acesso; se não aparecer, use a entrada Windows Boot Manager no menu do firmware. Esse fluxo ainda precisa de validação em hardware antes do release.

Mantenha Secure Boot habilitado. No primeiro reinício, se o MokManager abrir, escolha `Enroll MOK`, confirme a chave Universal Blue e reinicie. Se o enrollment precisar ser solicitado após a instalação, use `ujust enroll-secure-boot-key`; o MokManager pedirá a senha `universalblue` no próximo boot. Após o boot, confirme o estado com `mokutil --sb-state` e, na variante NVIDIA, confira o assinante do módulo com `modinfo -F signer nvidia`. Consulte o [guia oficial de Secure Boot do Bazzite](https://docs.bazzite.gg/General/Installation_Guide/secure_boot/).

Com Windows detectado no primeiro boot, o ForjaOS ajusta o relógio local para o modo compatível e monta volumes NTFS em somente leitura por padrão. Fast Startup pode deixar NTFS em estado inconsistente; BitLocker pode exigir a chave de recuperação após alterações no boot. O componente visual do aviso já está incluído na imagem; sua exibição depende da integração com o host do wizard FR-020.

### Fedora Media Writer

1. Abra Fedora Media Writer e escolha a opção de imagem personalizada.
2. Selecione a ISO já verificada e confira o pendrive de destino antes de iniciar.
3. Ao terminar, ejete a mídia, inicialize o hardware de referência por USB e registre se o instalador Anaconda abre.

### Ventoy

1. Instale Ventoy no pendrive de teste conforme as instruções da ferramenta e confirme o dispositivo escolhido. Essa preparação apaga o pendrive.
2. Copie a ISO verificada para a partição de dados do Ventoy, ejete a mídia e inicialize por USB.
3. Selecione a ISO no menu Ventoy e registre se o instalador Anaconda abre. Registre separadamente o resultado com Secure Boot ligado.

### `dd` em Linux

Este método escreve diretamente no dispositivo inteiro. Antes de executá-lo, confirme explicitamente que o alvo é o pendrive de teste. Use `lsblk -o NAME,SIZE,MODEL,TRAN,MOUNTPOINTS` antes e depois de inserir a mídia; identifique o novo **dispositivo**, não uma partição e nunca o disco do sistema. Desmonte as partições do pendrive. Substitua `/dev/sdX` pelo dispositivo conferido:

```bash
lsblk -o NAME,SIZE,MODEL,TRAN,MOUNTPOINTS
sudo dd if=forjaos.iso of=/dev/sdX bs=4M status=progress conv=fsync
sync
```

Ejetar e inicializar a mídia faz parte do teste. O comando acima é documentação; não é executado pelo pipeline.

## Registro do aceite

Em cada release, registre em `docs/releases/` a versão, SHA-256, tamanho das duas ISOs, identificadores dos pendrives de teste, método usado, hardware, estado de Secure Boot, boot do instalador e resultado. Uma ISO que compila em CI ainda não prova gravação ou instalação física. A instalação em dual boot nos hardwares de referência é coberta pelo caminho de validação do PRD §11 e pelos itens seguintes do roadmap.

# Instalação do ForjaOS por ISO

## Estado e escolha da imagem

F1-002 gera as variantes `forjaos.iso` (desktop genérico) e `forjaos-nvidia-open.iso` (NVIDIA open). Estas ISOs contêm o instalador Anaconda, não o sistema completo: a instalação exige **conexão com a internet** para baixar o payload ForjaOS do GHCR. O instalador referencia um digest imutável e deve verificar a assinatura do payload antes de instalá-lo; se a rede ou a verificação falhar, interrompa a instalação. Os artefatos de CI são para validação; só use uma versão publicada em GitHub Release após a validação de release. O fluxo de publicação e os testes físicos ainda precisam ser concluídos. Não confunda o arquivo de CI com uma versão `stable`.

Baixe a ISO desejada, seu `SHA256SUMS` e o arquivo `<nome-da-iso>.sigstore.json` do **mesmo** build ou release. Guarde os três no mesmo diretório. O `SHA256SUMS` de cada variante é separado; não substitua um pelo outro. Obtenha também `cosign.pub` do commit associado à imagem. Antes de gravar o pendrive, confira:

```bash
sha256sum -c SHA256SUMS
cosign verify-blob --key cosign.pub \
  --bundle forjaos.iso.sigstore.json forjaos.iso
```

Para a variante NVIDIA, troque `forjaos.iso` por `forjaos-nvidia-open.iso` nos nomes do segundo comando. Interrompa se qualquer verificação falhar. O PRD limita a ISO a 6 GB decimais; para publicar diretamente no GitHub Release, cada arquivo também precisa ter menos de 2 GiB. O CI mede ambos os limites.

## Pendrive e boot

Use um pendrive de pelo menos 8 GB, sem dados que precisem ser preservados, e uma conexão confiável com o GHCR durante a instalação. A gravação apaga ou substitui o conteúdo do dispositivo escolhido. Para validar FR-014, repita os três métodos abaixo em mídia de teste e registre o resultado separadamente. Mantenha Secure Boot no estado exigido pelo cenário de validação; a confirmação de MOK e dual boot pertence a F1-003.

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

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: window
    width: 1320
    height: 760
    implicitWidth: 1320
    implicitHeight: 760
    signal continueRequested()

    readonly property bool portuguese: Qt.locale().name.toLowerCase().startsWith("pt")
    property string windowsState: "unknown"
    property string secureBootState: "unknown"
    property string mokState: "unknown"
    readonly property color borderGhost: Qt.rgba(1, 1, 1, 0.08) // brand/palette.json: alpha.border-ghost
    readonly property color borderActive: Qt.rgba(0, 229 / 255, 1, 0.35) // brand/palette.json: alpha.border-active

    QtObject {
        id: copy
        readonly property string header: window.portuguese ? "Configuração inicial" : "Initial setup"
        readonly property string context: window.portuguese ? "ETAPA DE SEGURANÇA · ANTES DO WIZARD" : "SAFETY STEP · BEFORE THE WIZARD"
        readonly property string title: window.portuguese ? "Confira antes de continuar" : "Review before continuing"
        readonly property string intro: window.portuguese
            ? "Estas orientações ajudam a proteger seus dados ao instalar ao lado do Windows."
            : "These notes help protect your data when installing alongside Windows."
        readonly property string windowsFound: window.portuguese ? "Windows encontrado" : "Windows detected"
        readonly property string windowsMissing: window.portuguese ? "Nenhum Windows detectado" : "No Windows detected"
        readonly property string unavailable: window.portuguese ? "Estado indisponível" : "Status unavailable"
        readonly property string readOnly: window.portuguese ? "NTFS somente leitura" : "NTFS read-only"
        readonly property string fastStartup: window.portuguese ? "Inicialização Rápida e NTFS" : "Fast Startup and NTFS"
        readonly property string fastStartupBody: window.portuguese
            ? "A Inicialização Rápida mantém o kernel em hibernação após o desligamento. O ForjaOS monta NTFS em somente leitura para não gravar nesse estado."
            : "Fast Startup keeps the kernel hibernated after shutdown. ForjaOS mounts NTFS read-only to avoid writing in that state."
        readonly property string bitlocker: window.portuguese ? "BitLocker e recuperação" : "BitLocker and recovery"
        readonly property string bitlockerBody: window.portuguese
            ? "Guarde sua chave de recuperação fora deste computador. Mudanças no boot podem fazer o Windows solicitá-la."
            : "Keep your recovery key somewhere outside this computer. Boot changes may cause Windows to request it."
        readonly property string installAlongside: window.portuguese ? "Instalação ao lado do Windows" : "Install alongside Windows"
        readonly property string installBody: window.portuguese
            ? "No Anaconda, revise o disco e o resumo antes de iniciar. O ForjaOS não escolhe nem apaga discos automaticamente."
            : "In Anaconda, review the disk and summary before starting. ForjaOS does not select or erase disks automatically."
        readonly property string secureBoot: "Secure Boot"
        readonly property string universalBlueKey: window.portuguese ? "Chave Universal Blue" : "Universal Blue key"
        readonly property string enabled: window.portuguese ? "Ativado" : "Enabled"
        readonly property string disabled: window.portuguese ? "Desativado" : "Disabled"
        readonly property string mokRegistered: window.portuguese ? "Chave MOK inscrita" : "MOK key enrolled"
        readonly property string mokPending: window.portuguese ? "Inscrição MOK pendente" : "MOK enrollment pending"
        readonly property string secureBody: window.portuguese
            ? "Mantenha Secure Boot habilitado. A chave MOK autoriza o carregador e os módulos assinados da imagem."
            : "Keep Secure Boot enabled. The MOK key authorizes the bootloader and signed image modules."
        readonly property string step1: window.portuguese ? "Conclua a instalação e reinicie o computador." : "Complete installation and restart the computer."
        readonly property string step2: window.portuguese ? "No MokManager, escolha Enroll MOK e confirme a chave." : "In MokManager, choose Enroll MOK and confirm the key."
        readonly property string step3: window.portuguese ? "Reinicie para iniciar o ForjaOS com Secure Boot." : "Restart to boot ForjaOS with Secure Boot."
        readonly property string enrollmentCommand: "ujust enroll-secure-boot-key"
        readonly property string stateNote: window.portuguese
            ? "Os estados acima são lidos deste sistema. Nenhuma alteração de disco ou de firmware será feita nesta tela."
            : "The statuses above are read from this system. This screen will not change disks or firmware."
        readonly property string footer: window.portuguese
            ? "Revise as opções de instalação antes de qualquer alteração no disco."
            : "Review installation options before making any disk changes."
        readonly property string continueLabel: window.portuguese ? "Entendi, continuar" : "I understand, continue"
    }

    Rectangle {
        anchors.fill: parent
        color: "#10141e"
        border.color: window.borderGhost
        radius: 16
        anchors.margins: 24

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 20

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 64
                spacing: 14

                Rectangle {
                    Layout.preferredWidth: 42
                    Layout.preferredHeight: 42
                    radius: 12
                    color: "#1e2433"
                    border.color: window.borderActive
                    Text { anchors.centerIn: parent; text: "F"; color: "#00e5ff"; font.family: "Plus Jakarta Sans"; font.pixelSize: 22; font.weight: Font.Bold }
                }
                ColumnLayout {
                    spacing: 2
                    Text { text: copy.header; color: "#dfe2f0"; font.family: "Plus Jakarta Sans"; font.pixelSize: 17; font.weight: Font.Bold }
                    Text { text: copy.context; color: "#94a3b8"; font.family: "JetBrains Mono"; font.pixelSize: 11 }
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: window.portuguese ? "PRIMEIRO BOOT" : "FIRST BOOT"
                    color: "#f59e0b"
                    font.family: "JetBrains Mono"
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                    padding: 8
                    background: Rectangle { color: "#161b26"; border.color: "#f59e0b"; radius: 6 }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 70
                spacing: 10
                Repeater {
                    model: window.portuguese
                        ? ["Segurança", "Idioma", "Mascote", "Perfil", "Contas", "Resumo"]
                        : ["Safety", "Language", "Mascot", "Profile", "Accounts", "Summary"]
                    delegate: Rectangle {
                        required property int index
                        required property string modelData
                        Layout.fillWidth: true
                        height: 42
                        color: index === 0 ? "#1e2433" : "#161b26"
                        radius: 9
                        border.color: index === 0 ? window.borderActive : window.borderGhost
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            spacing: 9
                            Rectangle {
                                Layout.preferredWidth: 26
                                Layout.preferredHeight: 26
                                radius: 13
                                color: index === 0 ? "#00e5ff" : "transparent"
                                border.color: index === 0 ? "#00e5ff" : window.borderGhost
                                Text { anchors.centerIn: parent; text: index + 1; color: index === 0 ? "#070a11" : "#94a3b8"; font.family: "JetBrains Mono"; font.pixelSize: 11 }
                            }
                            Text { text: modelData; color: index === 0 ? "#dfe2f0" : "#94a3b8"; font.family: "Plus Jakarta Sans"; font.pixelSize: 12; elide: Text.ElideRight }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 18

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: 500
                    color: "#171b26"
                    border.color: window.borderGhost
                    radius: 16

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 14
                            Rectangle {
                                Layout.preferredWidth: 46; Layout.preferredHeight: 46; radius: 13
                                color: "#161b26"
                                Text { anchors.centerIn: parent; text: "!"; color: "#f59e0b"; font.family: "Plus Jakarta Sans"; font.pixelSize: 24; font.weight: Font.Bold }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4
                                Text { text: copy.title; color: "#dfe2f0"; font.family: "Plus Jakarta Sans"; font.pixelSize: 24; font.weight: Font.Bold }
                                Text { text: copy.intro; color: "#94a3b8"; font.family: "Inter"; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 66
                            color: "#10141e"
                            border.color: window.borderGhost
                            radius: 12
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 16
                                ColumnLayout {
                                    spacing: 3
                                    Text { text: window.portuguese ? "DETECÇÃO DE SISTEMA" : "SYSTEM DETECTION"; color: "#94a3b8"; font.family: "JetBrains Mono"; font.pixelSize: 10 }
                                    Text { text: window.windowsState === "yes" ? copy.windowsFound : window.windowsState === "no" ? copy.windowsMissing : copy.unavailable; color: "#dfe2f0"; font.family: "Plus Jakarta Sans"; font.pixelSize: 14; font.weight: Font.DemiBold }
                                }
                                Item { Layout.fillWidth: true }
                                Label { text: copy.readOnly; color: "#10b981"; font.family: "JetBrains Mono"; font.pixelSize: 10; padding: 7; background: Rectangle { color: "#161b26"; radius: 6 } }
                            }
                        }

                        Repeater {
                            model: [
                                { number: "01", title: copy.fastStartup, body: copy.fastStartupBody },
                                { number: "02", title: copy.bitlocker, body: copy.bitlockerBody },
                                { number: "03", title: copy.installAlongside, body: copy.installBody }
                            ]
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                color: "#10141e"
                                border.color: window.borderGhost
                                radius: 12
                                RowLayout {
                                    anchors.fill: parent; anchors.margins: 14; spacing: 12
                                    Rectangle {
                                        Layout.alignment: Qt.AlignTop
                                        Layout.preferredWidth: 30; Layout.preferredHeight: 30
                                        color: "#161b26"; radius: 9
                                        Text { anchors.centerIn: parent; text: modelData.number; color: "#f59e0b"; font.family: "JetBrains Mono"; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 4
                                        Text { text: modelData.title; color: "#dfe2f0"; font.family: "Plus Jakarta Sans"; font.pixelSize: 13; font.weight: Font.DemiBold }
                                        Text { text: modelData.body; color: "#94a3b8"; font.family: "Inter"; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: 380
                    color: "#171b26"
                    border.color: window.borderGhost
                    radius: 16
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 24; spacing: 14
                        Text { text: copy.secureBoot.toUpperCase(); color: "#94a3b8"; font.family: "JetBrains Mono"; font.pixelSize: 11; font.weight: Font.DemiBold }
                        Rectangle {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            color: "#10141e"; border.color: window.borderGhost; radius: 12
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 20; spacing: 14
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text { text: copy.universalBlueKey; color: "#dfe2f0"; font.family: "Plus Jakarta Sans"; font.pixelSize: 15; font.weight: Font.DemiBold; Layout.fillWidth: true }
                                    Label {
                                        text: window.mokState === "yes" ? copy.mokRegistered : window.mokState === "no" ? copy.mokPending : copy.unavailable
                                        color: window.mokState === "yes" ? "#10b981" : "#f59e0b"
                                        font.family: "JetBrains Mono"; font.pixelSize: 10; padding: 6
                                        background: Rectangle { color: "#161b26"; radius: 6 }
                                    }
                                }
                                Text { text: copy.secureBody; color: "#94a3b8"; font.family: "Inter"; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                Label {
                                    text: window.secureBootState === "yes" ? copy.enabled : window.secureBootState === "no" ? copy.disabled : copy.unavailable
                                    color: window.secureBootState === "yes" ? "#10b981" : "#f59e0b"
                                    font.family: "JetBrains Mono"; font.pixelSize: 11
                                }
                                Rectangle { Layout.fillWidth: true; height: 1; color: window.borderGhost }
                                Repeater {
                                    model: [copy.step1, copy.step2, copy.step3]
                                    delegate: RowLayout {
                                        required property int index
                                        required property string modelData
                                        Layout.fillWidth: true; spacing: 10
                                        Text { text: "0" + (index + 1); color: "#00e5ff"; font.family: "JetBrains Mono"; font.pixelSize: 11 }
                                        Text { text: modelData; color: "#dfe2f0"; font.family: "Inter"; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                    }
                                }
                                Label {
                                    text: copy.enrollmentCommand
                                    color: "#00e5ff"; font.family: "JetBrains Mono"; font.pixelSize: 11
                                    padding: 10; Layout.fillWidth: true
                                    background: Rectangle { color: "#161b26"; radius: 8 }
                                }
                            }
                        }
                        Text { text: copy.stateNote; color: "#94a3b8"; font.family: "Inter"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 64
                Text { text: copy.footer; color: "#94a3b8"; font.family: "Inter"; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Button {
                    text: copy.continueLabel
                    Layout.preferredHeight: 42
                    contentItem: Label { text: parent.text; color: "#001f24"; font.family: "Plus Jakarta Sans"; font.pixelSize: 12; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; padding: 16 }
                    background: Rectangle { color: parent.down ? "#00b4d8" : "#00e5ff"; radius: 9 }
                    onClicked: window.continueRequested()
                }
            }
        }
    }
}

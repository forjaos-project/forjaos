import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: wizard
    visible: true
    visibility: Window.FullScreen
    title: "ForjaOS Setup"
    color: "#0f131d"
    property int step: 0
    property string language: "pt-BR"
    property string keyboard: "br"
    property string mascot: "Guará"
    property string profile: "minimal"
    property bool unity: false
    property string status: ""
    property real setupProgress: 0
    property bool finished: false
    property bool showPreflight: true
    function tr(pt, en) { return language === "pt-BR" ? pt : en }
    readonly property string setupCommand: "forja setup --profile " + profile + " --mascot "
        + JSON.stringify(mascot) + " --language " + language + " --keyboard " + keyboard
        + (unity ? " --unity" : "")
    readonly property var stepNames: language === "pt-BR"
        ? ["Idioma", "Mascote", "Perfil", "Contas", "Instaladores", "Resumo"]
        : ["Language", "Mascot", "Profile", "Accounts", "Installers", "Summary"]
    Timer { interval: 1200; repeat: true; running: wizard.finished; onTriggered: { wizard.status = bridge.setupStatus(); wizard.setupProgress = bridge.setupProgress() } }

    header: Rectangle {
        height: 64
        visible: !wizard.showPreflight
        color: "#161b26"
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 32
            anchors.rightMargin: 32
            Label { text: "ForjaOS Setup"; color: "#f1f5f9"; font.pixelSize: 22; font.bold: true }
            Item { Layout.fillWidth: true }
            Label { text: wizard.tr("PRIMEIRO BOOT", "FIRST BOOT"); color: "#00e5ff" }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 32
        spacing: 24
        visible: !wizard.showPreflight
        Rectangle {
            Layout.preferredWidth: 288
            Layout.fillHeight: true
            color: "#161b26"
            radius: 12
            Column {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 8
                Repeater {
                    model: wizard.stepNames
                    delegate: Rectangle {
                        width: 256; height: 56; radius: 8
                        color: index === wizard.step ? "#1e2433" : "transparent"
                        border.color: index === wizard.step ? "#00e5ff" : "transparent"
                        Label { anchors.centerIn: parent; text: (index + 1) + "  " + modelData; color: index <= wizard.step ? "white" : "#64748b"; font.pixelSize: 16 }
                    }
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#161b26"
            radius: 12
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 32
                spacing: 16
                Label { text: wizard.stepNames[wizard.step]; color: "#f1f5f9"; font.pixelSize: 28; font.bold: true }
                Label { visible: wizard.step === 0; text: wizard.tr("Escolha idioma e teclado. A aplicação do layout ocorre nas configurações do Plasma.", "Choose language and keyboard. Apply the layout in Plasma settings."); color: "#94a3b8"; wrapMode: Text.WordWrap }
                ComboBox { visible: wizard.step === 0; model: ["Português (Brasil)", "English (US)"]; onCurrentIndexChanged: wizard.language = currentIndex === 0 ? "pt-BR" : "en-US" }
                ComboBox { visible: wizard.step === 0; model: ["Teclado brasileiro (ABNT2)", "US International"]; onCurrentIndexChanged: wizard.keyboard = currentIndex === 0 ? "br" : "us" }
                Label { visible: wizard.step === 1; text: wizard.tr("Escolha o nome do mascote. A prévia de voz será exibida quando houver vozes instaladas.", "Choose the mascot name. Voice preview will appear when voices are installed."); color: "#94a3b8"; wrapMode: Text.WordWrap }
                Flow {
                    visible: wizard.step === 1
                    Layout.fillWidth: true
                    spacing: 12
                    Repeater {
                        model: ["Guará", "Tupã", "Jaci", "Iara", "Ipê", "Boto", "Curió", "Arara"]
                        delegate: Rectangle {
                            width: 140; height: 96; radius: 12
                            color: "#1e2433"
                            border.color: wizard.mascot === modelData ? "#00e5ff" : "#3b494c"
                            Label { anchors.centerIn: parent; text: modelData; color: "#f1f5f9"; font.pixelSize: 18 }
                            MouseArea { anchors.fill: parent; onClicked: { customName.clear(); wizard.mascot = modelData } }
                        }
                    }
                }
                TextField { id: customName; visible: wizard.step === 1; placeholderText: "Nome personalizado (opcional)"; maximumLength: 24; onTextChanged: { if (text.trim().length) wizard.mascot = text.trim() } }
                Label { visible: wizard.step === 2; text: wizard.tr("Selecione o perfil. A instalação disponível será iniciada em segundo plano e o status mostrará pendências.", "Choose a profile. Available installers run in the background and the status shows pending items."); color: "#94a3b8"; wrapMode: Text.WordWrap }
                Flow {
                    visible: wizard.step === 2
                    Layout.fillWidth: true
                    spacing: 12
                    Repeater {
                        model: ["web", "backend", "gamedev", "devops", "ai", "minimal"]
                        delegate: Rectangle {
                            width: 220; height: 86; radius: 10
                            color: "#1e2433"
                            border.color: wizard.profile === modelData ? "#00e5ff" : "#3b494c"
                            Label { anchors.centerIn: parent; text: modelData; color: "#f1f5f9"; font.pixelSize: 18 }
                            MouseArea { anchors.fill: parent; onClicked: wizard.profile = modelData }
                        }
                    }
                }
                Label { visible: wizard.step === 3; text: wizard.tr("Autentique sua conta GitHub no terminal. Chaves de API só podem ser cadastradas no KWallet.", "Sign in to GitHub in the terminal. API keys are stored only in KWallet."); color: "#94a3b8"; wrapMode: Text.WordWrap }
                Button { visible: wizard.step === 3; text: "Abrir gh auth login"; onClicked: wizard.status = bridge.githubLogin() }
                ComboBox { id: provider; visible: wizard.step === 3; model: ["anthropic", "openai", "openrouter", "nous"] }
                TextField { id: apiKey; visible: wizard.step === 3; placeholderText: "Chave de API (opcional)"; echoMode: TextInput.Password; Layout.fillWidth: true }
                Button { visible: wizard.step === 3; text: "Salvar no KWallet"; onClicked: { wizard.status = bridge.storeKey(provider.currentText, apiKey.text); apiKey.clear() } }
                Label { visible: wizard.step === 4; text: wizard.tr("O Unity Hub pode ser instalado em segundo plano com o instalador oficial.", "Unity Hub can be installed in the background using its official installer."); color: "#94a3b8"; wrapMode: Text.WordWrap }
                CheckBox { visible: wizard.step === 4; text: "Instalar Unity Hub"; onCheckedChanged: wizard.unity = checked }
                Label { visible: wizard.step === 5; text: "Mascote: " + wizard.mascot + "\nPerfil: " + wizard.profile + "\nIdioma: " + wizard.language + "\nTeclado: " + wizard.keyboard + "\nUnity Hub: " + (wizard.unity ? "sim" : "não"); color: "#f1f5f9"; font.pixelSize: 18 }
                Label { visible: wizard.step === 5; text: wizard.tr("Reproduzir no terminal", "Reproduce in terminal"); color: "#94a3b8" }
                Label { visible: wizard.step === 5; text: wizard.setupCommand; color: "#00e5ff"; font.family: "monospace"; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                Button { visible: wizard.step === 5; text: wizard.tr("Copiar comando", "Copy command"); onClicked: bridge.copyText(wizard.setupCommand) }
                Label { visible: wizard.step === 5; text: wizard.tr("Progresso da instalação", "Installation progress"); color: "#94a3b8" }
                ProgressBar { visible: wizard.step === 5; value: wizard.setupProgress; Layout.fillWidth: true }
                Item { Layout.fillHeight: true }
                Label { text: wizard.status; color: "#94a3b8"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            }
        }
    }

    Loader {
        id: preflightLoader
        anchors.fill: parent
        visible: wizard.showPreflight
        active: wizard.showPreflight
        source: "Preflight.qml"
        Connections {
            target: preflightLoader.item
            function onContinueRequested() { wizard.showPreflight = false }
        }
    }

    footer: Rectangle {
        height: 72
        color: "#161b26"
        visible: !wizard.showPreflight
        RowLayout {
            anchors.fill: parent
            anchors.margins: 16
            Button { text: wizard.tr("Voltar", "Back"); enabled: wizard.step > 0 && !wizard.finished; onClicked: wizard.step-- }
            Item { Layout.fillWidth: true }
            Button { text: wizard.tr("Pular wizard", "Skip wizard"); onClicked: { wizard.profile = "minimal"; wizard.unity = false; wizard.status = bridge.finish(wizard.mascot, wizard.profile, wizard.language, wizard.keyboard, false); wizard.finished = wizard.status.indexOf("iniciada") >= 0 } }
            Button {
                text: wizard.step === 5 ? wizard.tr("Finalizar e entrar no desktop", "Finish and enter desktop") : wizard.tr("Avançar", "Next")
                onClicked: {
                    if (wizard.step < 5) wizard.step++
                    else { wizard.status = bridge.finish(wizard.mascot, wizard.profile, wizard.language, wizard.keyboard, wizard.unity); wizard.finished = wizard.status.indexOf("iniciada") >= 0 }
                }
            }
            Button { visible: wizard.finished; text: wizard.tr("Entrar no desktop", "Enter desktop"); onClicked: wizard.close() }
        }
    }
}

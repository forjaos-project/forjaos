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
    property bool finished: false
    property bool showPreflight: true
    readonly property var stepNames: ["Idioma", "Mascote", "Perfil", "Contas", "Instaladores", "Resumo"]
    Timer { interval: 1200; repeat: true; running: wizard.finished; onTriggered: wizard.status = bridge.setupStatus() }

    header: Rectangle {
        height: 64
        color: "#161b26"
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 32
            anchors.rightMargin: 32
            Label { text: "ForjaOS Setup"; color: "#f1f5f9"; font.pixelSize: 22; font.bold: true }
            Item { Layout.fillWidth: true }
            Label { text: "PRIMEIRO BOOT"; color: "#00e5ff" }
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
                Label { visible: wizard.step === 0; text: "Escolha o idioma. O teclado pode ser ajustado nas configurações do Plasma."; color: "#94a3b8"; wrapMode: Text.WordWrap }
                ComboBox { visible: wizard.step === 0; model: ["Português (Brasil)", "English (US)"]; onCurrentIndexChanged: wizard.language = currentIndex === 0 ? "pt-BR" : "en-US" }
                ComboBox { visible: wizard.step === 0; model: ["Teclado brasileiro (ABNT2)", "US International"]; onCurrentIndexChanged: wizard.keyboard = currentIndex === 0 ? "br" : "us" }
                Label { visible: wizard.step === 1; text: "Escolha o nome do Guará. Voz e wake word entram em uma etapa futura."; color: "#94a3b8"; wrapMode: Text.WordWrap }
                ComboBox { visible: wizard.step === 1; model: ["Guará", "Tupã", "Jaci", "Iara", "Ipê", "Boto", "Curió", "Arara"]; onCurrentTextChanged: wizard.mascot = currentText }
                Label { visible: wizard.step === 2; text: "Selecione o perfil. A instalação dos pacotes depende da F2-002."; color: "#94a3b8"; wrapMode: Text.WordWrap }
                ComboBox { visible: wizard.step === 2; model: ["minimal", "web", "backend", "gamedev", "devops", "ai"]; onCurrentTextChanged: wizard.profile = currentText }
                Label { visible: wizard.step === 3; text: "Autentique sua conta GitHub no terminal. Chaves de API só podem ser cadastradas no KWallet."; color: "#94a3b8"; wrapMode: Text.WordWrap }
                Button { visible: wizard.step === 3; text: "Abrir gh auth login"; onClicked: wizard.status = bridge.githubLogin() }
                ComboBox { id: provider; visible: wizard.step === 3; model: ["anthropic", "openai", "openrouter", "nous"] }
                TextField { id: apiKey; visible: wizard.step === 3; placeholderText: "Chave de API (opcional)"; echoMode: TextInput.Password; Layout.fillWidth: true }
                Button { visible: wizard.step === 3; text: "Salvar no KWallet"; onClicked: { wizard.status = bridge.storeKey(provider.currentText, apiKey.text); apiKey.clear() } }
                Label { visible: wizard.step === 4; text: "O Unity Hub pode ser instalado em segundo plano com o instalador oficial."; color: "#94a3b8"; wrapMode: Text.WordWrap }
                CheckBox { visible: wizard.step === 4; text: "Instalar Unity Hub"; onCheckedChanged: wizard.unity = checked }
                Label { visible: wizard.step === 5; text: "Mascote: " + wizard.mascot + "\nPerfil: " + wizard.profile + "\nIdioma: " + wizard.language + "\nTeclado: " + wizard.keyboard + "\nUnity Hub: " + (wizard.unity ? "sim" : "não"); color: "#f1f5f9"; font.pixelSize: 18 }
                Label { visible: wizard.step === 5; text: "forja setup --profile " + wizard.profile + " --mascot " + wizard.mascot.toLowerCase(); color: "#00e5ff"; font.family: "monospace" }
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
            Button { text: "Voltar"; enabled: wizard.step > 0 && !wizard.finished; onClicked: wizard.step-- }
            Item { Layout.fillWidth: true }
            Button { text: "Pular wizard"; onClicked: { wizard.profile = "minimal"; wizard.unity = false; wizard.status = bridge.finish(wizard.mascot, wizard.profile, wizard.language, wizard.keyboard, false); wizard.finished = wizard.status.indexOf("iniciada") >= 0 } }
            Button {
                text: wizard.step === 5 ? "Finalizar e entrar no desktop" : "Avançar"
                onClicked: {
                    if (wizard.step < 5) wizard.step++
                    else { wizard.status = bridge.finish(wizard.mascot, wizard.profile, wizard.language, wizard.keyboard, wizard.unity); wizard.finished = wizard.status.indexOf("iniciada") >= 0 }
                }
            }
            Button { visible: wizard.finished; text: "Entrar no desktop"; onClicked: wizard.close() }
        }
    }
}

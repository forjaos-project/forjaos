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
    property bool claudeCode: false
    property bool devcontainers: false
    property bool vscodeDevcontainers: false
    property var keyProviders: []
    property bool githubRequested: false
    property string status: ""
    property real setupProgress: 0
    property string setupLog: ""
    property bool finished: false
    property bool showPreflight: true
    function tr(pt, en) { return language === "pt-BR" ? pt : en }
    readonly property string setupCommand: "forja setup --profile " + profile + " --mascot "
        + JSON.stringify(mascot) + " --language " + language + " --keyboard " + keyboard
        + (unity ? " --unity" : "") + (claudeCode ? " --claude-code" : "")
        + (githubRequested ? " --github" : "")
        + (devcontainers ? " --devcontainers" : "")
        + (vscodeDevcontainers ? " --vscode-devcontainers" : "")
        + keyProviders.map(function(provider) { return " --api-key " + provider }).join("")
    readonly property var stepNames: language === "pt-BR"
        ? ["Idioma", "Mascote", "Perfil", "Contas", "Instaladores", "Resumo"]
        : ["Language", "Mascot", "Profile", "Accounts", "Installers", "Summary"]
    Timer { interval: 1200; repeat: true; running: wizard.finished; onTriggered: { wizard.status = bridge.setupStatus(); wizard.setupProgress = bridge.setupProgress(); wizard.setupLog = bridge.setupLog() } }

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
                Label { visible: wizard.step === 1; text: wizard.tr("Escolha o nome do mascote e, se quiser, baixe uma das vozes locais pt-BR licenciadas em CC0.", "Choose the mascot name and, optionally, download one of the local pt-BR voices licensed CC0."); color: "#94a3b8"; wrapMode: Text.WordWrap }
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
                Label { visible: wizard.step === 1; text: wizard.tr("Voz local do Guará", "Guará local voice"); color: "#f1f5f9" }
                ComboBox { id: voiceChoice; visible: wizard.step === 1; model: ["pt_BR-cadu-medium", "pt_BR-jeff-medium"]; Layout.fillWidth: true }
                Button { visible: wizard.step === 1; text: wizard.tr("Baixar e selecionar voz", "Download and select voice"); enabled: bridge.voiceStatus.indexOf("Baixando") !== 0; onClicked: bridge.downloadVoice(voiceChoice.currentText) }
                Label { visible: wizard.step === 1; text: bridge.voiceStatus; color: "#94a3b8"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Label { visible: wizard.step === 2; text: wizard.tr("Selecione o perfil. O primeiro boot prepara zsh, Starship, Homebrew, Git via KWallet e Podman rootless. As instalações escolhidas rodam em segundo plano.", "Choose a profile. First boot prepares zsh, Starship, Homebrew, Git via KWallet, and rootless Podman. Selected installs run in the background."); color: "#94a3b8"; wrapMode: Text.WordWrap }
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
                Label {
                    visible: wizard.step === 2
                    text: wizard.profile === "web" ? "Node · pnpm · Chrome (RPM oficial em Distrobox) · Postman (arquivo oficial)"
                        : wizard.profile === "backend" ? "Java · Go · Python · PostgreSQL container · DBeaver"
                        : wizard.profile === "gamedev" ? "Godot · templates de exportação · Blender · Krita · Unity opcional"
                        : wizard.profile === "devops" ? "kubectl · k9s · Helm · Terraform · AWS · GCP · Azure"
                        : wizard.profile === "ai" ? "Ollama · Hermes Agent · Codex CLI · Jupyter · modelo sugerido: Qwen3 8B Q4"
                        : "Base sem ferramentas adicionais"
                    color: "#94a3b8"
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                Label { visible: wizard.step === 3; text: wizard.tr("Autentique sua conta GitHub no terminal. O Git usa libsecret e o agente SSH integra as chaves ao KWallet.", "Sign in to GitHub in the terminal. Git uses libsecret and the SSH agent integrates keys with KWallet."); color: "#94a3b8"; wrapMode: Text.WordWrap }
                Button { visible: wizard.step === 3; text: "Abrir gh auth login"; onClicked: { wizard.status = bridge.githubLogin(); wizard.githubRequested = wizard.status.indexOf("aberta") >= 0 } }
                Button { visible: wizard.step === 3; text: "Adicionar chaves SSH ao agente/KWallet"; onClicked: wizard.status = bridge.sshAdd() }
                ComboBox { id: provider; visible: wizard.step === 3; model: ["anthropic", "openai", "openrouter", "nous"] }
                TextField { id: apiKey; visible: wizard.step === 3; placeholderText: "Chave de API (opcional)"; echoMode: TextInput.Password; Layout.fillWidth: true }
                Button { visible: wizard.step === 3; text: "Salvar no KWallet"; onClicked: { wizard.status = bridge.storeKey(provider.currentText, apiKey.text); if (wizard.status === "Chave salva no KWallet." && wizard.keyProviders.indexOf(provider.currentText) < 0) wizard.keyProviders = wizard.keyProviders.concat([provider.currentText]); apiKey.clear() } }
                Label { visible: wizard.step === 4; text: wizard.tr("Instaladores opcionais executam em segundo plano. Docker CE usa a fonte oficial, exige senha de administrador e reinicialização; Podman segue como padrão.", "Optional installers run in the background. Docker CE uses its official source, requires administrator authentication and a reboot; Podman remains the default."); color: "#94a3b8"; wrapMode: Text.WordWrap }
                CheckBox { visible: wizard.step === 4; text: "Instalar Unity Hub"; onCheckedChanged: wizard.unity = checked }
                CheckBox { visible: wizard.step === 4; text: "Instalar Claude Code"; onCheckedChanged: wizard.claudeCode = checked }
                CheckBox { visible: wizard.step === 4; text: "Instalar Dev Containers CLI"; onCheckedChanged: wizard.devcontainers = checked }
                CheckBox { visible: wizard.step === 4; text: "Instalar VS Code + extensão Dev Containers (software Microsoft)"; onCheckedChanged: wizard.vscodeDevcontainers = checked }
                Button { visible: wizard.step === 4; text: "Instalar Docker CE rootless (opcional)"; onClicked: wizard.status = bridge.dockerSetup() }
                Label { visible: wizard.step === 5; text: "Mascote: " + wizard.mascot + "\nPerfil: " + wizard.profile + "\nIdioma: " + wizard.language + "\nTeclado: " + wizard.keyboard + "\nUnity Hub: " + (wizard.unity ? "sim" : "não") + "\nClaude Code: " + (wizard.claudeCode ? "sim" : "não") + "\nDev Containers CLI: " + (wizard.devcontainers || wizard.vscodeDevcontainers ? "sim" : "não") + "\nVS Code proprietário: " + (wizard.vscodeDevcontainers ? "sim" : "não") + "\nChaves no KWallet: " + (wizard.keyProviders.length ? wizard.keyProviders.join(", ") : "nenhuma"); color: "#f1f5f9"; font.pixelSize: 18 }
                Label { visible: wizard.step === 5; text: wizard.tr("Reproduzir no terminal", "Reproduce in terminal"); color: "#94a3b8" }
                Label { visible: wizard.step === 5; text: wizard.setupCommand; color: "#00e5ff"; font.family: "monospace"; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                Label { visible: wizard.step === 5 && wizard.keyProviders.length > 0; text: wizard.keyProviders.map(function(provider) { return "forja keys set " + provider }).join("\n"); color: "#00e5ff"; font.family: "monospace" }
                Label { visible: wizard.step === 5; text: "gh auth login"; color: "#00e5ff"; font.family: "monospace" }
                Button { visible: wizard.step === 5; text: wizard.tr("Copiar comando", "Copy command"); onClicked: bridge.copyText(wizard.setupCommand) }
                Label { visible: wizard.step === 5; text: wizard.tr("Progresso da instalação", "Installation progress"); color: "#94a3b8" }
                ProgressBar { visible: wizard.step === 5; value: wizard.setupProgress; Layout.fillWidth: true }
                Rectangle {
                    visible: wizard.step === 5
                    color: "#080b11"
                    radius: 8
                    Layout.fillWidth: true
                    Layout.preferredHeight: 128
                    Label { anchors.fill: parent; anchors.margins: 12; text: wizard.setupLog || wizard.tr("Aguardando instalação", "Waiting for installation"); color: "#94a3b8"; font.family: "monospace"; wrapMode: Text.WordWrap }
                }
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
            Button { text: wizard.tr("Pular wizard", "Skip wizard"); enabled: !wizard.finished; onClicked: { wizard.profile = "minimal"; wizard.unity = false; wizard.claudeCode = false; wizard.devcontainers = false; wizard.vscodeDevcontainers = false; wizard.githubRequested = false; wizard.status = bridge.finish(wizard.mascot, wizard.profile, wizard.language, wizard.keyboard, false, false, false, false, false); wizard.finished = wizard.status.indexOf("iniciada") >= 0 } }
            Button {
                text: wizard.step === 5 ? wizard.tr("Finalizar e entrar no desktop", "Finish and enter desktop") : wizard.tr("Avançar", "Next")
                enabled: !wizard.finished
                onClicked: {
                    if (wizard.step < 5) wizard.step++
                    else { wizard.status = bridge.finish(wizard.mascot, wizard.profile, wizard.language, wizard.keyboard, wizard.githubRequested, wizard.unity, wizard.claudeCode, wizard.devcontainers, wizard.vscodeDevcontainers); wizard.finished = wizard.status.indexOf("iniciada") >= 0 }
                }
            }
            Button { visible: wizard.finished; text: wizard.tr("Entrar no desktop", "Enter desktop"); onClicked: wizard.close() }
        }
    }
}

pragma Translator: "main"

import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

Window {
    id: root
    width: 520
    height: hero.overlayHeight
    x: hero.overlayX
    y: hero.overlayY
    visible: false
    color: "transparent"
    flags: Qt.Popup | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    title: qsTr("ForjaOS — Central de Comando")
    property bool receivedActivation: false

    onActiveChanged: {
        if (active) receivedActivation = true
        else if (receivedActivation && visible) close()
    }
    onClosing: hero.closeOverlay()
    onVisibleChanged: {
        if (visible) promptInput.forceActiveFocus()
    }

    Shortcut {
        sequence: "Esc"
        context: Qt.ApplicationShortcut
        onActivated: root.close()
    }

    Rectangle {
        anchors.fill: parent
        radius: 16
        color: "#0f131d"
        border.color: "#3b494c"
        border.width: 1
        clip: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Image {
                    source: "mascot/guara-idle.svg"
                    sourceSize.width: 42
                    sourceSize.height: 42
                    fillMode: Image.PreserveAspectFit
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        text: qsTr("CENTRAL DE COMANDO")
                        color: "#dfe2f0"
                        font.family: "Plus Jakarta Sans"
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                        font.letterSpacing: 1.1
                    }
                    Text {
                        text: qsTr("ForjaOS  /  HERO")
                        color: "#94a3b8"
                        font.family: "JetBrains Mono"
                        font.pixelSize: 10
                    }
                }

                Rectangle {
                    radius: 11
                    color: (hero.heroState === "ocioso" || hero.heroState === "idle") ? "#10141e" : "#1b1f2a"
                    border.color: (hero.heroState === "ocioso" || hero.heroState === "idle") ? "#10b981" : "#3b494c"
                    implicitWidth: stateLabel.implicitWidth + 18
                    implicitHeight: 28
                    Text {
                        id: stateLabel
                        anchors.centerIn: parent
                        text: "● " + hero.heroState
                        color: (hero.heroState === "ocioso" || hero.heroState === "idle") ? "#10b981" : "#94a3b8"
                        font.family: "JetBrains Mono"
                        font.pixelSize: 10
                    }
                }
                ToolButton {
                    id: microphoneButton
                    text: hero.microphoneEnabled ? qsTr("Desligar microfone") : qsTr("Ligar microfone")
                    icon.name: "audio-input-microphone"
                    Accessible.name: text
                    ToolTip.text: text
                    ToolTip.visible: hovered || activeFocus
                    onClicked: hero.toggleMicrophone()
                    contentItem: Text {
                        text: "●"
                        color: hero.microphoneEnabled ? "#10b981" : "#f43f5e"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 20
                    }
                }

                ToolButton {
                    id: closeButton
                    text: "×"
                    onClicked: root.close()
                    Accessible.name: qsTr("Fechar Central de Comando")
                    contentItem: Text {
                        text: closeButton.text
                        color: "#94a3b8"
                        font.pixelSize: 23
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 108
                radius: 16
                color: "#171b26"
                border.color: "#3b494c"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 14
                    Image {
                        id: assistantMascot
                        source: hero.busy ? "mascot/guara-thinking.svg" : "mascot/guara-idle.svg"
                        sourceSize.width: 66
                        sourceSize.height: 78
                        fillMode: Image.PreserveAspectFit
                        scale: hero.busy ? 1.05 : 1
                        Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.InOutQuad } }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 5
                        Text {
                            text: qsTr("Olá, sou o Guará.")
                            color: "#dfe2f0"
                            font.family: "Plus Jakarta Sans"
                            font.pixelSize: 16
                            font.weight: Font.DemiBold
                        }
                        Text {
                            Layout.fillWidth: true
                            text: hero.busy ? qsTr("Estou cuidando da sua solicitação…") : qsTr("Seu sistema, projetos e ferramentas em um só lugar.")
                            color: "#94a3b8"
                            font.family: "Plus Jakarta Sans"
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                        }
                        Text {
                            text: qsTr("Diga o que você precisa fazer")
                            color: "#00e5ff"
                            font.family: "JetBrains Mono"
                            font.pixelSize: 10
                        }
                    }
                }
            }

            ScrollView {
                id: statusScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                ColumnLayout {
                    width: statusScroll.availableWidth
                    spacing: 10

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 8
                        rowSpacing: 8
                        Repeater {
                            model: [
                                {title: qsTr("Wi-Fi"), value: hero.wifi, accent: hero.wifi === "desligado" || hero.wifi === "off" ? "#94a3b8" : "#00e5ff", prompt: hero.wifiPrompt},
                                {title: qsTr("Bluetooth"), value: hero.bluetooth, accent: hero.bluetooth === "desligado" || hero.bluetooth === "off" ? "#94a3b8" : "#8b5cf6", prompt: hero.bluetoothPrompt},
                                {title: qsTr("VPN"), value: hero.vpn, accent: hero.vpn === "desconectada" || hero.vpn === "disconnected" ? "#94a3b8" : "#38bdf8", prompt: hero.vpnPrompt},
                                {title: qsTr("Modo Jogo"), value: hero.gameMode, accent: hero.gameMode === "ativo" || hero.gameMode === "on" ? "#f97316" : "#94a3b8", prompt: hero.gameModePrompt},
                                {title: qsTr("Firewall"), value: hero.firewall, accent: hero.firewall === "ativo" || hero.firewall === "on" ? "#10b981" : "#94a3b8", prompt: ""},
                                {title: qsTr("Não perturbe"), value: hero.dnd, accent: "#94a3b8", prompt: ""}
                            ]
                            delegate: StatusTile {
                                required property var modelData
                                Layout.fillWidth: true
                                title: modelData.title
                                value: modelData.value
                                accent: modelData.accent
                                prompt: modelData.prompt
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Repeater {
                            model: [
                                {label: "CPU", value: hero.cpu, progress: parseInt(hero.cpu) >= 0 ? parseInt(hero.cpu) : -1, accent: "#00e5ff"},
                                {label: "RAM", value: hero.ram, progress: hero.ramPercent, accent: "#38bdf8"},
                                {label: "GPU", value: hero.gpu, progress: parseInt(hero.gpu) >= 0 ? parseInt(hero.gpu) : -1, accent: "#8b5cf6"},
                                {label: "VRAM", value: hero.vram, progress: hero.vramPercent, accent: "#f97316"}
                            ]
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.preferredHeight: 62
                                radius: 12
                                color: "#171b26"
                                border.color: "#3b494c"
                                Column {
                                    anchors.centerIn: parent
                                    spacing: 5
                                    Text {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: modelData.label
                                        color: "#94a3b8"
                                        font.family: "JetBrains Mono"
                                        font.pixelSize: 9
                                    }
                                    Text {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: modelData.value
                                        color: "#dfe2f0"
                                        font.family: "Plus Jakarta Sans"
                                        font.pixelSize: 14
                                        font.weight: Font.DemiBold
                                    }
                                    Rectangle {
                                        width: 44
                                        height: 4
                                        radius: 2
                                        color: "#1e2433"
                                        Rectangle {
                                            width: parent.width * Math.max(0, Math.min(100, modelData.progress)) / 100
                                            height: parent.height
                                            radius: 2
                                            color: modelData.accent
                                            visible: modelData.progress >= 0
                                        }
                                    }
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 10
                        rowSpacing: 10
                        StatusCard {
                            Layout.fillWidth: true
                            title: qsTr("Containers")
                            accent: "#8b5cf6"
                            lines: hero.containers.length ? hero.containers.map(item => item.name + "  ·  " + item.status) : [qsTr("Nenhum container em execução")]
                            action: qsTr("Abrir projetos")
                            prompt: "Mostre meus projetos de desenvolvimento."
                        }
                        StatusCard {
                            Layout.fillWidth: true
                            title: qsTr("Modelos locais")
                            accent: "#8b5cf6"
                            lines: hero.models.length ? hero.models : [qsTr("Nenhum modelo local detectado")]
                            action: qsTr("Ver modelos instalados")
                            prompt: "Liste os modelos locais instalados."
                        }
                    }
                    StatusCard {
                        Layout.fillWidth: true
                        title: qsTr("Segurança e logs")
                        accent: "#10b981"
                        lines: hero.securityServices.map(item => item.name + "  ·  " + item.status).concat(hero.audit.length ? hero.audit.map(item => item.tool + "  ·  " + item.decision) : [qsTr("Auditoria  ·  sem eventos recentes")])
                        action: qsTr("Consultar auditoria")
                        prompt: "Mostre os eventos recentes de auditoria, sem exibir prompts."
                    }
                    StatusCard {
                        Layout.fillWidth: true
                        title: qsTr("Rede")
                        accent: "#00e5ff"
                        lines: [qsTr("Recebido  ·  ") + hero.rxRate, qsTr("Enviado  ·  ") + hero.txRate, qsTr("Latência  ·  ") + hero.latency, qsTr("LAN  ·  ") + hero.lan]
                        action: qsTr("Abrir configurações de rede")
                        prompt: "Abra as configurações de rede do sistema."
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: conversationColumn.implicitHeight + 20
                Layout.maximumHeight: 148
                radius: 14
                color: "#171b26"
                border.color: "#3b494c"
                clip: true

                ColumnLayout {
                    id: conversationColumn
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 7

                    ListView {
                        id: conversation
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(contentHeight, 86)
                        visible: count > 0
                        clip: true
                        spacing: 5
                        model: ListModel { id: messages }
                        delegate: Column {
                            required property string question
                            required property string answer
                            required property string tool
                            required property string tier
                            required property string status
                            required property bool pending
                            width: conversation.width
                            spacing: 2
                            Text {
                                width: parent.width
                            text: qsTr("Você  ·  ") + question
                                color: "#94a3b8"
                                font.family: "Plus Jakarta Sans"
                                font.pixelSize: 10
                                elide: Text.ElideRight
                            }
                            Text {
                                width: parent.width
                                text: pending ? qsTr("Guará  ·  processando…") : qsTr("Guará  ·  ") + answer + (tool ? "  [" + tool + " · " + tier + "]" : "")
                                color: status === "erro" ? "#f43f5e" : "#dfe2f0"
                                font.family: "Plus Jakarta Sans"
                                font.pixelSize: 10
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TextField {
                            id: promptInput
                            Layout.fillWidth: true
                            placeholderText: qsTr("Pergunte ou solicite uma ação…")
                            color: "#dfe2f0"
                            placeholderTextColor: "#64748b"
                            font.family: "Plus Jakarta Sans"
                            font.pixelSize: 12
                            enabled: !hero.busy && hero.pendingId.length === 0
                            selectByMouse: true
                            background: Rectangle { color: "#0f131d"; radius: 10; border.color: promptInput.activeFocus ? "#00e5ff" : "#3b494c" }
                            Keys.onReturnPressed: sendPrompt()
                        }
                        Button {
                            id: pushToTalkButton
                            text: qsTr("Segure para falar")
                            enabled: hero.microphoneEnabled && !hero.busy && hero.pendingId.length === 0
                            onPressed: hero.startPushToTalk()
                            onReleased: hero.stopPushToTalk()
                            onCanceled: hero.stopPushToTalk()
                            Accessible.name: text
                            ToolTip.text: qsTr("A fala inicia uma conversa local com o HERO")
                            ToolTip.visible: hovered || activeFocus
                        }
                        Button {
                            id: sendButton
                            text: hero.busy ? "…" : qsTr("Enviar")
                            enabled: !hero.busy && hero.pendingId.length === 0 && promptInput.text.trim().length > 0
                            onClicked: sendPrompt()
                            background: Rectangle { radius: 10; color: parent.enabled ? "#00e5ff" : "#313540" }
                            contentItem: Text {
                                text: sendButton.text
                                color: sendButton.enabled ? "#00363d" : "#94a3b8"
                                font.family: "Plus Jakarta Sans"
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: hero.pendingId.length > 0
                        Text {
                            Layout.fillWidth: true
                            text: qsTr("Ação requer confirmação explícita")
                            color: "#f59e0b"
                            font.family: "Plus Jakarta Sans"
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                        }
                        Button {
                            id: rejectButton
                            text: qsTr("Recusar")
                            onClicked: hero.confirmAction(false)
                            background: Rectangle { radius: 8; color: "#1b1f2a"; border.color: "#3b494c" }
                            contentItem: Text { text: rejectButton.text; color: "#dfe2f0"; font.family: "Plus Jakarta Sans"; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        }
                        Button {
                            id: approveButton
                            text: qsTr("Confirmar")
                            onClicked: hero.confirmAction(true)
                            background: Rectangle { radius: 8; color: "#00e5ff" }
                            contentItem: Text { text: approveButton.text; color: "#00363d"; font.family: "Plus Jakarta Sans"; font.pixelSize: 10; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        }
                    }
                }
            }
        }
    }

    function sendPrompt() {
        const text = promptInput.text.trim()
        if (!text || hero.busy || hero.pendingId.length > 0) return
        promptInput.clear()
        hero.sendText(text)
    }

    Connections {
        target: hero
        function onVoiceTranscribed(text) {
            messages.append({question: text, answer: "", tool: "", tier: "", status: "pensando", pending: true})
            conversation.positionViewAtEnd()
        }
        function onVoiceAnswer(answer) {
            if (messages.count > 0 && messages.get(messages.count - 1).pending) {
                messages.setProperty(messages.count - 1, "answer", answer)
                messages.setProperty(messages.count - 1, "pending", false)
                messages.setProperty(messages.count - 1, "status", "ok")
            } else {
                messages.append({question: qsTr("Voz"), answer: answer, tool: "", tier: "", status: "ok", pending: false})
            }
            conversation.positionViewAtEnd()
        }
        function onVoiceError(message) {
            messages.append({question: qsTr("Áudio"), answer: message, tool: "", tier: "", status: "erro", pending: false})
            conversation.positionViewAtEnd()
        }
        function onVoiceIgnored() {
            messages.append({question: qsTr("Voz"), answer: qsTr("Gatilho ignorado: HERO ocupado."), tool: "", tier: "", status: "erro", pending: false})
            conversation.positionViewAtEnd()
        }
        function onMessageAdded(question, answer, tool, tier, status, pending) {
            if (pending) {
                messages.append({question: question, answer: answer, tool: tool, tier: tier, status: status, pending: true})
            } else if (messages.count > 0) {
                const index = messages.count - 1
                messages.setProperty(index, "answer", answer)
                messages.setProperty(index, "tool", tool)
                messages.setProperty(index, "tier", tier)
                messages.setProperty(index, "status", status)
                messages.setProperty(index, "pending", false)
            } else {
                messages.append({question: question, answer: answer, tool: tool, tier: tier, status: status, pending: false})
            }
            conversation.positionViewAtEnd()
        }
    }

    component StatusCard: Rectangle {
        id: card
        property string title
        property color accent: "#00e5ff"
        property var lines: []
        property string action
        property string prompt
        implicitHeight: cardColumn.implicitHeight + 24
        radius: 14
        color: "#171b26"
        border.color: "#3b494c"

        ColumnLayout {
            id: cardColumn
            anchors.fill: parent
            anchors.margins: 12
            spacing: 7
            RowLayout {
                Layout.fillWidth: true
                Rectangle { width: 7; height: 7; radius: 4; color: card.accent }
                Text {
                    Layout.fillWidth: true
                    text: card.title
                    color: "#dfe2f0"
                    font.family: "Plus Jakarta Sans"
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
            }
            Repeater {
                model: card.lines
                delegate: Text {
                    required property string modelData
                    Layout.fillWidth: true
                    text: modelData
                    color: "#94a3b8"
                    font.family: "JetBrains Mono"
                    font.pixelSize: 9
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }
            }
            Button {
                id: cardButton
                Layout.fillWidth: true
                text: card.action
                onClicked: hero.sendText(card.prompt)
                background: Rectangle { radius: 8; color: "#1b1f2a"; border.color: "#3b494c" }
                contentItem: Text {
                    text: cardButton.text
                    color: "#00e5ff"
                    font.family: "Plus Jakarta Sans"
                    font.pixelSize: 9
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
            }
        }
    }

    component StatusTile: Button {
        id: tile
        property string title
        property string value
        property color accent: "#00e5ff"
        property string prompt
        enabled: prompt.length > 0
        onClicked: hero.sendText(prompt)
        Layout.preferredHeight: 56
        background: Rectangle { radius: 8; color: "#10141e"; border.color: tile.activeFocus ? "#00e5ff" : "#3b494c" }
        Accessible.name: title + ", " + value
        contentItem: RowLayout {
            spacing: 8
            Rectangle { width: 6; height: 6; radius: 3; color: tile.accent }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text { text: tile.title; color: "#dfe2f0"; font.family: "Plus Jakarta Sans"; font.pixelSize: 11; font.weight: Font.DemiBold }
                Text { text: tile.value; color: "#94a3b8"; font.family: "JetBrains Mono"; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true }
            }
            Text {
                visible: tile.prompt.length > 0
                text: tile.prompt.length ? qsTr("Alterar") : ""
                color: "#00e5ff"
                font.family: "Plus Jakarta Sans"
                font.pixelSize: 9
            }
        }
    }
}

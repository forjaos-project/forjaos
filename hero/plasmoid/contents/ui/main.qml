import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid 2.0
import org.kde.kirigami as Kirigami
import org.forjaos.hero 1.0

PlasmoidItem {
    id: root
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    function mascotSource() {
        if (hero.state === "escutando" || hero.state === "gravando") return Qt.resolvedUrl("../images/guara-listening.svg")
        if (hero.state === "pensando" || hero.state === "transcrevendo") return Qt.resolvedUrl("../images/guara-thinking.svg")
        if (hero.state === "falando") return Qt.resolvedUrl("../images/guara-speaking.svg")
        if (hero.state === "erro") return Qt.resolvedUrl("../images/guara-error.svg")
        return Qt.resolvedUrl("../images/guara-idle.svg")
    }

    function stateColor() {
        if (hero.state === "escutando" || hero.state === "gravando") return "#00e5ff"
        if (hero.state === "pensando" || hero.state === "transcrevendo") return "#8b5cf6"
        if (hero.state === "falando") return "#f97316"
        if (hero.state === "erro" || hero.state === "indisponível") return "#f43f5e"
        return "#94a3b8"
    }

    function sendPrompt(input) {
        const query = input.trim()
        if (query.length === 0 || hero.busy) return false
        hero.askText(query)
        return true
    }

    HeroService {
        id: hero
    }

    toolTipMainText: qsTr("HERO · Guará")
    toolTipSubText: qsTr("Estado: %1").arg(hero.state)

    compactRepresentation: Item {
        implicitWidth: 32
        implicitHeight: 32

        Rectangle {
            anchors.centerIn: parent
            width: 32
            height: 32
            radius: 16
            color: "transparent"
            border.width: 2
            border.color: root.stateColor()
        }
        Image {
            anchors.centerIn: parent
            width: 24
            height: 24
            source: root.mascotSource()
            sourceSize: Qt.size(48, 48)
            smooth: true
            SequentialAnimation on scale {
                loops: Animation.Infinite
                NumberAnimation { to: 1.04; duration: 900; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1.0; duration: 900; easing.type: Easing.InOutSine }
            }
        }
        MouseArea {
            anchors.fill: parent
            onClicked: {
                plasmoid.expanded = !plasmoid.expanded
            }
        }
    }

    fullRepresentation: Rectangle {
        Layout.minimumWidth: 384
        Layout.minimumHeight: content.implicitHeight + 32
        Layout.preferredWidth: 384
        Layout.preferredHeight: content.implicitHeight + 32
        radius: 12
        color: "#161b26"
        border.width: 1
        border.color: Qt.rgba(0, 229 / 255, 255 / 255, 0.35)

        ColumnLayout {
            id: content
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Image {
                    Layout.preferredWidth: 56
                    Layout.preferredHeight: 56
                    source: root.mascotSource()
                    sourceSize: Qt.size(96, 96)
                    smooth: true
                    SequentialAnimation on scale {
                        loops: Animation.Infinite
                        NumberAnimation { to: 1.04; duration: 900; easing.type: Easing.InOutSine }
                        NumberAnimation { to: 1.0; duration: 900; easing.type: Easing.InOutSine }
                    }
                }
                ColumnLayout {
                    spacing: 2
                    Label {
                        text: qsTr("Guará")
                        color: "#dfe2f0"
                        font.family: "Plus Jakarta Sans"
                        font.pixelSize: 16
                        font.weight: Font.DemiBold
                    }
                    Label {
                        text: qsTr("HERO · herod · %1").arg(hero.state.toUpperCase())
                        color: "#94a3b8"
                        font.family: "JetBrains Mono"
                        font.pixelSize: 10
                    }
                }
                Item { Layout.fillWidth: true }
                ToolButton {
                    Layout.preferredWidth: 36
                    Layout.minimumWidth: 36
                    Layout.preferredHeight: 36
                    icon.name: "window-new"
                    text: qsTr("Abrir Central de Comando")
                    display: AbstractButton.IconOnly
                    Accessible.name: text
                    onClicked: hero.openOverlay()
                    ToolTip.text: text
                    ToolTip.visible: hovered || activeFocus
                    ToolTip.delay: 500
                    background: Rectangle {
                        radius: 8
                        color: parent.hovered || parent.activeFocus ? "#262a35" : "transparent"
                    }
                    contentItem: Kirigami.Icon {
                        source: "window-new"
                        color: "#dfe2f0"
                        width: 20
                        height: 20
                        anchors.centerIn: parent
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: Math.max(44, answerLabel.implicitHeight + 20)
                radius: 8
                color: "#10141e"
                border.color: "#3b494c"
                Label {
                    id: answerLabel
                    anchors.fill: parent
                    anchors.margins: 10
                    text: hero.lastAnswer || qsTr("Pergunte ou solicite uma ação ao HERO.")
                    color: "#dfe2f0"
                    wrapMode: Text.Wrap
                    font.pixelSize: 14
                    font.family: "Plus Jakarta Sans"
                }
            }

            RowLayout {
                Layout.fillWidth: true
                TextField {
                    id: prompt
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    Layout.preferredHeight: 40
                    placeholderText: qsTr("Pergunte ou solicite uma ação…")
                    placeholderTextColor: "#94a3b8"
                    font.family: "JetBrains Mono"
                    font.pixelSize: 12
                    color: "#dfe2f0"
                    background: Rectangle {
                        color: "#10141e"
                        radius: 8
                        border.width: 1
                        border.color: prompt.activeFocus ? "#00e5ff" : "#3b494c"
                    }
                    onAccepted: {
                        if (root.sendPrompt(text)) clear()
                    }
                }
                Button {
                    id: sendButton
                    text: qsTr("Enviar")
                    Layout.preferredWidth: 76
                    Layout.minimumWidth: 76
                    Layout.preferredHeight: 36
                    enabled: !hero.busy && prompt.text.trim().length > 0
                    background: Rectangle {
                        radius: 8
                        color: sendButton.enabled ? "#00e5ff" : "#262a35"
                    }
                    contentItem: Text {
                        text: sendButton.text
                        color: sendButton.enabled ? "#00363d" : "#94a3b8"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.family: "Plus Jakarta Sans"
                        font.pixelSize: 12
                    }
                    onClicked: {
                        if (root.sendPrompt(prompt.text)) prompt.clear()
                    }
                }
            }
        }

    }

    Plasmoid.contextualActions: [
        PlasmaCore.Action { text: qsTr("Abrir Central de Comando"); icon.name: "window-new"; onTriggered: hero.openOverlay() },
        PlasmaCore.Action { text: qsTr("Ativar Modo Texto"); icon.name: "edit-text"; onTriggered: plasmoid.expanded = true },
        PlasmaCore.Action { text: qsTr("Ativar Modo Jogo"); icon.name: "applications-games"; onTriggered: hero.askText(qsTr("Ative modo jogo")) }
    ]
}

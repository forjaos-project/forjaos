import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    width: 1120
    height: 760
    minimumWidth: 760
    minimumHeight: 520
    visible: true
    title: "Memória ForjaOS"
    color: "#11151b"

    header: TabBar {
        id: tabs
        background: Rectangle { color: "#1b222c" }
        TabButton { text: "Linha do tempo" }
        TabButton { text: "Grafo" }
        TabButton { text: "Busca" }
    }

    StackLayout {
        anchors.fill: parent
        currentIndex: tabs.currentIndex

        ScrollView {
            clip: true
            ListView {
                model: vault.timeline
                spacing: 10
                leftMargin: 20
                rightMargin: 20
                topMargin: 20
                bottomMargin: 20
                delegate: Rectangle {
                    required property var modelData
                    width: ListView.view.width - 40
                    height: card.implicitHeight + 24
                    radius: 10
                    color: "#1b222c"
                    ColumnLayout {
                        id: card
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6
                        Label { text: modelData.title; color: "#f3f6fa"; font.pixelSize: 17; font.bold: true }
                        Label { text: modelData.path; color: "#91a1b5"; font.pixelSize: 12 }
                        Label { text: modelData.excerpt; color: "#c4cdd8"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    }
                }
                Label {
                    anchors.centerIn: parent
                    visible: vault.timeline.length === 0
                    text: "O vault ainda não tem notas Markdown."
                    color: "#91a1b5"
                }
            }
        }

        Item {
            Canvas {
                id: graphCanvas
                anchors.fill: parent
                anchors.margins: 20
                property var graphNodes: vault.nodes
                property var graphLinks: vault.links
                onGraphNodesChanged: requestPaint()
                onGraphLinksChanged: requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx = getContext("2d")
                    ctx.reset()
                    const count = graphNodes.length
                    if (count === 0) return
                    const positions = new Map()
                    for (let i = 0; i < count; i++) {
                        const angle = i * 2.399963 + Math.PI
                        const radius = Math.sqrt((i + 0.5) / count) * Math.min(width, height) * 0.44
                        positions.set(graphNodes[i].id, [width / 2 + Math.cos(angle) * radius,
                                                         height / 2 + Math.sin(angle) * radius])
                    }
                    ctx.strokeStyle = "#405165"
                    ctx.lineWidth = 1
                    for (let i = 0; i < graphLinks.length; i++) {
                        const from = positions.get(graphLinks[i].source)
                        const to = positions.get(graphLinks[i].target)
                        if (!from || !to) continue
                        ctx.beginPath(); ctx.moveTo(from[0], from[1]); ctx.lineTo(to[0], to[1]); ctx.stroke()
                    }
                    for (let i = 0; i < count; i++) {
                        const point = positions.get(graphNodes[i].id)
                        ctx.beginPath(); ctx.arc(point[0], point[1], 4, 0, Math.PI * 2)
                        ctx.fillStyle = graphNodes[i].node_type === "note" ? "#ef9d42" : "#61b5c8"
                        ctx.fill()
                    }
                }
            }
            Label {
                anchors.centerIn: parent
                visible: vault.nodes.length === 0
                text: "Reconstrua o índice para gerar o grafo."
                color: "#91a1b5"
            }
            Label {
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 28
                text: vault.nodes.length + " nós · " + vault.links.length + " relações"
                color: "#91a1b5"
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 14
            RowLayout {
                Layout.fillWidth: true
                TextField {
                    id: query
                    Layout.fillWidth: true
                    placeholderText: "Buscar nas notas locais"
                    onAccepted: runSearch()
                    background: Rectangle { radius: 8; color: "#1b222c"; border.color: "#405165" }
                    color: "#f3f6fa"
                }
                Button { text: "Buscar"; onClicked: runSearch() }
            }
            ListView {
                id: results
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8
                model: ListModel { id: searchResults }
                delegate: Rectangle {
                    required property string title
                    required property string path
                    required property string excerpt
                    width: results.width
                    height: resultColumn.implicitHeight + 24
                    radius: 8
                    color: "#1b222c"
                    ColumnLayout {
                        id: resultColumn
                        anchors.fill: parent
                        anchors.margins: 12
                        Label { text: title; color: "#f3f6fa"; font.bold: true }
                        Label { text: path; color: "#91a1b5"; font.pixelSize: 12 }
                        Label { text: excerpt; color: "#c4cdd8"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    }
                }
                Label { anchors.centerIn: parent; visible: searchResults.count === 0; text: "Digite um termo para buscar."; color: "#91a1b5" }
            }
        }
    }

    function runSearch() {
        searchResults.clear()
        const matches = vault.search(query.text)
        for (let i = 0; i < matches.length; i++) searchResults.append(matches[i])
    }
}

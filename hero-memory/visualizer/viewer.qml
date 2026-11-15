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

    header: RowLayout {
        spacing: 0
        TabBar {
            id: tabs
            Layout.fillWidth: true
            background: Rectangle { color: "#1b222c" }
            TabButton { text: "Linha do tempo" }
            TabButton { text: "Grafo" }
            TabButton { text: "Busca" }
        }
        ToolButton {
            text: "Coletores"
            onClicked: collectorMenu.open()
        }
        Menu {
            id: collectorMenu
            Repeater {
                model: vault.collectors
                MenuItem {
                    required property var modelData
                    text: modelData.source + (modelData.available ? "" : " (indisponível)")
                    checkable: true
                    checked: modelData.enabled
                    enabled: modelData.available
                    onTriggered: {
                        if (!vault.setCollector(modelData.source, checked))
                            collectorMenu.close()
                    }
                }
            }
        }
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
            WorkerScript {
                id: graphLayoutWorker
                source: "GraphLayout.js"
                onMessage: function(messageObject) {
                    if (messageObject.generation === graphCanvas.layoutGeneration
                            && messageObject.positions.length === graphCanvas.graphNodes.length)
                        graphCanvas.layoutPositions = messageObject.positions
                }
            }
            Timer {
                id: graphLayoutTimer
                interval: 80
                repeat: false
                onTriggered: graphLayoutWorker.sendMessage({
                    nodes: graphCanvas.graphNodes,
                    links: graphCanvas.graphLinks,
                    generation: graphCanvas.layoutGeneration
                })
            }
            RowLayout {
                id: graphControls
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.margins: 12
                z: 1
                Label { text: "Grafo"; color: "#f3f6fa"; font.bold: true }
                ComboBox {
                    id: graphTypeFilter
                    model: ["Todos os tipos", "Notas", "Repositórios", "Commits", "Comandos", "Conversas", "Janelas", "Código"]
                    onActivated: graphCanvas.nodeTypeFilter = ["", "note", "repository", "commit", "command", "conversation", "window", "code"][currentIndex]
                }
                ComboBox {
                    id: graphDateFilter
                    model: ["Todo o período", "30 dias", "365 dias"]
                    onActivated: graphCanvas.dateRangeDays = [0, 30, 365][currentIndex]
                }
                ToolButton {
                    text: "−"
                    Accessible.name: "Reduzir zoom do grafo"
                    onClicked: graphCanvas.zoom = Math.max(0.25, graphCanvas.zoom / 1.2)
                }
                Label {
                    text: Math.round(graphCanvas.zoom * 100) + "%"
                    color: "#91a1b5"
                    Layout.minimumWidth: 48
                    horizontalAlignment: Text.AlignHCenter
                }
                ToolButton {
                    text: "+"
                    Accessible.name: "Aumentar zoom do grafo"
                    onClicked: graphCanvas.zoom = Math.min(4, graphCanvas.zoom * 1.2)
                }
                ToolButton {
                    text: "Centralizar"
                    onClicked: {
                        graphCanvas.zoom = 1
                        graphCanvas.panX = 0
                        graphCanvas.panY = 0
                    }
                }
                Label { text: "Arraste para mover · roda do mouse para zoom"; color: "#91a1b5"; font.pixelSize: 11 }
            }
            Canvas {
                id: graphCanvas
                anchors.fill: parent
                anchors.margins: 20
                anchors.topMargin: 58
                property var graphNodes: vault.nodes
                property var graphLinks: vault.links
                property real zoom: 1
                property real panX: 0
                property real panY: 0
                property string nodeTypeFilter: ""
                property int dateRangeDays: 0
                property int visibleNodeCount: 0
                property var layoutPositions: []
                property int layoutGeneration: 0
                Component.onCompleted: graphLayoutTimer.restart()
                onGraphNodesChanged: {
                    layoutGeneration++
                    layoutPositions = []
                    graphLayoutTimer.restart()
                    requestPaint()
                }
                onGraphLinksChanged: {
                    layoutGeneration++
                    layoutPositions = []
                    graphLayoutTimer.restart()
                    requestPaint()
                }
                onLayoutPositionsChanged: requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onZoomChanged: requestPaint()
                onPanXChanged: requestPaint()
                onPanYChanged: requestPaint()
                onNodeTypeFilterChanged: requestPaint()
                onDateRangeDaysChanged: requestPaint()
                WheelHandler {
                    onWheel: event => {
                        const factor = event.angleDelta.y > 0 ? 1.12 : 1 / 1.12
                        graphCanvas.zoom = Math.max(0.25, Math.min(4, graphCanvas.zoom * factor))
                    }
                }
                DragHandler {
                    target: null
                    property real previousX: 0
                    property real previousY: 0
                    onActiveChanged: {
                        if (active) {
                            previousX = translation.x
                            previousY = translation.y
                        }
                    }
                    onTranslationChanged: {
                        graphCanvas.panX += translation.x - previousX
                        graphCanvas.panY += translation.y - previousY
                        previousX = translation.x
                        previousY = translation.y
                    }
                }
                onPaint: {
                    const ctx = getContext("2d")
                    ctx.reset()
                    const visibleNodes = []
                    for (let i = 0; i < graphNodes.length; i++) {
                        const node = graphNodes[i]
                        if (nodeTypeFilter && node.node_type !== nodeTypeFilter) continue
                        if (dateRangeDays > 0) {
                            const modified = Number(node.modified_at || 0)
                            if (modified < Date.now() / 1000 - dateRangeDays * 86400) continue
                        }
                        visibleNodes.push({node: node, index: i})
                    }
                    visibleNodeCount = visibleNodes.length
                    const count = visibleNodes.length
                    if (count === 0) return
                    if (layoutPositions.length !== graphNodes.length) return
                    const positions = new Map()
                    const radiusScale = Math.min(width, height) * 0.44
                    for (let i = 0; i < count; i++) {
                        let point = layoutPositions[visibleNodes[i].index]
                        point = [point[0] * radiusScale, point[1] * radiusScale]
                        positions.set(visibleNodes[i].node.id, point)
                    }
                    ctx.translate(width / 2 + panX, height / 2 + panY)
                    ctx.scale(zoom, zoom)
                    ctx.strokeStyle = "#405165"
                    ctx.lineWidth = 1
                    for (let i = 0; i < graphLinks.length; i++) {
                        const from = positions.get(graphLinks[i].source)
                        const to = positions.get(graphLinks[i].target)
                        if (!from || !to) continue
                        ctx.beginPath(); ctx.moveTo(from[0], from[1]); ctx.lineTo(to[0], to[1]); ctx.stroke()
                    }
                    for (let i = 0; i < count; i++) {
                        const point = positions.get(visibleNodes[i].node.id)
                        ctx.beginPath(); ctx.arc(point[0], point[1], 4, 0, Math.PI * 2)
                        ctx.fillStyle = visibleNodes[i].node.node_type === "note" ? "#ef9d42" : "#61b5c8"
                        ctx.fill()
                    }
                }
            }
            Label {
                anchors.centerIn: parent
                visible: graphCanvas.visibleNodeCount === 0
                text: vault.nodes.length === 0 ? "Reconstrua o índice para gerar o grafo." : "Nenhum nó corresponde aos filtros."
                color: "#91a1b5"
            }
            Label {
                anchors.centerIn: parent
                visible: graphCanvas.visibleNodeCount > 0
                         && graphCanvas.layoutPositions.length !== graphCanvas.graphNodes.length
                text: "Organizando grafo..."
                color: "#91a1b5"
            }
            Label {
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 28
                text: graphCanvas.visibleNodeCount + " / " + vault.nodes.length + " nós · " + vault.links.length + " relações"
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

    footer: Label {
        padding: 8
        text: vault.collectorStatus
        color: "#91a1b5"
        background: Rectangle { color: "#1b222c" }
    }

    function runSearch() {
        searchResults.clear()
        const matches = vault.search(query.text)
        for (let i = 0; i < matches.length; i++) searchResults.append(matches[i])
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    width: 1440
    height: 900
    minimumWidth: 1280
    minimumHeight: 520
    visible: true
    title: "Memória ForjaOS"
    color: "#070a11"
    font.family: "Plus Jakarta Sans"
    property alias viewIndex: tabs.currentIndex
    palette.window: "#070a11"
    palette.base: "#10141e"
    palette.button: "#1e2433"
    palette.text: "#f1f5f9"
    palette.buttonText: "#f1f5f9"
    palette.highlight: "#00e5ff"
    palette.highlightedText: "#070a11"
    component ForgeButton: Button {
        id: control
        implicitHeight: 40
        contentItem: Text {
            text: control.text
            font: control.font
            color: control.highlighted ? "#00e5ff" : "#f1f5f9"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            opacity: control.enabled ? 1 : 0.4
        }
        background: Rectangle {
            radius: 8
            color: control.down ? "#1e2433" : control.hovered ? "#161b26" : "#10141e"
            border.color: control.highlighted || control.activeFocus ? "#00e5ff" : "#3b494c"
        }
    }
    property string selectedPath: ""
    property string selectedTitle: ""
    property string selectedPreview: ""
    property var selectedLinks: []
    function inspect(path, title) {
        selectedPath = path
        selectedTitle = title
        selectedPreview = vault.previewNote(path)
    }
    function sourceColor(kind) {
        return {command: "#00e5ff", commit: "#8b5cf6", conversation: "#f97316",
                window: "#94a3b8", note: "#10b981", repository: "#8b5cf6", code: "#38bdf8"}[kind] || "#94a3b8"
    }
    Shortcut { sequence: "Ctrl+1"; onActivated: tabs.currentIndex = 1 }
    Shortcut { sequence: "Ctrl+2"; onActivated: tabs.currentIndex = 0 }
    Shortcut { sequence: "Ctrl+3"; onActivated: tabs.currentIndex = 2 }
    Shortcut { sequence: "Ctrl+F"; onActivated: { tabs.currentIndex = 2; query.forceActiveFocus() } }


    header: RowLayout {
        height: 64
        spacing: 16
        Label { text: "Forja Memory · memd"; font.pixelSize: 20; font.bold: true; color: "#f1f5f9"; leftPadding: 24 }
        Label { text: "~/ForjaOS/vault"; font.family: "JetBrains Mono"; color: "#94a3b8"; Layout.fillWidth: true }
        Label { text: vault.nodes.length + " nós · " + vault.links.length + " relações"; color: "#00e5ff" }
        ForgeButton { text: "Atualizar"; onClicked: vault.refresh() }
        ForgeButton {
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

    Rectangle {
        id: sidebar
        width: 256
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        color: "#10141e"
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 16
            Label { text: "MEMÓRIA DO SISTEMA"; color: "#94a3b8"; font.pixelSize: 12 }
            TabBar {
                id: tabs
                visible: false
                TabButton { text: "Linha do tempo" }
                TabButton { text: "Grafo" }
                TabButton { text: "Busca" }
            }
            Repeater {
                model: ["Linha do tempo   Ctrl+2", "Grafo   Ctrl+1", "Busca   Ctrl+3"]
                delegate: ForgeButton {
                    required property int index
                    required property string modelData
                    text: modelData
                    Layout.fillWidth: true
                    highlighted: tabs.currentIndex === index
                    onClicked: tabs.currentIndex = index
                }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: "#3b494c" }
            Label { text: "COLETORES"; color: "#94a3b8"; font.pixelSize: 12 }
            Repeater {
                model: vault.collectors
                delegate: CheckBox {
                    required property var modelData
                    text: modelData.source
                    checked: modelData.enabled
                    enabled: modelData.available
                    onClicked: vault.setCollector(modelData.source, checked)
                }
            }
            Item { Layout.fillHeight: true }
            Label { text: "Dados locais · sem nuvem"; color: "#94a3b8" }
        }
    }
    Rectangle {
        id: inspector
        width: 380
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        color: "#10141e"
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 16
            Label { text: window.selectedPath ? "ENTIDADE SELECIONADA" : "PRÉVIA DO DIA"; color: "#00e5ff"; font.pixelSize: 12 }
            Label { text: window.selectedTitle || vault.day; color: "#f1f5f9"; font.pixelSize: 20; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Label { text: window.selectedPath || "daily/" + vault.day + ".md"; color: "#94a3b8"; font.family: "JetBrains Mono"; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
            ScrollView {
                Layout.fillHeight: true
                Layout.fillWidth: true
                TextArea {
                    readOnly: true
                    textFormat: TextEdit.PlainText
                    text: window.selectedPath ? window.selectedPreview || "Sem arquivo Markdown associado." : vault.preview || "Sem nota diária para esta data."
                    wrapMode: TextEdit.Wrap
                    color: "#bac9cc"
                    background: null
                }
            }
            ForgeButton {
                text: "Abrir no editor"
                enabled: (window.selectedPath ? window.selectedPreview : vault.preview).length > 0
                onClicked: vault.openNote(window.selectedPath || "daily/" + vault.day + ".md")
            }
            Label { text: "forja memory timeline"; color: "#94a3b8"; font.family: "JetBrains Mono" }
            Label { text: "CONEXÕES DIRETAS · " + window.selectedLinks.length; color: "#00e5ff"; visible: window.selectedLinks.length > 0 }
            ListView {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(180, contentHeight)
                clip: true
                model: window.selectedLinks
                delegate: Label {
                    required property var modelData
                    width: ListView.view.width
                    text: modelData.source + " → " + modelData.target
                    color: "#94a3b8"
                    elide: Text.ElideMiddle
                    height: 28
                }
            }
        }
    }
    StackLayout {
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.left: sidebar.right
        anchors.right: inspector.left
        currentIndex: tabs.currentIndex

        ColumnLayout {
            RowLayout {
                Layout.fillWidth: true
                Layout.margins: 16
                Label { text: "ATIVIDADE DO DIA"; color: "#f1f5f9"; font.bold: true }
                TextField { id: dayInput; text: vault.day; inputMask: "9999-99-99"; onAccepted: vault.selectDay(text) }
                ForgeButton { text: "Ir"; onClicked: vault.selectDay(dayInput.text) }
                Label { text: vault.timeline.length + " notas"; color: "#94a3b8" }
            }
            ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
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
                    radius: 8
                    color: "#10141e"
                    Rectangle { width: 4; height: parent.height; color: window.sourceColor(modelData.node_type) }
                    TapHandler { onTapped: window.inspect(modelData.path, modelData.title) }
                    ColumnLayout {
                        id: card
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6
                        Label { text: new Date(modelData.modified * 1000).toLocaleTimeString(Qt.locale(), "hh:mm") + " · " + modelData.title; Layout.fillWidth: true; elide: Text.ElideRight; color: "#f1f5f9"; font.pixelSize: 17; font.bold: true }
                        Label { text: modelData.path; color: "#94a3b8"; font.pixelSize: 12 }
                        Label { text: modelData.excerpt; color: "#bac9cc"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    }
                }
                Label {
                    anchors.centerIn: parent
                    visible: vault.timeline.length === 0
                    text: "Nenhuma nota indexada nesta data."
                    color: "#94a3b8"
                }
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
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 12
                z: 1

                ComboBox {
                    Layout.preferredWidth: 144
                    id: graphTypeFilter
                    model: ["Todos os tipos", "Notas", "Repositórios", "Commits", "Comandos", "Conversas", "Janelas", "Código"]
                    onActivated: graphCanvas.nodeTypeFilter = ["", "note", "repository", "commit", "command", "conversation", "window", "code"][currentIndex]
                }
                ComboBox {
                    Layout.preferredWidth: 128
                    id: graphDateFilter
                    model: ["Todo o período", "30 dias", "365 dias"]
                    onActivated: graphCanvas.dateRangeDays = [0, 30, 365][currentIndex]
                }
                ForgeButton {
                    text: "−"
                    Accessible.name: "Reduzir zoom do grafo"
                    onClicked: graphCanvas.zoom = Math.max(0.25, graphCanvas.zoom / 1.2)
                }
                Label {
                    text: Math.round(graphCanvas.zoom * 100) + "%"
                    color: "#94a3b8"
                    Layout.minimumWidth: 48
                    horizontalAlignment: Text.AlignHCenter
                }
                ForgeButton {
                    text: "+"
                    Accessible.name: "Aumentar zoom do grafo"
                    onClicked: graphCanvas.zoom = Math.min(4, graphCanvas.zoom * 1.2)
                }
                ForgeButton {
                    text: "Centralizar"
                    onClicked: {
                        graphCanvas.zoom = 1
                        graphCanvas.panX = 0
                        graphCanvas.panY = 0
                    }
                }

            }
            Canvas {
                id: graphCanvas
                objectName: "graphCanvas"
                anchors.fill: parent
                anchors.margins: 20
                anchors.topMargin: 100
                property var graphNodes: vault.nodes
                property string selectedId: ""
                property var screenPositions: []
                TapHandler {
                    onTapped: function(eventPoint) {
                        let closest = null
                        let distance = 144
                        for (const entry of graphCanvas.screenPositions) {
                            const dx = entry.x - eventPoint.position.x
                            const dy = entry.y - eventPoint.position.y
                            if (dx * dx + dy * dy < distance) {
                                closest = entry.node
                                distance = dx * dx + dy * dy
                            }
                        }
                        if (closest) {
                            graphCanvas.selectedId = closest.id
                            window.selectedLinks = vault.related(closest.id)
                            window.inspect(closest.source_file || closest.id, closest.label || closest.id)
                            graphCanvas.requestPaint()
                        }
                    }
                }
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
                    screenPositions = []
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
                    ctx.strokeStyle = "#3b494c"
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
                        const node = visibleNodes[i].node
                        screenPositions.push({node: node, x: width / 2 + panX + point[0] * zoom, y: height / 2 + panY + point[1] * zoom})
                        ctx.fillStyle = window.sourceColor(node.node_type)
                        if (node.id === selectedId) {
                            ctx.strokeStyle = "#f1f5f9"
                            ctx.stroke()
                            ctx.fillText(node.label || node.id, point[0] + 8, point[1] - 8)
                        }
                        ctx.fill()
                    }
                }
            }
            Label {
                anchors.centerIn: parent
                visible: graphCanvas.visibleNodeCount === 0
                text: vault.nodes.length === 0 ? "Reconstrua o índice para gerar o grafo." : "Nenhum nó corresponde aos filtros."
                color: "#94a3b8"
            }
            Label {
                anchors.centerIn: parent
                visible: graphCanvas.visibleNodeCount > 0
                         && graphCanvas.layoutPositions.length !== graphCanvas.graphNodes.length
                text: "Organizando grafo..."
                color: "#94a3b8"
            }
            Label {
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: 28
                text: graphCanvas.visibleNodeCount + " / " + vault.nodes.length + " nós · " + vault.links.length + " relações"
                color: "#94a3b8"
            }
        }

        ColumnLayout {
            Layout.margins: 20
            spacing: 14
            RowLayout {
                Layout.fillWidth: true
                TextField {
                    id: query
                    Layout.fillWidth: true
                    placeholderText: "Buscar nas notas locais"
                    onAccepted: runSearch()
                    background: Rectangle { radius: 8; color: "#10141e"; border.color: "#3b494c" }
                    color: "#f1f5f9"
                }
                ForgeButton { text: "Buscar"; onClicked: runSearch() }
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
                    color: "#10141e"
                    TapHandler { onTapped: window.inspect(path, title) }
                    ColumnLayout {
                        id: resultColumn
                        anchors.fill: parent
                        anchors.margins: 12
                        Label { text: title; color: "#f1f5f9"; font.bold: true }
                        Label { text: path; color: "#94a3b8"; font.pixelSize: 12 }
                        Label { text: excerpt; color: "#bac9cc"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    }
                }
                Label { anchors.centerIn: parent; visible: searchResults.count === 0; text: "Digite um termo para buscar."; color: "#94a3b8" }
            }
        }
    }

    footer: Label {
        padding: 8
        text: vault.collectorStatus
        color: "#94a3b8"
        background: Rectangle { color: "#10141e" }
    }

    function runSearch() {
        searchResults.clear()
        const matches = vault.search(query.text)
        for (let i = 0; i < matches.length; i++) searchResults.append(matches[i])
    }
}

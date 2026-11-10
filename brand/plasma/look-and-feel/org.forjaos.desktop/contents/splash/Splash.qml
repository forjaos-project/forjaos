import QtQuick

Rectangle {
    id: root
    color: "#070a11"
    property int stage

    Image {
        id: mark
        anchors.centerIn: parent
        width: 128
        height: 128
        source: "file:///usr/share/pixmaps/system-logo-white.png"
        fillMode: Image.PreserveAspectFit
        opacity: root.stage >= 5 ? 0 : 1
        Behavior on opacity { NumberAnimation { duration: 320 } }
    }
    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: mark.bottom
        anchors.topMargin: 32
        width: root.stage >= 2 ? 64 : 0
        height: 3
        radius: 1
        color: "#00e5ff"
        Behavior on width { NumberAnimation { duration: 320 } }
    }
}

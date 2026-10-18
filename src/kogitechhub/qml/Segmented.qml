import QtQuick

// Selettore a segmenti per valori numerici (frequenza di report).
Rectangle {
    id: root
    property var options: []
    property int value: 0
    property string suffix: ""
    signal picked(int v)

    height: 42
    radius: 12
    color: theme.bg
    border.width: 1
    border.color: theme.line

    Row {
        anchors.fill: parent
        anchors.margins: 3
        Repeater {
            model: root.options
            delegate: Rectangle {
                required property var modelData
                width: root.options.length > 0 ? (root.width - 6) / root.options.length : 0
                height: root.height - 6
                radius: 9
                color: modelData === root.value ? theme.accent : (seg.containsMouse ? theme.panelHi : "transparent")
                Txt {
                    anchors.centerIn: parent
                    text: modelData + root.suffix
                    font.pixelSize: 13
                    font.weight: modelData === root.value ? Font.DemiBold : Font.Normal
                    color: modelData === root.value ? "#FFFFFF" : theme.muted
                }
                MouseArea {
                    id: seg
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.picked(modelData)
                }
            }
        }
    }
}

import QtQuick

// Slider continuo con pallino: luminosità, velocità, sidetone.
Item {
    id: root
    property int value: 0
    property int from: 0
    property int to: 100
    property int step: 1
    property string suffix: ""
    property bool interactive: true
    signal moved(int value)

    implicitHeight: 34
    readonly property real ratio: to > from
                                     ? Math.max(0, Math.min(1, (value - from) / (to - from)))
                                     : 0

    Rectangle {
        id: track
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width
        height: 6
        radius: 3
        color: theme.bg
        border.width: 1
        border.color: theme.line

        Rectangle {
            width: Math.max(6, track.width * root.ratio)
            height: parent.height
            radius: 3
            color: root.interactive ? theme.accent : theme.dim
        }
        Rectangle {
            x: Math.max(0, Math.min(track.width - width, track.width * root.ratio - width / 2))
            anchors.verticalCenter: parent.verticalCenter
            width: 18; height: 18; radius: 9
            color: theme.text
            border.width: 3
            border.color: root.interactive ? theme.accent : theme.dim
        }
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.interactive
        hoverEnabled: true
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor

        function pick(x) {
            var ratio = Math.max(0, Math.min(1, x / width))
            var wanted = root.from + Math.round((root.to - root.from) * ratio / root.step) * root.step
            wanted = Math.max(root.from, Math.min(root.to, wanted))
            if (wanted !== root.value) root.moved(wanted)
        }

        onPressed: (mouse) => pick(mouse.x)
        onPositionChanged: (mouse) => { if (pressed) pick(mouse.x) }
    }
}

import QtQuick

Rectangle {
    id: root
    property int idx: 0
    property var info: ({})
    property bool removable: false
    property bool editing: false

    height: 46
    radius: 12
    color: info.active ? theme.accentSoft : (hover.hovered ? theme.panelHi : "transparent")

    HoverHandler { id: hover }

    function startEdit() {
        editing = true
        input.text = String(info.dpi)
        input.forceActiveFocus()
        input.selectAll()
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: app.selectPreset(root.idx)
        onDoubleClicked: root.startEdit()
    }

    // indicatore del preset attivo
    Rectangle {
        x: 14
        anchors.verticalCenter: parent.verticalCenter
        width: 16; height: 16; radius: 8
        color: "transparent"
        border.width: 2
        border.color: info.active ? theme.accent : theme.dim
        Rectangle { anchors.centerIn: parent; width: 8; height: 8; radius: 4; color: theme.accent; visible: !!info.active }
    }

    Txt {
        id: valueText
        visible: !root.editing
        x: 42
        anchors.verticalCenter: parent.verticalCenter
        text: info.dpi
        font.pixelSize: 17
        font.weight: info.active ? Font.DemiBold : Font.Normal
    }
    Txt { visible: !root.editing; x: valueText.x + valueText.implicitWidth + 6; anchors.baseline: valueText.baseline
          text: "DPI"; color: theme.muted; font.pixelSize: 12 }

    TextInput {
        id: input
        visible: root.editing
        x: 42
        width: 80
        anchors.verticalCenter: parent.verticalCenter
        color: theme.text
        font.family: theme.fontFamily
        font.pixelSize: 17
        selectionColor: theme.accent
        inputMethodHints: Qt.ImhDigitsOnly
        validator: IntValidator { bottom: 1; top: 99999 }
        onAccepted: {
            var v = parseInt(text)
            if (!isNaN(v)) app.setDpiTyped(root.idx, v)
            root.editing = false
        }
        onActiveFocusChanged: if (!activeFocus) root.editing = false
        Keys.onEscapePressed: root.editing = false
    }

    // marcatore dell'avvio / azione per impostarlo
    Rectangle {
        id: bootChip
        visible: !!info.default
        anchors.right: removeBtn.left
        anchors.rightMargin: 6
        anchors.verticalCenter: parent.verticalCenter
        height: 24
        width: bootText.implicitWidth + 20
        radius: 6
        color: theme.amber
        Txt { id: bootText; anchors.centerIn: parent; text: "Avvio"; color: "#2A1B00"; font.pixelSize: 12; font.weight: Font.DemiBold }
    }
    Rectangle {
        id: setBoot
        visible: !info.default && hover.hovered && !root.editing
        anchors.right: removeBtn.left
        anchors.rightMargin: 6
        anchors.verticalCenter: parent.verticalCenter
        height: 24
        width: setBootText.implicitWidth + 20
        radius: 6
        color: "transparent"
        border.width: 1
        border.color: theme.amber
        Txt { id: setBootText; anchors.centerIn: parent; text: "Imposta avvio"; color: theme.amber; font.pixelSize: 12 }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: app.setDefaultPreset(root.idx) }
    }

    Item {
        id: removeBtn
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        width: 28; height: 28
        Icon {
            anchors.centerIn: parent
            name: "close"; width: 14; height: 14
            tint: removeArea.containsMouse ? theme.danger : theme.muted
            visible: root.removable && hover.hovered
        }
        MouseArea {
            id: removeArea
            anchors.fill: parent
            hoverEnabled: true
            enabled: root.removable
            cursorShape: Qt.PointingHandCursor
            onClicked: app.removePreset(root.idx)
        }
    }
}

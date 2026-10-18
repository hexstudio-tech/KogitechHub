import QtQuick

Rectangle {
    id: root
    property string message: ""
    property bool isError: false

    function show(text, error) {
        message = text
        isError = error
        opacity = 1
        hideTimer.restart()
    }

    width: Math.min(parent.width - 48, label.implicitWidth + 56)
    height: 46
    radius: 14
    color: theme.panelHi
    border.width: 1
    border.color: isError ? theme.danger : theme.line
    opacity: 0
    visible: opacity > 0
    Behavior on opacity { NumberAnimation { duration: 160 } }

    Row {
        anchors.centerIn: parent
        spacing: 10
        Icon { name: root.isError ? "alert" : "info"; tint: root.isError ? theme.danger : theme.accent; width: 18; height: 18; anchors.verticalCenter: parent.verticalCenter }
        Txt { id: label; text: root.message; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight }
    }
    Timer { id: hideTimer; interval: 4200; onTriggered: { root.opacity = 0; app.clearToast() } }
}

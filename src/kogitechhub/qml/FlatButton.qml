import QtQuick

Rectangle {
    id: root
    property string text: ""
    property bool primary: false
    property string iconName: ""
    signal clicked()

    implicitHeight: 40
    implicitWidth: row.implicitWidth + 32
    radius: 11
    color: primary ? (area.containsMouse ? Qt.lighter(theme.accent, 1.12) : theme.accent)
                   : (area.containsMouse ? theme.panelHi : "transparent")
    border.width: primary ? 0 : 1
    border.color: root.activeFocus ? theme.accent : theme.line
    activeFocusOnTab: true
    Keys.onReturnPressed: root.clicked()
    Keys.onSpacePressed: root.clicked()

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 8
        Icon {
            visible: root.iconName !== ""
            name: root.iconName
            tint: root.primary ? "#FFFFFF" : theme.text
            width: 16; height: 16
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            text: root.text
            color: root.primary ? "#FFFFFF" : theme.text
            font.weight: Font.Medium
            anchors.verticalCenter: parent.verticalCenter
        }
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}

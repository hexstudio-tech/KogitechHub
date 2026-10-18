import QtQuick

Rectangle {
    id: root
    property var info: ({})
    readonly property bool configurable: !!info.configurable

    width: 344
    height: 176
    radius: 18
    color: area.containsMouse ? theme.panelHi : theme.panel
    border.width: 1
    border.color: root.activeFocus ? theme.accent : theme.line
    activeFocusOnTab: true
    Keys.onReturnPressed: app.openDevice(info.id)
    Behavior on color { ColorAnimation { duration: 120 } }

    Icon { name: "mouse"; tint: root.configurable ? theme.accent : theme.muted; width: 30; height: 30; x: 22; y: 22 }

    Rectangle {
        anchors.right: parent.right
        anchors.rightMargin: 20
        y: 22
        height: 26
        width: chipText.implicitWidth + 24
        radius: 13
        color: root.configurable ? theme.accentSoft : theme.bg
        border.width: root.configurable ? 0 : 1
        border.color: theme.line
        Txt { id: chipText; anchors.centerIn: parent; font.pixelSize: 12
              text: root.configurable ? "Configurabile" : "Sola lettura"
              color: root.configurable ? "#B9B1FF" : theme.muted }
    }

    Column {
        x: 22; y: 66
        width: parent.width - 44
        spacing: 3
        Txt { width: parent.width; text: info.name || ""; font.pixelSize: 18; font.weight: Font.Medium; elide: Text.ElideRight }
        Txt { width: parent.width; color: theme.muted; font.pixelSize: 12; elide: Text.ElideRight
              text: (info.vendor ? info.vendor + "   " : "") + (info.vendorId || "") + ":" + (info.productId || "") }
    }

    Row {
        visible: root.configurable
        x: 22
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 20
        spacing: 28
        Item {
            width: n1.implicitWidth + 6 + u1.implicitWidth
            height: n1.implicitHeight
            Txt { id: n1; text: info.dpi || 0; font.pixelSize: 30; font.weight: Font.Light }
            Txt { id: u1; x: n1.implicitWidth + 6; anchors.baseline: n1.baseline; text: "DPI"; color: theme.muted; font.pixelSize: 13 }
        }
        Item {
            width: n2.implicitWidth + 6 + u2.implicitWidth
            height: n2.implicitHeight
            Txt { id: n2; text: info.reportRate || 0; font.pixelSize: 30; font.weight: Font.Light }
            Txt { id: u2; x: n2.implicitWidth + 6; anchors.baseline: n2.baseline; text: "Hz"; color: theme.muted; font.pixelSize: 13 }
        }
    }
    Txt {
        visible: !root.configurable
        x: 22
        width: parent.width - 44
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 18
        text: info.note || ""
        color: theme.muted
        font.pixelSize: 12
        wrapMode: Text.WordWrap
        maximumLineCount: 2
        elide: Text.ElideRight
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: app.openDevice(root.info.id)
    }
}

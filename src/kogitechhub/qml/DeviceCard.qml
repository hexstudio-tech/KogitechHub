import QtQuick

Rectangle {
    id: root
    property var info: ({})
    readonly property bool configurable: !!info.configurable
    readonly property bool lighting: !!info.lighting
    readonly property bool headset: !!info.headset
    readonly property string kind: info.kind || "mouse"

    function kindIcon() {
        if (kind === "keyboard") return "keyboard"
        if (kind === "headset") return "headset"
        if (lighting) return "rgb"
        return "mouse"
    }

    function chipText() {
        if (lighting && headset) return "RGB + cuffia"
        if (lighting) return "RGB"
        if (headset) return "Cuffia"
        return configurable ? "Configurabile" : "Sola lettura"
    }

    function subtitleText() {
        if (info.subtitle) return info.subtitle
        var ids = info.vendorId && info.productId ? info.vendorId + ":" + info.productId : ""
        return [info.vendor || "", ids].filter(function (x) { return x !== "" }).join("   ")
    }

    width: 344
    height: 176
    radius: 18
    color: area.containsMouse ? theme.panelHi : theme.panel
    border.width: 1
    border.color: root.activeFocus ? theme.accent : theme.line
    activeFocusOnTab: true
    Keys.onReturnPressed: app.openDevice(info.id)
    Behavior on color { ColorAnimation { duration: 120 } }

    Icon {
        name: root.kindIcon()
        tint: root.configurable ? theme.accent : theme.muted
        width: 30; height: 30; x: 22; y: 22
    }

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
        Txt {
            id: chipText
            anchors.centerIn: parent
            font.pixelSize: 12
            text: root.chipText()
            color: root.configurable ? "#B9B1FF" : theme.muted
        }
    }

    Column {
        x: 22; y: 66
        width: parent.width - 44
        spacing: 3
        Txt { width: parent.width; text: info.name || ""; font.pixelSize: 18; font.weight: Font.Medium; elide: Text.ElideRight }
        Txt {
            width: parent.width; color: theme.muted; font.pixelSize: 12; elide: Text.ElideRight
            text: root.subtitleText()
        }
    }

    // mouse: DPI e frequenza
    Row {
        visible: root.configurable && root.kind === "mouse" && !root.lighting
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

    // tastiere/dispositivi RGB: modalità attiva e LED
    Row {
        visible: root.lighting
        x: 22
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 22
        spacing: 24
        Column {
            spacing: 1
            Txt { text: info.activeMode || "—"; font.pixelSize: 20; font.weight: Font.Light }
            Txt { text: "modalità"; color: theme.muted; font.pixelSize: 11 }
        }
        Column {
            spacing: 1
            Txt { text: info.ledCount || 0; font.pixelSize: 20; font.weight: Font.Light }
            Txt { text: "LED"; color: theme.muted; font.pixelSize: 11 }
        }
    }

    // cuffie: batteria
    Row {
        visible: root.headset && !root.lighting
        x: 22
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 22
        spacing: 24
        Column {
            spacing: 1
            Txt {
                text: info.battery === null || info.battery === undefined ? "—" : info.battery
                font.pixelSize: 30; font.weight: Font.Light
            }
            Txt { text: "batteria %"; color: theme.muted; font.pixelSize: 11 }
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 1
            Txt {
                text: info.batteryStatus === "BATTERY_CHARGING" ? "In carica"
                      : info.batteryStatus === "BATTERY_AVAILABLE" ? "Batteria" : "n/d"
                font.pixelSize: 14
            }
            Txt { text: "stato"; color: theme.muted; font.pixelSize: 11 }
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

import QtQuick

Rectangle {
    id: root
    width: 84
    color: theme.rail

    component RailButton: Item {
        id: btn
        property string icon: "mouse"
        property string label: ""
        property bool selected: false
        signal clicked()
        width: 84
        height: 66
        Rectangle {
            width: 3; height: 30; radius: 2
            anchors.verticalCenter: parent.verticalCenter
            color: theme.accent
            visible: btn.selected
        }
        Rectangle {
            anchors.centerIn: parent
            width: 56; height: 56; radius: 14
            color: btn.selected ? theme.accentSoft : (ma.containsMouse ? theme.panelHi : "transparent")
        }
        Column {
            anchors.centerIn: parent
            spacing: 5
            Icon { name: btn.icon; tint: btn.selected ? theme.text : theme.muted; anchors.horizontalCenter: parent.horizontalCenter }
            Txt { text: btn.label; font.pixelSize: 11; color: btn.selected ? theme.text : theme.muted; anchors.horizontalCenter: parent.horizontalCenter }
        }
        MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: btn.clicked() }
    }

    // icona ed etichetta del pulsante del dispositivo aperto
    readonly property string deviceIcon: !app.current.id ? "gauge"
                                         : app.current.lighting ? "rgb"
                                         : app.current.headset ? "headset"
                                         : app.current.kind === "keyboard" ? "keyboard"
                                         : "gauge"
    readonly property string deviceLabel: !app.current.id ? "DPI"
                                          : app.current.lighting ? "RGB"
                                          : app.current.headset ? "Cuffie"
                                          : app.current.kind === "keyboard" ? "Tastiera"
                                          : "DPI"

    Column {
        anchors.top: parent.top
        anchors.topMargin: 22
        spacing: 6
        RailButton { icon: "devices"; label: "Dispositivi"; selected: app.page === "dashboard"; onClicked: app.goBack() }
        RailButton {
            icon: root.deviceIcon; label: root.deviceLabel
            visible: !!app.current.id
            selected: app.page === "device"
            onClicked: app.showDevice()
        }
    }
    RailButton {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 18
        icon: "info"; label: "Info"
        selected: app.page === "about"
        onClicked: app.showAbout()
    }
}

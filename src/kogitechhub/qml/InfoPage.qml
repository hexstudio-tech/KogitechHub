import QtQuick

// Pagina per i dispositivi rilevati ma non configurabili: solo informazioni.
Item {
    id: root
    readonly property var cur: app.current
    readonly property bool canSniff: !!cur.vendorId && !!cur.productId

    Rectangle {
        id: backBtn
        x: 40; y: 30
        width: 44; height: 44; radius: 12
        color: backArea.containsMouse ? theme.panelHi : "transparent"
        border.width: 1; border.color: theme.line
        Icon { anchors.centerIn: parent; name: "back"; tint: theme.text }
        MouseArea { id: backArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: app.goBack() }
    }
    Column {
        x: 104
        anchors.verticalCenter: backBtn.verticalCenter
        spacing: 3
        Txt { text: cur.name || ""; font.pixelSize: 28; font.weight: Font.Light }
        Txt { color: theme.muted; font.pixelSize: 12; text: "Sola lettura" }
    }

    Rectangle {
        x: 40
        y: 112
        width: Math.min(560, parent.width - 80)
        height: infoCol.height + 44
        radius: 20
        color: theme.panel
        border.width: 1
        border.color: theme.line

        Column {
            id: infoCol
            x: 24; y: 22
            width: parent.width - 48
            spacing: 14

            Txt {
                width: parent.width
                text: cur.note || "Questo dispositivo non è configurabile da KogitechHub."
                color: theme.muted
                wrapMode: Text.WordWrap
                lineHeight: 1.25
            }
            Rectangle { width: parent.width; height: 1; color: theme.line }
            Row {
                spacing: 16
                Txt { width: 140; text: "Produttore"; color: theme.muted }
                Txt { text: cur.vendor || "Sconosciuto" }
            }
            Row {
                spacing: 16
                Txt { width: 140; text: "ID USB"; color: theme.muted }
                Txt { text: (cur.vendorId || "") + ":" + (cur.productId || "") }
            }
            Repeater {
                model: Object.keys(cur.details || {})
                delegate: Row {
                    required property string modelData
                    spacing: 16
                    Txt { width: 140; text: modelData; color: theme.muted }
                    Txt { text: (cur.details || {})[modelData] }
                }
            }

            Rectangle { visible: canSniff; width: parent.width; height: 1; color: theme.line }

            Column {
                id: sniffCol
                visible: canSniff
                width: parent.width
                spacing: 10
                Txt {
                    width: parent.width
                    color: theme.muted; font.pixelSize: 12
                    wrapMode: Text.WordWrap; lineHeight: 1.2
                    text: "Laboratorio HID: cattura i report che questa periferica scambia "
                          + "con il sistema e prova a inviarne di tuoi, per ricostruire il "
                          + "protocollo di colori e pattern quando nessun backend la "
                          + "riconosce."
                }
                FlatButton {
                    primary: true
                    text: "Apri laboratorio HID"
                    onClicked: { sniffer.startFor(cur.vendorId || "", cur.productId || ""); app.showSniffer() }
                }
            }
        }
    }
}

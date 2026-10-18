import QtQuick

Item {
    Column {
        x: 48; y: 44
        width: Math.min(620, parent.width - 96)
        spacing: 18

        Txt { text: "KogitechHub"; font.pixelSize: 34; font.weight: Font.Light }
        Txt { text: "Versione " + app.version; color: theme.muted }
        Txt {
            width: parent.width
            wrapMode: Text.WordWrap
            lineHeight: 1.25
            color: theme.muted
            text: "KogitechHub configura DPI e preset dei mouse tramite libratbag (ratbagd), l'illuminazione RGB di tastiere e cuffie tramite OpenRGB e i controlli delle cuffie USB (batteria, sidetone, luci) tramite HeadsetControl. Le impostazioni dei mouse restano nella loro memoria onboard; quelle RGB vengono scritte sul controller del dispositivo."
        }

        Rectangle { width: parent.width; height: 1; color: theme.line }
        Txt { text: "Servizi"; font.pixelSize: 19; font.weight: Font.Medium }
        Repeater {
            model: app.backends
            delegate: Column {
                required property var modelData
                width: parent.width
                spacing: 3
                Row {
                    spacing: 12
                    Rectangle {
                        width: 10; height: 10; radius: 5
                        anchors.verticalCenter: parent.verticalCenter
                        color: modelData.ok ? theme.ok : theme.amber
                    }
                    Txt {
                        anchors.verticalCenter: parent.verticalCenter
                        text: (modelData.id === "ratbag" ? "libratbag (ratbagd)"
                               : modelData.id === "openrgb" ? "OpenRGB (tastiere, cuffie e RGB)"
                               : modelData.id === "headset" ? "HeadsetControl (cuffie USB)"
                               : modelData.id === "sys" ? "Rilevamento mouse di sistema"
                               : "Dispositivi simulati")
                              + (modelData.ok ? ": attivo" : ": non disponibile")
                    }
                }
                Txt {
                    visible: !modelData.ok && modelData.message !== ""
                    x: 22
                    width: parent.width - 22
                    color: theme.muted
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    text: modelData.message
                }
            }
        }
        Txt {
            visible: app.hint !== ""
            width: parent.width
            wrapMode: Text.WordWrap
            color: theme.amber
            text: app.hint
        }
    }
}

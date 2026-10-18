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
            text: "KogitechHub configura DPI, preset e frequenza di report dei mouse tramite libratbag (servizio ratbagd). I preset vengono salvati nella memoria del mouse, quindi restano attivi anche senza KogitechHub e anche su un altro computer."
        }

        Rectangle { width: parent.width; height: 1; color: theme.line }
        Txt { text: "Servizi"; font.pixelSize: 19; font.weight: Font.Medium }
        Repeater {
            model: app.backends
            delegate: Row {
                required property var modelData
                spacing: 12
                Rectangle {
                    width: 10; height: 10; radius: 5
                    anchors.verticalCenter: parent.verticalCenter
                    color: modelData.ok ? theme.ok : theme.amber
                }
                Txt {
                    anchors.verticalCenter: parent.verticalCenter
                    text: (modelData.id === "ratbag" ? "libratbag (ratbagd)"
                           : modelData.id === "sys" ? "Rilevamento mouse di sistema"
                           : "Mouse simulati")
                          + (modelData.ok ? ": attivo" : ": non disponibile")
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

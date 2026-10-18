import QtQuick

Item {
    id: root

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: col.height + 96
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: col
            x: 48
            y: 44
            width: root.width - 96
            spacing: 22

            Column {
                spacing: 6
                Txt { text: "Mouse collegati"; font.pixelSize: 34; font.weight: Font.Light }
                Txt {
                    color: theme.muted
                    text: app.devices.length === 0 ? "Nessun mouse rilevato."
                          : app.devices.length === 1 ? "1 mouse rilevato. Scegline uno per configurarlo."
                          : app.devices.length + " mouse rilevati. Scegline uno per configurarlo."
                }
            }

            Rectangle {
                visible: app.hint !== ""
                width: parent.width
                height: hintText.implicitHeight + 36
                radius: 14
                color: theme.panel
                border.width: 1
                border.color: theme.amber
                Icon { name: "alert"; tint: theme.amber; x: 18; y: 18; width: 20; height: 20 }
                Txt {
                    id: hintText
                    x: 52; y: 18
                    width: parent.width - 72
                    text: app.hint
                    wrapMode: Text.WordWrap
                    color: theme.text
                    lineHeight: 1.25
                }
            }

            Flow {
                width: parent.width
                spacing: 18
                Repeater {
                    model: app.devices
                    delegate: DeviceCard {
                        required property var modelData
                        info: modelData
                    }
                }
            }
        }
    }
}

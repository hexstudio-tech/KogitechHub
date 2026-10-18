import QtQuick

// Pagina RGB: modalità (pattern), colore, luminosità e velocità via OpenRGB.
Item {
    id: root
    readonly property var cur: app.current
    readonly property var modes: cur.modes || []
    readonly property var zones: cur.zones || []
    readonly property color preview: cur.color || theme.accent
    readonly property var swatches: ["#FF3B30", "#FF9500", "#FFD60A", "#34C759",
                                     "#32ADE6", "#7B6CFF", "#FFFFFF", "#FF2D55"]

    // intestazione
    Item {
        id: header
        x: 40; y: 30
        width: parent.width - 80
        height: 64

        Rectangle {
            id: backBtn
            width: 44; height: 44; radius: 12
            color: backArea.containsMouse ? theme.panelHi : "transparent"
            border.width: 1; border.color: theme.line
            Icon { anchors.centerIn: parent; name: "back"; tint: theme.text }
            MouseArea {
                id: backArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: app.goBack()
            }
        }
        Column {
            x: 64
            anchors.verticalCenter: backBtn.verticalCenter
            spacing: 3
            Txt { text: cur.name || ""; font.pixelSize: 28; font.weight: Font.Light }
            Txt {
                color: theme.muted; font.pixelSize: 12
                text: cur.subtitle || "Illuminazione RGB"
            }
        }
        Row {
            anchors.right: parent.right
            anchors.verticalCenter: backBtn.verticalCenter
            spacing: 8
            Rectangle {
                width: 8; height: 8; radius: 4
                anchors.verticalCenter: parent.verticalCenter
                color: app.syncing ? theme.amber : theme.ok
            }
            Txt {
                color: theme.muted; font.pixelSize: 12
                anchors.verticalCenter: parent.verticalCenter
                text: app.syncing ? "Scrittura sul dispositivo…" : "Sincronizzato"
            }
        }
    }

    // pannello impostazioni
    Rectangle {
        id: panel
        x: 40
        y: header.y + header.height + 22
        width: 356
        height: root.height - y - 36
        radius: 20
        color: theme.panel
        border.width: 1
        border.color: theme.line

        Flickable {
            anchors.fill: parent
            anchors.margins: 1
            contentWidth: width
            contentHeight: panelCol.height + 40
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: panelCol
                x: 22; y: 22
                width: parent.width - 44
                spacing: 14

                Txt { text: "Modalità"; font.pixelSize: 19; font.weight: Font.Medium }
                Txt {
                    width: parent.width
                    color: theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap; lineHeight: 1.2
                    text: modes.length > 0
                          ? "Il pattern che il dispositivo sa eseguire da solo. Con \"Direct\" l'interfaccia scrive i colori LED per LED."
                          : "Questo dispositivo non dichiara modalità: si possono scrivere solo i colori."
                }
                Flow {
                    width: parent.width
                    spacing: 8
                    Repeater {
                        model: root.modes
                        delegate: Rectangle {
                            required property var modelData
                            property bool selected: root.cur.mode === modelData
                            height: 36
                            width: chip.implicitWidth + 26
                            radius: 10
                            color: selected ? theme.accentSoft : (chipArea.containsMouse ? theme.panelHi : "transparent")
                            border.width: 1
                            border.color: selected ? theme.accent : theme.line
                            Txt {
                                id: chip
                                anchors.centerIn: parent
                                text: modelData
                                font.pixelSize: 13
                                font.weight: selected ? Font.DemiBold : Font.Normal
                                color: selected ? "#C9C3FF" : theme.muted
                            }
                            MouseArea {
                                id: chipArea
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: app.setLightingMode(modelData)
                            }
                        }
                    }
                }

                Rectangle { width: parent.width; height: 1; color: theme.line }

                Txt { text: "Colore"; font.pixelSize: 19; font.weight: Font.Medium }
                Row {
                    spacing: 8
                    Repeater {
                        model: root.swatches
                        delegate: Rectangle {
                            required property var modelData
                            width: 30; height: 30; radius: 8
                            color: modelData
                            border.width: root.cur.color === modelData ? 3 : 1
                            border.color: root.cur.color === modelData ? theme.text : theme.line
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (app.setLightingColor(modelData)) colorInput.text = modelData
                                }
                            }
                        }
                    }
                }
                TextInput {
                    id: colorInput
                    width: parent.width
                    height: 38
                    leftPadding: 12
                    verticalAlignment: TextInput.AlignVCenter
                    color: theme.text
                    font.family: theme.fontFamily
                    font.pixelSize: 15
                    selectionColor: theme.accent
                    text: root.cur.color || "#7B6CFF"
                    onAccepted: if (!app.setLightingColor(text)) text = root.cur.color
                    validator: RegularExpressionValidator { regularExpression: /^#?[0-9A-Fa-f]{0,6}$/ }
                }

                Rectangle { width: parent.width; height: 1; color: theme.line }

                Row {
                    width: parent.width
                    Txt { text: "Luminosità"; font.pixelSize: 15; width: parent.width - 50 }
                    Txt { text: (root.cur.brightness || 0) + "%"; color: theme.muted; horizontalAlignment: Text.AlignRight }
                }
                ValueSlider {
                    width: parent.width
                    value: root.cur.brightness || 0
                    onMoved: (v) => app.setLightingBrightness(v)
                }

                Row {
                    width: parent.width
                    Txt { text: "Velocità effetti"; font.pixelSize: 15; width: parent.width - 50 }
                    Txt { text: (root.cur.speed || 0) + "%"; color: theme.muted; horizontalAlignment: Text.AlignRight }
                }
                ValueSlider {
                    width: parent.width
                    value: root.cur.speed || 0
                    onMoved: (v) => app.setLightingSpeed(v)
                }
                Txt {
                    width: parent.width
                    color: theme.dim; font.pixelSize: 11; wrapMode: Text.WordWrap
                    text: "Luminosità e velocità vengono applicate solo se la modalità scelta le supporta."
                }

                Item { width: 1; height: 4 }
                FlatButton {
                    width: parent.width
                    text: "Applica ora"
                    primary: true
                    onClicked: app.commitNow()
                }
            }
        }
    }

    // anteprima
    Item {
        id: stage
        anchors.left: panel.right
        anchors.leftMargin: 40
        anchors.right: parent.right
        anchors.rightMargin: 40
        anchors.top: panel.top
        anchors.bottom: panel.bottom

        Txt {
            visible: !!root.cur.loading
            anchors.centerIn: parent
            text: "Lettura del dispositivo RGB…"
            color: theme.muted
        }

        Column {
            visible: !root.cur.loading
            width: parent.width
            anchors.verticalCenter: parent.verticalCenter
            spacing: 18

            Rectangle {
                id: glow
                width: Math.min(360, parent.width)
                height: 200
                radius: 24
                anchors.horizontalCenter: parent.horizontalCenter
                color: Qt.rgba(root.preview.r, root.preview.g, root.preview.b, 0.16)
                border.width: 2
                border.color: root.preview

                Rectangle {
                    width: 74; height: 74; radius: 37
                    anchors.centerIn: parent
                    color: root.preview
                    border.width: 6
                    border.color: Qt.rgba(1, 1, 1, 0.18)
                }
                Txt {
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 14
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.cur.mode || "Colore diretto"
                    color: theme.text
                    font.pixelSize: 15
                    font.weight: Font.Medium
                }
            }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 28
                Row {
                    spacing: 8
                    Rectangle { width: 12; height: 12; radius: 3; color: theme.accent; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: (root.cur.ledCount || 0) + " LED"; color: theme.muted; font.pixelSize: 12 }
                }
                Row {
                    spacing: 8
                    Rectangle { width: 12; height: 12; radius: 3; color: theme.amber; anchors.verticalCenter: parent.verticalCenter }
                    Txt {
                        text: (root.zones.length || 1) + (root.zones.length === 1 ? " zona" : " zone")
                        color: theme.muted; font.pixelSize: 12
                    }
                }
            }

            Txt {
                width: Math.min(520, parent.width)
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.AlignHCenter
                color: theme.muted
                font.pixelSize: 12
                wrapMode: Text.WordWrap
                lineHeight: 1.25
                text: root.cur.note || ""
            }
        }
    }
}

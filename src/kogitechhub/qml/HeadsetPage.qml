import QtQuick

// Pagina cuffie: batteria, sidetone, luci e timer di spegnimento.
Item {
    id: root
    readonly property var cur: app.current
    readonly property var caps: cur.capabilities || []
    function has(capability) { return caps.indexOf(capability) >= 0 }
    readonly property bool batteryKnown: cur.batteryStatus === "BATTERY_AVAILABLE"
                                         || cur.batteryStatus === "BATTERY_CHARGING"

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
            Txt { color: theme.muted; font.pixelSize: 12; text: cur.subtitle || "Cuffia" }
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
                text: app.syncing ? "Scrittura sulla cuffia…" : "Sincronizzato"
            }
        }
    }

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

                Column {
                    visible: root.has("sidetone")
                    width: parent.width
                    spacing: 8
                    Row {
                        width: parent.width
                        Txt { text: "Sidetone"; font.pixelSize: 19; font.weight: Font.Medium; width: parent.width - 54 }
                        Txt {
                            text: (root.cur.sidetone || 0) + " / " + (root.cur.sidetoneMax || 128)
                            color: theme.muted; horizontalAlignment: Text.AlignRight
                        }
                    }
                    Txt {
                        width: parent.width
                        color: theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap; lineHeight: 1.2
                        text: "Quanto senti la tua voce nelle cuffie, senza ritardo. 0 = spento."
                    }
                    ValueSlider {
                        width: parent.width
                        value: root.cur.sidetone || 0
                        to: root.cur.sidetoneMax || 128
                        step: 4
                        onMoved: (v) => app.setSidetone(v)
                    }
                }

                Rectangle { visible: root.has("sidetone"); width: parent.width; height: 1; color: theme.line }

                Column {
                    visible: root.has("lights")
                    width: parent.width
                    spacing: 8
                    Row {
                        width: parent.width
                        Txt { text: "LED della cuffia"; font.pixelSize: 19; font.weight: Font.Medium; width: parent.width - 70 }
                        Rectangle {
                            width: 52; height: 28; radius: 14
                            anchors.verticalCenter: parent.verticalCenter
                            color: root.cur.lights ? theme.accent : theme.bg
                            border.width: 1
                            border.color: root.cur.lights ? theme.accent : theme.line
                            Rectangle {
                                width: 22; height: 22; radius: 11
                                y: 3
                                x: root.cur.lights ? 27 : 3
                                color: "#FFFFFF"
                                Behavior on x { NumberAnimation { duration: 110 } }
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: app.setHeadsetLights(!root.cur.lights)
                            }
                        }
                    }
                    Txt {
                        width: parent.width
                        color: theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap; lineHeight: 1.2
                        text: "Accende o spegne le luci della cuffia. Per colori e pattern usa la pagina RGB, se OpenRGB riconosce il dispositivo."
                    }
                }

                Rectangle { visible: root.has("lights"); width: parent.width; height: 1; color: theme.line }

                Column {
                    visible: root.has("inactive time")
                    width: parent.width
                    spacing: 8
                    Txt { text: "Spegnimento automatico"; font.pixelSize: 19; font.weight: Font.Medium }
                    Txt {
                        width: parent.width
                        color: theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap; lineHeight: 1.2
                        text: "Dopo quanti minuti senza audio la cuffia si spegne."
                    }
                    Flow {
                        width: parent.width
                        spacing: 8
                        Repeater {
                            model: root.cur.inactiveChoices || [0, 10, 30, 60]
                            delegate: Rectangle {
                                required property var modelData
                                property bool selected: root.cur.inactive === modelData
                                height: 34
                                width: option.implicitWidth + 24
                                radius: 10
                                color: selected ? theme.accentSoft : (optionArea.containsMouse ? theme.panelHi : "transparent")
                                border.width: 1
                                border.color: selected ? theme.accent : theme.line
                                Txt {
                                    id: option
                                    anchors.centerIn: parent
                                    text: modelData === 0 ? "Mai" : modelData + " min"
                                    font.pixelSize: 13
                                    color: selected ? "#C9C3FF" : theme.muted
                                }
                                MouseArea {
                                    id: optionArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: app.setInactiveTime(modelData)
                                }
                            }
                        }
                    }
                }

                Txt {
                    width: parent.width
                    color: theme.dim; font.pixelSize: 11; wrapMode: Text.WordWrap
                    text: root.cur.note || ""
                }
            }
        }
    }

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
            text: "Lettura della cuffia…"
            color: theme.muted
        }

        Column {
            visible: !root.cur.loading
            width: parent.width
            anchors.verticalCenter: parent.verticalCenter
            spacing: 20

            Item {
                width: parent.width
                height: 150
                Txt {
                    id: big
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.horizontalCenterOffset: -30
                    text: root.batteryKnown ? root.cur.battery : "—"
                    font.pixelSize: 132
                    font.weight: Font.Thin
                }
                Txt {
                    anchors.left: big.right
                    anchors.leftMargin: 10
                    anchors.baseline: big.baseline
                    text: "%"
                    color: theme.muted
                    font.pixelSize: 26
                }
                Txt {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: big.bottom
                    anchors.topMargin: -4
                    color: root.cur.batteryStatus === "BATTERY_CHARGING" ? theme.ok : theme.muted
                    font.pixelSize: 13
                    text: root.cur.batteryStatus === "BATTERY_CHARGING"
                          ? "In carica"
                          : root.batteryKnown ? "Batteria" : "Batteria non disponibile"
                }
            }

            Column {
                visible: root.has("chatmix") && root.cur.chatmix !== null && root.cur.chatmix !== undefined
                width: Math.min(420, parent.width)
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 8
                Row {
                    width: parent.width
                    Txt { text: "Bilanciamento gioco / chat"; width: parent.width - 50; font.pixelSize: 13 }
                    Txt { text: root.cur.chatmix || 0; color: theme.muted; horizontalAlignment: Text.AlignRight }
                }
                Rectangle {
                    width: parent.width
                    height: 8
                    radius: 4
                    color: theme.bg
                    border.width: 1
                    border.color: theme.line
                    Rectangle {
                        width: parent.width * Math.max(0, Math.min(1, (root.cur.chatmix || 0) / 100))
                        height: parent.height
                        radius: 4
                        color: theme.accent
                    }
                }
            }

            Rectangle {
                width: Math.min(520, parent.width)
                height: detailsCol.height + 36
                anchors.horizontalCenter: parent.horizontalCenter
                radius: 16
                color: theme.panel
                border.width: 1
                border.color: theme.line

                Column {
                    id: detailsCol
                    x: 20; y: 18
                    width: parent.width - 40
                    spacing: 10
                    Repeater {
                        model: Object.keys(root.cur.details || {})
                        delegate: Row {
                            required property string modelData
                            width: detailsCol.width
                            spacing: 14
                            Txt { width: 120; text: modelData; color: theme.muted; font.pixelSize: 12 }
                            Txt {
                                width: parent.width - 134
                                text: (root.cur.details || {})[modelData]
                                font.pixelSize: 12
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            }
                        }
                    }
                }
            }
        }
    }
}

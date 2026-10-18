import QtQuick

Item {
    id: root
    readonly property var cur: app.current
    readonly property var presets: cur.presets || []
    readonly property bool canAdd: !!cur.canResize && presets.length < (cur.maxPresets || 0)
    readonly property bool canRemove: !!cur.canResize && presets.length > (cur.minPresets || 1)
    readonly property int activeDpi: {
        for (var i = 0; i < presets.length; i++)
            if (presets[i].active) return presets[i].dpi
        return 0
    }

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
            MouseArea { id: backArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: app.goBack() }
        }
        Column {
            x: 64
            anchors.verticalCenter: backBtn.verticalCenter
            spacing: 3
            Txt { text: cur.name || ""; font.pixelSize: 28; font.weight: Font.Light }
            Txt { color: theme.muted; font.pixelSize: 12
                  text: (cur.vendor ? cur.vendor + "   " : "") + (cur.vendorId || "") + ":" + (cur.productId || "") }
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
            Txt { color: theme.muted; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter
                  text: app.syncing ? "Scrittura sul mouse…" : "Sincronizzato con il mouse" }
        }
    }

    // pannello preset e frequenza
    Rectangle {
        id: panel
        x: 40
        y: header.y + header.height + 22
        width: 324
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
                spacing: 12

                Txt { text: "Preset DPI"; font.pixelSize: 19; font.weight: Font.Medium }
                Txt {
                    width: parent.width
                    color: theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap; lineHeight: 1.2
                    text: "I tasti DPI del mouse scorrono questi preset dal più basso al più alto. Il preset di avvio è quello usato all'accensione."
                }
                Column {
                    width: parent.width
                    spacing: 4
                    Repeater {
                        model: root.presets
                        delegate: PresetRow {
                            required property var modelData
                            required property int index
                            width: parent.width
                            idx: index
                            info: modelData
                            removable: root.canRemove
                        }
                    }
                }
                FlatButton {
                    visible: root.canAdd
                    width: parent.width
                    text: "Aggiungi preset"
                    iconName: "plus"
                    onClicked: app.addPresetAuto()
                }

                Rectangle { width: parent.width; height: 1; color: theme.line }

                Column {
                    visible: (cur.reportRates || []).length > 0
                    width: parent.width
                    spacing: 10
                    Txt { text: "Frequenza di report"; font.pixelSize: 19; font.weight: Font.Medium }
                    Txt {
                        width: parent.width
                        color: theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap; lineHeight: 1.2
                        text: "Quante volte al secondo il mouse comunica la sua posizione al computer."
                    }
                    Segmented {
                        width: parent.width
                        options: cur.reportRates || []
                        value: cur.reportRate || 0
                        onPicked: (v) => app.setReportRate(v)
                    }
                }

                Item { width: 1; height: 6 }
                FlatButton {
                    width: parent.width
                    text: "Ripristina predefiniti"
                    onClicked: app.restoreDefaults()
                }
            }
        }
    }

    // scena centrale
    Item {
        id: stage
        anchors.left: panel.right
        anchors.leftMargin: 40
        anchors.right: parent.right
        anchors.rightMargin: 40
        anchors.top: panel.top
        anchors.bottom: panel.bottom

        Txt {
            visible: !!cur.loading
            anchors.centerIn: parent
            text: "Lettura delle impostazioni dal mouse…"
            color: theme.muted
        }

        Column {
            visible: !cur.loading
            anchors.verticalCenter: parent.verticalCenter
            anchors.verticalCenterOffset: -10
            width: parent.width
            spacing: 6

            Item {
                width: parent.width
                height: 150
                Txt {
                    id: big
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.horizontalCenterOffset: -22
                    text: root.activeDpi
                    font.pixelSize: 132
                    font.weight: Font.Thin
                }
                Txt {
                    anchors.left: big.right
                    anchors.leftMargin: 10
                    anchors.baseline: big.baseline
                    text: "DPI"
                    color: theme.muted
                    font.pixelSize: 22
                }
            }

            DpiSlider {
                width: parent.width
                presets: root.presets
                dpiMin: cur.dpiMin || 100
                dpiMax: cur.dpiMax || 8000
                dpiList: cur.dpiList || []
                canAdd: root.canAdd
                canRemove: root.canRemove
            }

            Txt {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                color: theme.muted
                font.pixelSize: 13
                wrapMode: Text.WordWrap
                lineHeight: 1.25
                text: cur.canResize
                      ? "Clicca sulla barra per aggiungere un preset, sul numero per digitare il valore. Trascina il pallino per spostarlo, portalo lontano dalla barra e rilascia per rimuoverlo."
                      : "Questo mouse ha un numero fisso di preset. Trascina i pallini per cambiarne il valore."
            }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 24
                topPadding: 14
                Row {
                    spacing: 8
                    Rectangle { width: 12; height: 12; radius: 6; color: theme.accent; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: "Preset attivo"; color: theme.muted; font.pixelSize: 12 }
                }
                Row {
                    spacing: 8
                    Rectangle { width: 12; height: 12; radius: 3; color: theme.amber; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: "Preset di avvio"; color: theme.muted; font.pixelSize: 12 }
                }
                Row {
                    spacing: 8
                    Rectangle { width: 12; height: 12; radius: 6; color: theme.text; anchors.verticalCenter: parent.verticalCenter }
                    Txt { text: "Altri preset"; color: theme.muted; font.pixelSize: 12 }
                }
            }
        }
    }
}

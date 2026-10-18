import QtQuick

// Laboratorio HID: cattura i report di un nodo hidraw e ne invia di propri.
// Serve per le periferiche che nessun backend conosce (tastiere RGB generiche):
// si registra cosa manda il dispositivo quando si cambia effetto con il software
// del produttore, poi si prova a replicarlo con «Invia report».
Item {
    id: root
    readonly property var cur: app.current
    readonly property var info: sniffer.nodeInfo || {}
    readonly property bool hasNode: sniffer.node !== ""
    readonly property color warn: theme.amber
    property string sendKind: "output"

    function basename(path) {
        var parts = (path || "").split("/")
        return parts.length > 0 ? parts[parts.length - 1] : ""
    }

    function reportSummary(reports) {
        if (!reports || reports.length === 0)
            return "nessun report dichiarato"
        return reports.map(function (r) { return r.type + " " + r.bytes + " B" }).join("  ·  ")
    }

    // report su cui si può leggere o scrivere qualcosa: sono quelli usati per
    // i colori e i pattern quando il backend non conosce il dispositivo
    function configReports() {
        return (info.reports || []).filter(function (r) {
            return r.type === "feature" || r.type === "output"
        })
    }

    Item {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 40
        anchors.rightMargin: 40
        anchors.topMargin: 30
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
            Txt { text: "Laboratorio HID"; font.pixelSize: 28; font.weight: Font.Light }
            Txt {
                color: theme.muted; font.pixelSize: 12
                text: (root.cur.name || "Dispositivo") + "  ·  "
                      + (root.cur.vendorId || "????") + ":" + (root.cur.productId || "????")
            }
        }
        Row {
            anchors.right: parent.right
            anchors.verticalCenter: backBtn.verticalCenter
            spacing: 8
            Rectangle {
                width: 8; height: 8; radius: 4
                anchors.verticalCenter: parent.verticalCenter
                color: sniffer.capturing ? theme.ok : theme.dim
            }
            Txt {
                anchors.verticalCenter: parent.verticalCenter
                color: theme.muted; font.pixelSize: 12
                text: sniffer.capturing ? "Cattura in corso" : "Cattura ferma"
            }
        }
    }

    // --- colonna sinistra: nodi hidraw e permessi ---------------------------
    Rectangle {
        id: side
        anchors.left: header.left
        anchors.top: header.bottom
        anchors.topMargin: 18
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 36
        width: 320
        radius: 20
        color: theme.panel
        border.width: 1
        border.color: theme.line

        Flickable {
            anchors.fill: parent
            anchors.margins: 1
            contentWidth: width
            contentHeight: sideCol.height + 40
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: sideCol
                x: 20; y: 20
                width: parent.width - 40
                spacing: 12

                Txt { text: "Nodi hidraw"; font.pixelSize: 19; font.weight: Font.Medium }
                Txt {
                    width: parent.width
                    color: theme.muted; font.pixelSize: 12
                    wrapMode: Text.WordWrap; lineHeight: 1.2
                    text: "Interfacce del dispositivo su /dev: quella di configurazione "
                          + "è qui in cima. Colori e pattern viaggiano su un report di tipo "
                          + "feature o output, con pagina vendor 0xFF00."
                }

                Repeater {
                    model: sniffer.nodes
                    delegate: Rectangle {
                        required property var modelData
                        readonly property bool selected: sniffer.node === modelData.node
                        width: sideCol.width
                        height: nodeCol.height + 20
                        radius: 12
                        color: selected ? theme.accentSoft : (nodeArea.containsMouse ? theme.panelHi : "transparent")
                        border.width: 1
                        border.color: selected ? theme.accent : theme.line

                        Column {
                            id: nodeCol
                            x: 12; y: 10
                            width: parent.width - 24
                            spacing: 3
                            Row {
                                width: parent.width
                                spacing: 8
                                Txt {
                                    width: parent.width - 96
                                    text: root.basename(modelData.node)
                                    font.family: "monospace"; font.pixelSize: 13
                                    color: selected ? "#FFFFFF" : theme.text
                                }
                                Txt {
                                    width: 88
                                    horizontalAlignment: Text.AlignRight
                                    font.pixelSize: 11
                                    color: modelData.writable ? theme.ok
                                           : modelData.readable ? root.warn : theme.danger
                                    text: modelData.readable ? (modelData.writable ? "accesso" : "sola lettura")
                                                             : "bloccato"
                                }
                            }
                            Txt {
                                width: parent.width
                                font.pixelSize: 11; color: theme.muted
                                elide: Text.ElideRight
                                text: root.reportSummary(modelData.reports)
                            }
                        }
                        MouseArea {
                            id: nodeArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: sniffer.selectNode(modelData.node)
                        }
                    }
                }

                Txt {
                    visible: sniffer.nodes.length === 0
                    width: parent.width
                    color: theme.muted; font.pixelSize: 12
                    wrapMode: Text.WordWrap; lineHeight: 1.2
                    text: "Nessun nodo hidraw per questo dispositivo. Con OpenRGB non "
                          + "riconosciuto l'RGB resta comunque raggiungibile se il kernel "
                          + "espone il nodo: prova «Aggiorna» dopo aver ricollegato la periferica."
                }

                FlatButton {
                    width: parent.width
                    visible: root.hasNode && !root.info.readable
                    primary: true
                    text: "Abilita accesso"
                    onClicked: sniffer.grantAccess()
                }
                FlatButton {
                    width: parent.width
                    text: "Aggiorna"
                    onClicked: sniffer.refresh()
                }

                Txt {
                    width: parent.width
                    color: theme.dim; font.pixelSize: 11
                    wrapMode: Text.WordWrap; lineHeight: 1.25
                    text: "«Abilita accesso» installa una regola udev (chiede la password) "
                          + "che concede al tuo utente la lettura e la scrittura del nodo."
                }
                Txt {
                    width: parent.width
                    color: root.warn; font.pixelSize: 11
                    wrapMode: Text.WordWrap; lineHeight: 1.25
                    text: "Attenzione: su una tastiera la cattura registra anche i tasti "
                          + "premuti. Ferma la cattura prima di digitare password."
                }
            }
        }
    }

    // --- area centrale: cattura e invio -------------------------------------
    Column {
        anchors.left: side.right
        anchors.leftMargin: 24
        anchors.right: header.right
        anchors.top: side.top
        anchors.bottom: side.bottom
        spacing: 18

        // cattura
        Rectangle {
            width: parent.width
            height: Math.max(220, parent.height - 254)
            radius: 20
            color: theme.panel
            border.width: 1
            border.color: theme.line

            Row {
                id: captureHead
                x: 22; y: 20
                width: parent.width - 44
                spacing: 10

                Txt {
                    text: "Cattura"; font.pixelSize: 19; font.weight: Font.Medium
                    width: parent.width - 330
                    anchors.verticalCenter: parent.verticalCenter
                }
                Txt {
                    text: sniffer.reports.length + " report"
                    color: theme.muted; font.pixelSize: 12
                    width: 70
                    horizontalAlignment: Text.AlignRight
                    anchors.verticalCenter: parent.verticalCenter
                }
                FlatButton {
                    primary: !sniffer.capturing
                    text: sniffer.capturing ? "Ferma" : "Avvia"
                    onClicked: sniffer.toggleCapture()
                }
                FlatButton {
                    text: "Salva"
                    onClicked: sniffer.saveCapture()
                }
                FlatButton {
                    text: "Pulisci"
                    onClicked: sniffer.clearReports()
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 22
                anchors.rightMargin: 22
                anchors.top: captureHead.bottom
                anchors.topMargin: 14
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 20
                radius: 14
                color: theme.bg
                border.width: 1
                border.color: theme.line
                clip: true

                ListView {
                    id: reportList
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    model: sniffer.reports
                    spacing: 2
                    boundsBehavior: Flickable.StopAtBounds
                    onCountChanged: if (sniffer.capturing) positionViewAtEnd()

                    delegate: Rectangle {
                        required property var modelData
                        width: reportList.width
                        height: 22
                        radius: 6
                        color: modelData.sent ? theme.accentSoft : "transparent"
                        Txt {
                            x: 8
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 16
                            elide: Text.ElideRight
                            font.family: "monospace"
                            font.pixelSize: 12
                            color: modelData.sent ? "#C9C3FF"
                                 : modelData.read ? theme.ok : theme.text
                            text: (modelData.sent ? "→  " : modelData.read ? "←  " : "   ")
                                  + modelData.time + "  id " + modelData.id + "  "
                                  + modelData.length + " B   " + modelData.hex
                        }
                    }
                }

                Txt {
                    anchors.centerIn: parent
                    visible: sniffer.reports.length === 0
                    width: parent.width - 40
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    color: theme.muted; font.pixelSize: 12; lineHeight: 1.3
                    text: "Premi «Avvia», poi cambia l'effetto RGB con il software del "
                          + "produttore (o con i tasti della tastiera) e osserva i report "
                          + "che arrivano. Sono la firma del protocollo: usa «Invia report» "
                          + "per replicarli da Linux."
                }
            }
        }

        // invio
        Rectangle {
            width: parent.width
            height: 236
            radius: 20
            color: theme.panel
            border.width: 1
            border.color: theme.line

            Column {
                x: 22; y: 20
                width: parent.width - 44
                spacing: 10

                Txt { text: "Invia un report"; font.pixelSize: 19; font.weight: Font.Medium }

                // lettura in sola lettura: mostra lo stato attuale del dispositivo
                Row {
                    width: parent.width
                    spacing: 8
                    Txt {
                        visible: root.configReports().length === 0
                        color: theme.dim; font.pixelSize: 11
                        text: "Questo nodo non dichiara report di configurazione."
                    }
                    Repeater {
                        model: root.configReports()
                        delegate: Rectangle {
                            required property var modelData
                            height: 28
                            width: chip.implicitWidth + 24
                            radius: 9
                            color: chipArea.containsMouse ? theme.panelHi : "transparent"
                            border.width: 1
                            border.color: theme.line
                            Txt {
                                id: chip
                                anchors.centerIn: parent
                                font.pixelSize: 11
                                color: theme.muted
                                text: "leggi " + modelData.type + " " + modelData.id
                                      + " · " + modelData.bytes + " B"
                            }
                            MouseArea {
                                id: chipArea
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: sniffer.readFeature(modelData.id, modelData.bytes)
                            }
                        }
                    }
                }

                Row {
                    width: parent.width
                    spacing: 10

                    Rectangle {
                        width: parent.width - 110
                        height: 42
                        radius: 12
                        color: theme.bg
                        border.width: 1
                        border.color: hexField.activeFocus ? theme.accent : theme.line

                        TextInput {
                            id: hexField
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            verticalAlignment: TextInput.AlignVCenter
                            color: theme.text
                            font.family: "monospace"
                            font.pixelSize: 13
                            selectByMouse: true
                            clip: true
                            inputMethodHints: Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
                            Keys.onReturnPressed: sendBtn.clicked()
                            Txt {
                                anchors.verticalCenter: parent.verticalCenter
                                visible: hexField.text === ""
                                text: "05 01 FF 00 00   (primo byte = ID del report)"
                                color: theme.dim; font.pixelSize: 13
                            }
                        }
                    }
                    FlatButton {
                        id: sendBtn
                        primary: true
                        text: "Invia"
                        enabled: hexField.text !== ""
                        onClicked: if (sniffer.sendReport(hexField.text, root.sendKind)) hexField.text = ""
                    }
                }

                Row {
                    spacing: 8
                    Repeater {
                        model: [{ id: "output", label: "output" }, { id: "feature", label: "feature" }]
                        delegate: Rectangle {
                            required property var modelData
                            readonly property bool picked: root.sendKind === modelData.id
                            width: 96; height: 30; radius: 9
                            color: picked ? theme.accentSoft : (kindArea.containsMouse ? theme.panelHi : "transparent")
                            border.width: 1
                            border.color: picked ? theme.accent : theme.line
                            Txt {
                                anchors.centerIn: parent
                                text: modelData.label
                                font.pixelSize: 12
                                color: picked ? "#C9C3FF" : theme.muted
                            }
                            MouseArea {
                                id: kindArea
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.sendKind = modelData.id
                            }
                        }
                    }
                }

                Txt {
                    width: parent.width
                    color: root.warn; font.pixelSize: 11
                    wrapMode: Text.WordWrap; lineHeight: 1.25
                    text: "Scrivere report a caso può cambiare l'effetto, spegnere l'RGB o "
                          + "bloccare la periferica fino a un nuovo collegamento: procedi un "
                          + "valore alla volta, confrontando la cattura con il software del "
                          + "produttore. Un report sbagliato non è pericoloso, solo da annullare."
                }
            }
        }
    }
}

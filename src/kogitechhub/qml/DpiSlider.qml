import QtQuick

// Slider DPI con preset multipli.
//  - clic sul numero del preset: ne modifica il valore digitandolo (Invio conferma)
//  - clic sulla barra: aggiunge un preset
//  - trascina il pallino: cambia il suo valore (si riordina da solo)
//  - trascina un pallino lontano dalla barra e rilascia: lo rimuove
//  - frecce sinistra/destra: sposta il preset attivo di un valore
//
// Il mouse è gestito da un unico MouseArea sulla radice: i delegati del Repeater
// vengono distruitti e ricreati quando l'elenco dei preset cambia (durante un
// trascinamento succede a ogni passo), quindi un MouseArea dentro il delegate
// perderebbe la presa del mouse a metà gesto.
Item {
    id: root
    property var presets: []
    property int dpiMin: 100
    property int dpiMax: 8000
    property var dpiList: []
    property bool canAdd: false
    property bool canRemove: false

    readonly property real pad: 46
    readonly property real trackY: 96
    readonly property real span: Math.max(1, width - 2 * pad)
    property int dragIdx: -1
    property int editingIdx: -1
    property int labelIdx: -1
    property int dotIdx: -1
    property int pressDot: -1
    property int pressLabel: -1
    property bool removing: false
    property bool blockedTap: false
    property real pressX: 0
    property real pressY: 0

    implicitHeight: 190
    activeFocusOnTab: true
    Keys.onLeftPressed: app.nudge(-1)
    Keys.onRightPressed: app.nudge(1)

    function xFor(dpi) {
        return pad + (dpi - dpiMin) / Math.max(1, dpiMax - dpiMin) * span
    }
    function snapDpi(v) {
        var list = dpiList
        if (!list || list.length === 0) return Math.round(v)
        var lo = 0, hi = list.length - 1
        if (v <= list[0]) return list[0]
        if (v >= list[hi]) return list[hi]
        while (hi - lo > 1) {
            var mid = (lo + hi) >> 1
            if (list[mid] < v) lo = mid; else hi = mid
        }
        return (v - list[lo]) <= (list[hi] - v) ? list[lo] : list[hi]
    }
    function dpiAt(x) {
        var f = Math.max(0, Math.min(1, (x - pad) / span))
        return snapDpi(dpiMin + f * (dpiMax - dpiMin))
    }
    // pallino sotto il punto (zona di trascinamento)
    function hitDot(x, y) {
        if (Math.abs(y - trackY) > 20)
            return -1
        return nearestIndex(x, 20)
    }
    // numero sopra il pallino (clic = editor, non trascina)
    function hitLabel(x, y) {
        if (y < trackY - 60 || y > trackY - 20)
            return -1
        return nearestIndex(x, 26)
    }
    function nearestIndex(x, tol) {
        var best = -1, bd = tol
        for (var i = 0; i < root.presets.length; i++) {
            var d = Math.abs(root.xFor(root.presets[i].dpi) - x)
            if (d < bd) {
                bd = d
                best = i
            }
        }
        return best
    }

    function beginDrag(i) {
        root.editingIdx = -1
        root.forceActiveFocus()
        root.removing = false
        root.dragIdx = i
        app.selectPreset(i)
    }
    function moveDrag(pos) {
        if (root.dragIdx < 0)
            return
        root.removing = root.canRemove && Math.abs(pos.y - root.trackY) > 80
        if (root.removing)
            return
        root.dragIdx = app.setDpi(root.dragIdx, root.dpiAt(pos.x))
    }
    function endDrag() {
        if (root.dragIdx < 0)
            return
        if (root.removing)
            app.removePreset(root.dragIdx)
        else
            app.commitNow()
        root.dragIdx = -1
        root.removing = false
    }
    function startEdit(i) {
        root.editingIdx = i
    }
    function acceptEdit(i, text) {
        root.editingIdx = -1
        var v = parseInt(text)
        if (!isNaN(v)) {
            app.setDpiTyped(i, v)           // digitato: esatto se il mouse lo supporta
            app.commitNow()
        }
    }

    // tacche e scala
    Canvas {
        id: ticks
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var range = root.dpiMax - root.dpiMin
            var steps = [50, 100, 250, 500, 1000, 2000, 5000]
            var minor = 50
            for (var i = 0; i < steps.length; i++) {
                minor = steps[i]
                if (range / minor <= 70)
                    break
            }
            var major = minor * 5
            var first = Math.ceil(root.dpiMin / minor) * minor
            ctx.font = "11px sans-serif"
            ctx.textAlign = "center"
            for (var v = first; v <= root.dpiMax; v += minor) {
                var x = Math.round(root.xFor(v)) + 0.5
                var isMajor = (v % major) === 0
                ctx.strokeStyle = isMajor ? theme.dim : theme.line
                ctx.lineWidth = 1
                ctx.beginPath()
                ctx.moveTo(x, root.trackY + 10)
                ctx.lineTo(x, root.trackY + (isMajor ? 22 : 17))
                ctx.stroke()
                if (isMajor) {
                    ctx.fillStyle = theme.muted
                    ctx.fillText(String(v), x, root.trackY + 40)
                }
            }
        }
        Connections {
            target: root
            function onDpiMinChanged() { ticks.requestPaint() }
            function onDpiMaxChanged() { ticks.requestPaint() }
            function onWidthChanged() { ticks.requestPaint() }
        }
    }

    // binario
    Rectangle {
        x: root.pad; y: root.trackY - 2; width: root.span; height: 4; radius: 2
        color: theme.line
    }
    // tratto fino al preset attivo
    Rectangle {
        property real activeX: {
            for (var i = 0; i < root.presets.length; i++)
                if (root.presets[i].active)
                    return root.xFor(root.presets[i].dpi)
            return root.pad
        }
        x: root.pad; y: root.trackY - 2; width: Math.max(0, activeX - root.pad); height: 4; radius: 2
        color: theme.accent
    }

    // contorno di focus da tastiera
    Rectangle {
        anchors.fill: parent
        anchors.margins: 2
        radius: 14
        color: "transparent"
        border.width: 1
        border.color: theme.accent
        visible: root.activeFocus
        opacity: 0.5
    }

    Repeater {
        model: root.presets
        delegate: Item {
            id: marker
            required property var modelData
            required property int index
            readonly property bool grabbed: root.dragIdx === index
            readonly property bool editing: root.editingIdx === index
            readonly property bool fading: grabbed && root.removing
            x: root.xFor(modelData.dpi) - width / 2
            y: root.trackY - height / 2
            width: 36; height: 36
            opacity: fading ? 0.35 : 1

            onEditingChanged: {
                if (!editing)
                    return
                dpiInput.text = String(modelData.dpi)
                dpiInput.forceActiveFocus()
                dpiInput.selectAll()
            }

            Rectangle {
                anchors.centerIn: parent
                width: 34; height: 34; radius: 17
                color: "transparent"
                border.width: 2
                border.color: theme.accent
                opacity: 0.6
                visible: !!modelData.active
            }
            Rectangle {
                anchors.centerIn: parent
                width: modelData.default ? 20 : 18
                height: width
                radius: modelData.default ? 5 : width / 2
                color: modelData.default ? theme.amber : (modelData.active ? theme.accent : theme.text)
            }

            // numero: clic per digitare il valore
            Rectangle {
                visible: !marker.editing
                anchors.horizontalCenter: parent.horizontalCenter
                y: -32
                width: labelTxt.implicitWidth + 18
                height: 24
                radius: 7
                color: root.labelIdx === marker.index ? theme.panelHi : "transparent"
                Behavior on color { ColorAnimation { duration: 100 } }
                Txt {
                    id: labelTxt
                    anchors.centerIn: parent
                    text: modelData.dpi
                    font.pixelSize: 15
                    font.weight: modelData.active ? Font.DemiBold : Font.Normal
                    font.underline: !!modelData.active
                    color: modelData.default ? theme.amber : theme.text
                }
            }

            // editor del valore
            Rectangle {
                visible: marker.editing
                anchors.horizontalCenter: parent.horizontalCenter
                y: -33
                width: 86
                height: 26
                radius: 7
                color: theme.panelHi
                border.width: 1
                border.color: theme.accent
                TextInput {
                    id: dpiInput
                    anchors.fill: parent
                    anchors.margins: 4
                    horizontalAlignment: TextInput.AlignHCenter
                    verticalAlignment: TextInput.AlignVCenter
                    color: theme.text
                    font.family: theme.fontFamily
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    selectionColor: theme.accent
                    inputMethodHints: Qt.ImhDigitsOnly
                    validator: IntValidator { bottom: 1; top: 99999 }
                    onAccepted: if (marker.editing) root.acceptEdit(marker.index, dpiInput.text)
                    Keys.onEscapePressed: root.editingIdx = -1
                    onActiveFocusChanged: if (!activeFocus && marker.editing)
                                              root.editingIdx = -1
                }
            }
        }
    }

    // unico gestore del mouse: pallino (trascina), numero (digita), barra (aggiungi)
    MouseArea {
        anchors.fill: parent
        enabled: root.editingIdx < 0        // mentre si digita l'editor riceve il mouse
        hoverEnabled: true
        cursorShape: root.dragIdx >= 0 ? Qt.ClosedHandCursor
                     : root.labelIdx >= 0 ? Qt.IBeamCursor : Qt.PointingHandCursor
        onPositionChanged: (mouse) => {
            root.labelIdx = root.hitLabel(mouse.x, mouse.y)
            root.dotIdx = root.hitDot(mouse.x, mouse.y)
            if (root.dragIdx >= 0)
                root.moveDrag(Qt.point(mouse.x, mouse.y))
        }
        onPressed: (mouse) => {
            root.pressX = mouse.x
            root.pressY = mouse.y
            root.pressLabel = root.hitLabel(mouse.x, mouse.y)
            root.pressDot = root.hitDot(mouse.x, mouse.y)
            root.blockedTap = root.editingIdx >= 0
            root.editingIdx = -1
            root.forceActiveFocus()
            if (root.pressDot >= 0)
                root.beginDrag(root.pressDot)
        }
        onReleased: (mouse) => {
            if (root.dragIdx >= 0) {
                root.endDrag()
                return
            }
            if (root.blockedTap) {
                root.blockedTap = false
                return
            }
            if (Math.abs(mouse.x - root.pressX) >= 6 || Math.abs(mouse.y - root.pressY) >= 6)
                return                       // è stato un trascinamento, non un clic
            if (root.pressLabel >= 0)
                root.startEdit(root.pressLabel)
            else if (root.canAdd && Math.abs(mouse.y - root.trackY) < 60)
                app.addPresetAt(root.dpiAt(mouse.x))
        }
        onCanceled: {
            root.dragIdx = -1
            root.removing = false
            root.blockedTap = false
        }
    }
}

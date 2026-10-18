import QtQuick

// Icone a tratto disegnate con Canvas (nessun font di icone richiesto).
Canvas {
    id: root
    property string name: "mouse"
    property color tint: theme.muted
    property real stroke: 1.8
    width: 22
    height: 22
    onTintChanged: requestPaint()
    onNameChanged: requestPaint()
    onWidthChanged: requestPaint()

    function rrect(ctx, x, y, w, h, r) {
        ctx.beginPath()
        ctx.moveTo(x + r, y)
        ctx.lineTo(x + w - r, y)
        ctx.arc(x + w - r, y + r, r, -Math.PI / 2, 0)
        ctx.lineTo(x + w, y + h - r)
        ctx.arc(x + w - r, y + h - r, r, 0, Math.PI / 2)
        ctx.lineTo(x + r, y + h)
        ctx.arc(x + r, y + h - r, r, Math.PI / 2, Math.PI)
        ctx.lineTo(x, y + r)
        ctx.arc(x + r, y + r, r, Math.PI, Math.PI * 1.5)
        ctx.closePath()
    }

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.scale(width / 24, height / 24)
        ctx.strokeStyle = root.tint
        ctx.fillStyle = root.tint
        ctx.lineWidth = root.stroke * 24 / width * (width / 22)
        ctx.lineCap = "round"
        ctx.lineJoin = "round"
        if (name === "mouse") {
            rrect(ctx, 6.5, 2.5, 11, 19, 5.5)
            ctx.stroke()
            ctx.beginPath(); ctx.moveTo(12, 2.8); ctx.lineTo(12, 9.5); ctx.stroke()
        } else if (name === "gauge") {
            ctx.beginPath(); ctx.arc(12, 14, 8.5, Math.PI * 0.85, Math.PI * 2.15); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(12, 14); ctx.lineTo(16.2, 8.8); ctx.stroke()
            ctx.beginPath(); ctx.arc(12, 14, 1.2, 0, Math.PI * 2); ctx.fill()
        } else if (name === "info") {
            ctx.beginPath(); ctx.arc(12, 12, 9, 0, Math.PI * 2); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(12, 11); ctx.lineTo(12, 16.5); ctx.stroke()
            ctx.beginPath(); ctx.arc(12, 7.6, 1.1, 0, Math.PI * 2); ctx.fill()
        } else if (name === "back") {
            ctx.beginPath(); ctx.moveTo(14.5, 5.5); ctx.lineTo(8, 12); ctx.lineTo(14.5, 18.5); ctx.stroke()
        } else if (name === "plus") {
            ctx.beginPath(); ctx.moveTo(12, 5); ctx.lineTo(12, 19); ctx.moveTo(5, 12); ctx.lineTo(19, 12); ctx.stroke()
        } else if (name === "close") {
            ctx.beginPath(); ctx.moveTo(6.5, 6.5); ctx.lineTo(17.5, 17.5); ctx.moveTo(17.5, 6.5); ctx.lineTo(6.5, 17.5); ctx.stroke()
        } else if (name === "alert") {
            ctx.beginPath(); ctx.moveTo(12, 3.5); ctx.lineTo(21.5, 20); ctx.lineTo(2.5, 20); ctx.closePath(); ctx.stroke()
            ctx.beginPath(); ctx.moveTo(12, 10); ctx.lineTo(12, 14.5); ctx.stroke()
            ctx.beginPath(); ctx.arc(12, 17.2, 1, 0, Math.PI * 2); ctx.fill()
        }
    }
}

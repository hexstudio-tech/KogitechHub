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
        } else if (name === "keyboard") {
            rrect(ctx, 2.5, 6.5, 19, 11, 2.5); ctx.stroke()
            for (var row = 0; row < 2; row++) {
                for (var col = 0; col < 5; col++) {
                    ctx.fillRect(5.5 + col * 3.1, 9.2 + row * 2.6, 1.7, 1.5)
                }
            }
            ctx.fillRect(8, 14.4, 8, 1.5)
        } else if (name === "headset") {
            ctx.beginPath(); ctx.arc(12, 11.5, 8, Math.PI, Math.PI * 2); ctx.stroke()
            rrect(ctx, 3.2, 11, 4.2, 7.5, 2.1); ctx.stroke()
            rrect(ctx, 16.6, 11, 4.2, 7.5, 2.1); ctx.stroke()
        } else if (name === "rgb") {
            ctx.beginPath(); ctx.arc(12, 12, 8.6, 0, Math.PI * 2); ctx.stroke()
            var dots = [[12, 6.6], [6.8, 14.8], [17.2, 14.8]]
            for (var i = 0; i < dots.length; i++) {
                ctx.beginPath(); ctx.arc(dots[i][0], dots[i][1], 1.7, 0, Math.PI * 2); ctx.fill()
            }
        } else if (name === "devices") {
            rrect(ctx, 3, 3, 7.5, 7.5, 2); ctx.stroke()
            rrect(ctx, 13.5, 3, 7.5, 7.5, 2); ctx.stroke()
            rrect(ctx, 3, 13.5, 7.5, 7.5, 2); ctx.stroke()
            rrect(ctx, 13.5, 13.5, 7.5, 7.5, 2); ctx.stroke()
        }
    }
}

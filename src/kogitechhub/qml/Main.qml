import QtQuick
import QtQuick.Window

Window {
    id: win
    width: 1180
    height: 740
    minimumWidth: 980
    minimumHeight: 620
    visible: true
    title: "KogitechHub"
    color: theme.bg

    Rail {
        id: rail
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
    }

    Item {
        id: stage
        anchors.left: rail.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom

        Dashboard { anchors.fill: parent; visible: app.page === "dashboard" }
        DevicePage { anchors.fill: parent; visible: app.page === "device" && !!app.current.configurable }
        InfoPage { anchors.fill: parent; visible: app.page === "device" && !app.current.configurable }
        AboutPage { anchors.fill: parent; visible: app.page === "about" }
    }

    Toast {
        id: toast
        anchors.horizontalCenter: stage.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
        z: 10
    }

    Connections {
        target: app
        function onToastChanged() {
            if (app.toast !== "") toast.show(app.toast, app.toastIsError)
        }
    }
}

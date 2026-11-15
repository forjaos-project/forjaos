import QtQuick 2.0

Timer {
    interval: 30000
    repeat: true
    running: true

    function recordActiveWindow() {
        const active = workspace.activeWindow;
        if (!active || active.specialWindow || active.desktopWindow || active.dock || active.menu || active.popupWindow) {
            return;
        }

        const app = String(active.resourceClass || active.resourceName || "").trim();
        const title = String(active.caption || "").trim();
        if (app.length === 0 || title.length === 0) {
            return;
        }

        callDBus(
            "org.forjaos.Memory",
            "/org/forjaos/Memory",
            "org.forjaos.Memory",
            "CollectWindow",
            app.slice(0, 256),
            title.slice(0, 4096)
        );
    }

    onTriggered: recordActiveWindow()
}

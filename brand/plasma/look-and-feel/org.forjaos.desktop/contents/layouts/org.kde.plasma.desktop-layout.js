// First-login layout for FR-052. Optional launchers are added by their feature packages.
var top = new Panel;
top.location = "top";
top.height = 40;
top.floating = false;
top.lengthMode = "fill";
top.addWidget("org.kde.plasma.kickoff");
top.addWidget("org.kde.plasma.pager");
top.addWidget("org.kde.plasma.panelspacer");
top.addWidget("org.kde.plasma.digitalclock");
top.addWidget("org.kde.plasma.panelspacer");
top.addWidget("org.kde.plasma.systemtray");

var dock = new Panel;
dock.location = "bottom";
dock.height = 64;
dock.floating = true;
dock.lengthMode = "fit";
dock.alignment = "center";
var tasks = dock.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("launchers", [
    "applications:org.kde.konsole.desktop",
    "applications:org.kde.dolphin.desktop",
    "applications:org.kde.plasma-systemmonitor.desktop",
    "preferred://browser"
]);
tasks.reloadConfig();
dock.addWidget("org.kde.plasma.kickoff");

var desktops = desktopsForActivity(currentActivity());
for (var i = 0; i < desktops.length; ++i) {
    desktops[i].wallpaperPlugin = "org.kde.image";
    desktops[i].currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    desktops[i].writeConfig("Image", "file:///usr/share/wallpapers/ForjaOS/dark-abstract.png");
}

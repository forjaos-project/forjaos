# Gaming and game development

Steam and the `steam-devices` rules come from the desktop base. Gamescope, MangoHud, and BlueZ are installed from the repositories already configured in the image. At first boot, the `gamedev` profile installs Godot 4, Blender, Krita, Lutris, Heroic, and ProtonPlus for the user through Flathub. It then downloads the official export templates matching the installed Godot version, verifies their SHA-256 digest, and places them in the Flatpak data directory. If you also select VS Code, the profile installs the Godot Tools extension.

Open ProtonPlus to install Proton GE for your user account. It is not bundled in the image. Unity Hub is optional and has a separate installer (`forja install unity`).

Game Mode starts when Steam or gamescope is detected in your session. You can also use `forja game-mode on|off|status`. While active, ForjaOS requests the `performance` power profile and Plasma Do Not Disturb. `off` suppresses automatic reactivation until the current game process exits. A manual `on` remains active after the game closes.

At the final build, validate one native and two Proton games, Game Mode entry and exit, power profile, notifications, MangoHud, gamescope, and Xbox, DualSense, and 8BitDo controllers over USB and Bluetooth. Run `bash scripts/validate-godot-exports.sh <output-directory>` from a session with the gamedev profile installed to export the sample Godot project for Linux and Web. Performance with HERO/Memory enabled will be measured in F4-004.

Name:           forjaos-plasma
Version:        0.1
Release:        1%{?dist}
Summary:        ForjaOS Plasma desktop theme, fonts, and wallpapers
License:        Apache-2.0 AND CC-BY-SA-4.0 AND OFL-1.1
BuildArch:      noarch
Provides:       plasma-lookandfeel-fedora = %{base_look_evr}
Provides:       f45-backgrounds-kde = %{base_wallpaper_evr}
Requires:       jetbrains-mono-fonts

%description
Project-owned Plasma dark/light theme, first-login layout, 4K wallpapers,
Plus Jakarta Sans UI font, global shortcuts (terminal, files), Plymouth and GRUB
themes, and the Konsole profile. Exact compatibility
capabilities preserve the inherited KDE dependency graph during replacement.

%prep

%build

%install
mkdir -p %{buildroot}/usr/share/plasma/look-and-feel
cp -a %{_sourcedir}/plasma/look-and-feel/org.forjaos.desktop %{buildroot}/usr/share/plasma/look-and-feel/
mkdir -p %{buildroot}/usr/share/plasma/desktoptheme
cp -a %{_sourcedir}/plasma/desktoptheme/forja-dark %{buildroot}/usr/share/plasma/desktoptheme/
cp -a %{_sourcedir}/plasma/desktoptheme/forja-light %{buildroot}/usr/share/plasma/desktoptheme/
install -Dm0644 %{_sourcedir}/plasma/color-schemes/ForjaDark.colors %{buildroot}/usr/share/color-schemes/ForjaDark.colors
install -Dm0644 %{_sourcedir}/plasma/color-schemes/ForjaLight.colors %{buildroot}/usr/share/color-schemes/ForjaLight.colors
for wallpaper in %{_sourcedir}/wallpapers/*.png; do
    install -Dm0644 "$wallpaper" "%{buildroot}/usr/share/wallpapers/ForjaOS/${wallpaper##*/}"
done
install -Dm0644 %{_sourcedir}/fonts/PlusJakartaSans-VF.ttf %{buildroot}/usr/share/fonts/plus-jakarta-sans/PlusJakartaSans-VF.ttf
for shortcut in %{_sourcedir}/shortcuts/*.desktop; do
    install -Dm0644 "$shortcut" "%{buildroot}/usr/share/kglobalaccel/${shortcut##*/}"
done
for theme in dark light; do
    mkdir -p "%{buildroot}/usr/share/plymouth/themes/forjaos-$theme" "%{buildroot}/usr/share/grub/themes/forja-$theme"
    cp -a "%{_sourcedir}/plymouth/forjaos-$theme/." "%{buildroot}/usr/share/plymouth/themes/forjaos-$theme/"
    cp -a "%{_sourcedir}/grub/forja-$theme/." "%{buildroot}/usr/share/grub/themes/forja-$theme/"
done
install -Dm0644 %{_sourcedir}/konsole/ForjaOS.profile %{buildroot}/usr/share/konsole/ForjaOS.profile
install -Dm0644 "%{_sourcedir}/konsole/Forja Dark.colorscheme" "%{buildroot}/usr/share/konsole/Forja Dark.colorscheme"
install -Dm0644 "%{_sourcedir}/konsole/Forja Light.colorscheme" "%{buildroot}/usr/share/konsole/Forja Light.colorscheme"
install -Dm0644 %{_sourcedir}/licenses/LICENSES.md %{buildroot}/usr/share/licenses/forjaos-plasma/LICENSES.md
install -Dm0644 %{_sourcedir}/licenses/OFL.txt %{buildroot}/usr/share/licenses/forjaos-plasma/OFL.txt

%files
%license /usr/share/licenses/forjaos-plasma/LICENSES.md
%license /usr/share/licenses/forjaos-plasma/OFL.txt
/usr/share/plasma/look-and-feel/org.forjaos.desktop
/usr/share/plasma/desktoptheme/forja-dark
/usr/share/plasma/desktoptheme/forja-light
/usr/share/color-schemes/ForjaDark.colors
/usr/share/color-schemes/ForjaLight.colors
/usr/share/wallpapers/ForjaOS/
/usr/share/fonts/plus-jakarta-sans/
/usr/share/kglobalaccel/org.forjaos.terminal.desktop
/usr/share/kglobalaccel/org.forjaos.files.desktop
/usr/share/plymouth/themes/forjaos-dark
/usr/share/plymouth/themes/forjaos-light
/usr/share/grub/themes/forja-dark
/usr/share/grub/themes/forja-light
/usr/share/konsole/ForjaOS.profile
"/usr/share/konsole/Forja Dark.colorscheme"
"/usr/share/konsole/Forja Light.colorscheme"

%changelog
* Tue Nov 10 2026 ForjaOS Project <forjaos@users.noreply.github.com> - 0.1-1
- Package ForjaOS Plasma identity and preserve exact base capabilities

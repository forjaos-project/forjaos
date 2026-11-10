Name:           forjaos-branding
Version:        0.1
Release:        1%{?dist}
Summary:        ForjaOS system identity and logos
License:        Apache-2.0 AND CC-BY-SA-4.0
BuildArch:      noarch
Provides:       system-logos
Provides:       system-release
Provides:       fedora-release-identity = %{base_identity_evr}
Obsoletes:      fedora-logos <= %{base_logos_evr}
Obsoletes:      fedora-release-identity-kinoite <= %{base_identity_evr}
Requires:       fedora-release-kinoite = %{base_identity_evr}

%description
Project-owned identity files and logos for ForjaOS bootc images.

%prep

%build

%install
install -Dm0644 %{_sourcedir}/os-release %{buildroot}/usr/lib/os-release
install -Dm0644 %{_sourcedir}/80-kde-desktop.preset %{buildroot}/usr/lib/systemd/system-preset/80-kde-desktop.preset
install -Dm0644 %{_sourcedir}/icons/forjaos-256.png %{buildroot}/usr/share/pixmaps/system-logo-white.png
install -Dm0644 %{_sourcedir}/licenses/LICENSES.md %{buildroot}/usr/share/licenses/forjaos-branding/LICENSES.md
for icon in %{_sourcedir}/icons/forjaos-*.png; do
    size=${icon##*forjaos-}
    size=${size%.png}
    install -Dm0644 "$icon" "%{buildroot}/usr/share/icons/hicolor/${size}x${size}/places/start-here.png"
    install -Dm0644 "$icon" "%{buildroot}/usr/share/icons/hicolor/${size}x${size}/apps/fedora-logo-icon.png"
done
install -Dm0644 %{_sourcedir}/svg/forjaos-icon.svg %{buildroot}/usr/share/icons/hicolor/scalable/places/start-here.svg
install -Dm0644 %{_sourcedir}/svg/forjaos-icon.svg %{buildroot}/usr/share/icons/hicolor/scalable/apps/fedora-logo-icon.svg

%files
%license /usr/share/licenses/forjaos-branding/LICENSES.md
/usr/lib/os-release
/usr/lib/systemd/system-preset/80-kde-desktop.preset
/usr/share/pixmaps/system-logo-white.png
/usr/share/icons/hicolor/*/places/start-here.png
/usr/share/icons/hicolor/*/apps/fedora-logo-icon.png
/usr/share/icons/hicolor/scalable/places/start-here.svg
/usr/share/icons/hicolor/scalable/apps/fedora-logo-icon.svg

%changelog
* Mon Nov 09 2026 ForjaOS Project <forjaos@users.noreply.github.com> - 0.1-1
- Package project-owned identity and licensed logos

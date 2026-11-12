Name:           forjaos-branding
Version:        0.1
Release:        1%{?dist}
Summary:        ForjaOS installer identity and Anaconda branding
License:        Apache-2.0 AND CC-BY-SA-4.0 AND OFL-1.1
BuildArch:      noarch
Provides:       system-logos
Provides:       system-release
Provides:       fedora-release-identity = %{base_identity_evr}
Provides:       fedora-release-identity-basic = %{base_identity_evr}
Obsoletes:      fedora-logos <= %{base_logos_evr}
Obsoletes:      fedora-release-identity-basic <= %{base_identity_evr}
Requires:       fedora-release = %{base_release_evr}

%description
Project-owned identity, logo, font, and Anaconda style for the live installer.

%prep

%build

%install
install -Dm0644 %{_sourcedir}/os-release %{buildroot}/usr/lib/os-release
install -Dm0644 %{_sourcedir}/forjaos.conf %{buildroot}/etc/anaconda/profile.d/forjaos.conf
install -Dm0644 %{_sourcedir}/forjaos.css %{buildroot}/usr/share/anaconda/pixmaps/forjaos.css
install -Dm0644 %{_sourcedir}/forjaos-logo.png %{buildroot}/usr/share/anaconda/pixmaps/forjaos-logo.png
install -Dm0644 %{_sourcedir}/forjaos-logo.png %{buildroot}/usr/share/pixmaps/system-logo-white.png
install -Dm0644 %{_sourcedir}/branding.css %{buildroot}/usr/share/cockpit/branding/forjaos/branding.css
install -Dm0644 %{_sourcedir}/forjaos-logo.png %{buildroot}/usr/share/cockpit/branding/forjaos/logo.png
install -Dm0644 %{_sourcedir}/PlusJakartaSans-VF.ttf %{buildroot}/usr/share/fonts/forjaos/PlusJakartaSans-VF.ttf
install -Dm0644 %{_sourcedir}/OFL.txt %{buildroot}/usr/share/licenses/forjaos-branding/OFL.txt
install -Dm0644 %{_sourcedir}/LICENSES.md %{buildroot}/usr/share/licenses/forjaos-branding/LICENSES.md
for icon in %{_sourcedir}/forjaos-[0-9]*.png; do
    size=${icon##*forjaos-}
    size=${size%.png}
    install -Dm0644 "$icon" "%{buildroot}/usr/share/icons/hicolor/${size}x${size}/places/start-here.png"
done
install -Dm0644 %{_sourcedir}/forjaos-icon.svg %{buildroot}/usr/share/icons/hicolor/scalable/places/start-here.svg

%files
%license /usr/share/licenses/forjaos-branding/OFL.txt
%license /usr/share/licenses/forjaos-branding/LICENSES.md
/usr/lib/os-release
/etc/anaconda/profile.d/forjaos.conf
/usr/share/anaconda/pixmaps/forjaos.css
/usr/share/anaconda/pixmaps/forjaos-logo.png
/usr/share/pixmaps/system-logo-white.png
/usr/share/cockpit/branding/forjaos/branding.css
/usr/share/cockpit/branding/forjaos/logo.png
/usr/share/fonts/forjaos/PlusJakartaSans-VF.ttf
/usr/share/icons/hicolor/*/places/start-here.png
/usr/share/icons/hicolor/scalable/places/start-here.svg

%changelog
* Thu Nov 12 2026 ForjaOS Project <forjaos@users.noreply.github.com> - 0.1-1
- Brand the Anaconda live installer with project-owned assets

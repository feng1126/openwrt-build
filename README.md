# XG-040G-MD OpenWrt Snapshot Build

This repository builds OpenWrt for Nokia/Bell XG-040G-MD through GitHub Actions.

It clones official `openwrt/openwrt` directly, then builds the Airoha AN7581
`nokia_xg-040g-md-ubi` target from the selected branch. This UBI profile is
the intended profile for TC U-Boot style installs. The default branch is `main`,
which corresponds to OpenWrt snapshot development builds.

Important:

- This repository is only an automated build wrapper; the OpenWrt source is
  pulled from the official upstream repository.
- The default build is a snapshot build, not an official stable release.
- For TC U-Boot installs, use the `nokia_xg-040g-md-ubi` `sysupgrade.itb`
  image, not the non-UBI `sysupgrade.bin`.
- XG-PON behavior still needs to be validated on real hardware.

Run manually from GitHub:

1. Open Actions.
2. Select `Build XG-040G-MD OpenWrt`.
3. Click `Run workflow`.
4. Download the firmware artifact after the job finishes.

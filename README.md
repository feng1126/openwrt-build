# XG-040G-MD OpenWrt PR Build

This repository builds OpenWrt for Nokia/Bell XG-040G-MD through GitHub Actions.

It clones `openwrt/openwrt`, merges PR `23569`, then builds the Airoha AN7581 target.

Important:

- This is for testing a pending OpenWrt PR.
- It is not an official OpenWrt stable release.
- XG-PON may not work after flashing OpenWrt, according to the PR notes.

Run manually from GitHub:

1. Open Actions.
2. Select `Build XG-040G-MD OpenWrt`.
3. Click `Run workflow`.
4. Download the firmware artifact after the job finishes.


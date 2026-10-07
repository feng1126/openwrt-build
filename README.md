# XG-040G-MD OpenWrt Snapshot Build

This repository builds OpenWrt for Nokia/Bell XG-040G-MD through GitHub Actions.

It clones official `openwrt/openwrt`, then builds the Airoha AN7581
`nokia_xg-040g-md-ubi` target from the selected branch. This UBI profile is
the intended profile for TC U-Boot style installs. The default source branch is
`main`, which is the OpenWrt snapshot development branch.

Important:

- This repository is only an automated build wrapper; firmware sources are
  pulled from the official OpenWrt repository.
- The default build is a snapshot build, not an official stable release.
- For TC U-Boot installs, use the `nokia_xg-040g-md-ubi` `sysupgrade.itb`
  image, not the non-UBI `sysupgrade.bin`.
- XG-PON behavior still needs to be validated on real hardware.

Run manually from GitHub:

1. Open Actions.
2. Select `Build XG-040G-MD OpenWrt`.
3. Click `Run workflow`.
4. Keep `base_branch` as `main`, or enter an OpenWrt branch that supports the
   XG-040G-MD UBI profile. Start the workflow.
5. Download the firmware artifact after the job finishes, for example
   `xg040gmd-openwrt-main`.

The selected repository, branch and source commit are saved in `source.txt` in
the build log artifact.

PassWall and its dependency packages are vendored from the official
[Openwrt-Passwall](https://github.com/Openwrt-Passwall) GitHub repositories.
The source commits are recorded in `local_packages/passwall-upstream.json`
and copied to the build logs. The build uses Xray, including its Hysteria2 support;
standalone Sing-box, Hysteria and V2Ray plugin binaries are disabled to reduce image size.
The GeoIP package is locally changed to the pinned China/private-only asset;
other component choices use upstream defaults. There are no custom SOCKS forwarding,
DNS bypass controls, automatic node migrations or rule-update overrides.

The build configuration is stored in `configs/xg040gmd.config`. Edit this file
to change packages; configuration is not passed through the workflow input form,
which can lose line breaks. After `make defconfig`, the workflow verifies the
AN7581 XG-040G-MD UBI profile and essential LuCI packages before downloading or
compiling sources.

## MosDNS defaults

MosDNS 5.3.4-r14, LuCI 1.7.14 and its Chinese translation replace SmartDNS.
The unchanged package sources are pinned in `local_packages/mosdns-upstream.json`.
Fresh installations enable MosDNS on port 6053 with IPv4 preference for domestic
and foreign domains, while retaining IPv6-only DNS answers. Its 4096-entry cache,
prefetch, two concurrent upstreams and 120-second connection reuse are enabled.
Domestic upstreams use AliDNS/Tencent DoH; foreign upstreams use Cloudflare/Google
DoH. Configure working proxy nodes before relying on blocked foreign upstreams.

Passwall uses its upstream ChinaDNS-NG integration for domain/IP policy sets;
both direct and remote DNS point to MosDNS, with UDP for local DNS transport.
Only Passwall performs client DNS interception. MosDNS's LuCI DNS-forwarding
option is enabled; dnsmasq caching is disabled by that upstream option, leaving
DNS caching to MosDNS. No proxy credentials, nodes, or WAN credentials are added.

`files/etc/uci-defaults/99-zzz-xg040gmd-dns` installs these defaults only on a
fresh install. Retained-config upgrades and repeated initialization preserve
existing DNS choices. This profile keeps the tested Passwall classification
path; it does not implement a new MosDNS-only firewall-set integration.

Simplified Chinese is enabled with `CONFIG_LUCI_LANG_zh_Hans=y`. LuCI translation
packages are hidden Kconfig options driven by this language setting, so selecting
individual `luci-i18n-*-zh-cn` packages alone is insufficient. The workflow checks
that the base interface and Cloudflared Chinese translations remain enabled.

The Argon theme is fetched from the `master` branch of
[`jerrykuku/luci-theme-argon`](https://github.com/jerrykuku/luci-theme-argon)
at build time. Its commit is recorded in `argon-source.txt` in the build logs.

Each run uploads a separate `xg040gmd-build-logs-<run>-<attempt>` artifact even
when a step fails. It includes the seed and generated configuration, configuration
and download logs, and compilation logs for steps that ran. Failed parallel builds
are retried with one job, with the retry output saved as `build-retry.log`.

The firmware includes `luci-app-airoha-npu` and its Chinese translation. Open
**Network > Airoha NPU** to enable software and hardware flow offloading, then
click **Save & Apply**. The offloading page uses the standard firewall settings. Hardware flow offloading is
not enabled by the build or package installation; OpenWrt's default is off.
Opening the page does not modify the configuration. Upgrades retaining an existing
firewall configuration retain its offloading choices.

The upstream AN7581 target already enables the NPU driver and this board's device
tree enables its NPU node. Driver initialization is distinct from enabling traffic
offloading; this UI controls traffic offloading, not the device's power state.
The configuration explicitly includes `airoha-en7581-npu-firmware`,
`kmod-nft-offload`, and `conntrack` to preserve and inspect that support.

After flashing, run `dmesg | grep -iE 'airoha|npu|firmware'` to check driver and
firmware startup. During a routed LAN-to-WAN TCP transfer, run
`conntrack -L -o extended 2>/dev/null | grep HW_OFFLOAD`. `HW_OFFLOAD` identifies
hardware-offloaded connections; `OFFLOAD` alone identifies software offload.
Enabling the firewall option alone does not prove hardware acceleration works.

This acceleration targets eligible forwarded traffic, not the userspace
encryption performed by Passwall or Cloudflared. Test proxy routing, traffic
accounting and any SQM configuration after enabling it. To turn off acceleration,
set both `firewall.@defaults[0].flow_offloading` and
`firewall.@defaults[0].flow_offloading_hw` to `0`, commit `firewall`, then restart
the firewall service.

**Status > SoC Status** displays CPU and NPU frequencies using read-only kernel
interfaces, refreshing every five seconds. Missing values display as `N/A`.
CPU frequency controls, overclocking RPC methods, and direct register access have
been removed. The build configuration disables `/dev/mem` and BusyBox `devmem`.
The only settings provided by this app are the manual firewall flow-offloading
switches under **Network > Airoha NPU**; opening either page does not enable them.

## XG-040G-MD network defaults

Every build installs `files/etc/uci-defaults/99-zz-xg040gmd-wan` into the
firmware. OpenWrt runs it once after installation (including a sysupgrade),
after `99-default-settings`. It only applies to `nokia,xg-040g-md` and
`nokia,xg-040g-md-ubi` boards:

- `lan1`: `WAN` uses IPv4 DHCP; `WAN6` uses DHCPv6 with `reqaddress=try`
  and `reqprefix=no`, matching the tested upstream-router setup.
- `lan2`, `lan3`, `lan4`: remain in `br-lan`, using the default LAN address
  `10.10.10.10/24`. Detailed DHCP event logging is disabled.
- Both WAN interfaces belong to the `wan` firewall zone, with IPv4
  masquerading, MSS clamping and LAN-to-WAN forwarding. Existing zone
  policies and the standard DHCPv6/ICMPv6 rules are preserved.

Network defaults are applied only on a fresh installation or an upgrade
without retained settings. On a retained-config upgrade, the OpenWrt restore
archive causes both network initialization scripts to preserve WAN, LAN,
firewall and DHCP choices, including PPPoE credentials. A persistent
`network.globals.xg040gmd_defaults=1` flag prevents subsequent reruns from
resetting the network. Detailed DHCP event logging is explicitly disabled,
including when upgrading from a firmware that enabled it. IPv6 prefix
delegation to downstream LAN clients is not requested on a fresh installation.
DDNS credentials and per-device service settings are not included.
The build verifies that the target profile and `odhcp6c` are enabled before
installing the script. IPv6 still requires an upstream IPv6 router/service.

## NATMap

The firmware defaults to the locally vendored muink enhanced NATMap packages:
`luci-app-natmapt`, its Simplified Chinese translation, and the matching `natmapt`
backend. The original `natmap` and `luci-app-natmap` packages are disabled to avoid
conflicting service, configuration and LuCI files. Package source commits are
recorded in each vendored package's `SOURCE` file. The workflow checks these
selections after `make defconfig`. Configure mappings in LuCI after flashing.

### DDNS and NATMap recovery

The firmware includes the Cloudflare-Origin NATMap updater with separate origin
rules for each hostname, and plain HTTP forwarding for Codex and SSH web.
Use `http://codex.fengown.top` and `http://ssh.fengown.top`; origin rules select
the current NATMap ports automatically. No certificate is required. An upgrade
converts preserved older proxy configs from HTTPS to HTTP. Existing Cloudflare
IPv6 services check their actual origin IP using the provider API; dynv6 IPv6
services obtain the address from `pppoe-WAN` without forcing IPv6 API transport.
Tokens stay in the router configuration and are never baked into the firmware.
The sysupgrade preservation list includes `/etc/natmap/`.

## Full Cone NAT

Includes pinned ImmortalWrt Full Cone module and userspace patches, disabled by
default. After flashing, use **Network > Firewall > General Settings > Full Cone NAT**
to enable IPv4 Full Cone for masquerading zones. This improves UDP peer
connectivity, not bandwidth. See [patch sources and verification](patches/fullcone/README.md).

## Geo data size and updates

Firmware embeds the pinned `geoip-only-cn-private.dat` asset (about 134 KiB)
to reduce image size. GeoSite remains complete. Update settings use upstream
defaults: MosDNS automatic updates are off, its manual GeoIP update uses the slim
asset, and Passwall's GeoIP update URL uses the full asset. Both services share
`/usr/share/v2ray/`. Other country GeoIP tags require downloading and loading the
full database. `99-zzzz-xg040gmd-geodata` only undoes the previous custom update
policy when its migration marker exists; fresh installations use upstream defaults.

The workflow fixes the legacy SmartDNS LuCI array-to-boolean status bug after
feeds installation. SmartDNS remains disabled in the MosDNS firmware profile;
the source fix also applies if SmartDNS is selected in a future profile.


## Nokia XG-040G-MD PON 移植

本分支保留官方 OpenWrt 底版，并通过 `scripts/apply-pon.py` 集成 PonWrt 的 PON 内核接口、PCS 和 Nokia UBI 板级适配，以及两个 PON feed 的软件包源码。源码提交和文件校验值见 `patches/pon/sources.json`。工作流固定到已验证的官方 OpenWrt 提交；更新底版需要重新对比补丁，不直接追随 main。

编译配置包含 `kmod-airoha-xpon`、`kmod-airoha-en7572`、`airoha-ponctl`、`airoha-pond`、诊断工具、PON 和 IPTV LuCI 页面。`airoha-paged-bosa` 保留在源码中，目标 Nokia 使用 EN7572，无需选中。所有 PON 包保持同级目录，确保驱动共享头文件和符号版本依赖正确。

适用目标为 `nokia_xg-040g-md-ubi`、Linux 6.18。现有用户配置会覆盖首次启动的网络默认值；升级后应在 LuCI 检查 WAN 设备是否为 `pon0`，并按线路需要设置 VLAN 和上网协议。PON 模式默认留空，需要在“网络 → PON”配置。使用设备自身的 BOSA 校准和 RI 数据；迁移不会自动生成认证信息，也不会刷写设备。

上游协议状态：XG-PON 和 10G/1G EPON 已测试；XGS-PON 和 10G/10G EPON 尚未测试；GPON 和 1G EPON 尚未实现。固件编译通过不代表已经完成光线路注册和业务实测。

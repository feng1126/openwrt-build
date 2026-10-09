# Nokia XG-040G-MD OpenWrt 固件编译

通过 GitHub Actions 为 Nokia/Bell XG-040G-MD 编译 OpenWrt，基于官方 OpenWrt，集成 PON 适配、LuCI 中文界面、Passwall、MosDNS、NATMap 和内存优化配置。

| 项目 | 当前配置 |
| --- | --- |
| 编译仓库分支 | `main` |
| 平台 / 设备 | Airoha AN7581 / `nokia_xg-040g-md-ubi` |
| OpenWrt 底版 | 每次获取所选上游分支的最新提交，默认 `openwrt/openwrt` 的 `main` |
| 自动构建 | 已迁移至 [immortal-build](https://github.com/feng1126/immortal-build)，本仓库保留手动构建 |
| 自动发布 | 构建成功后发布 GitHub Release，标记为 Latest |
| 压缩交换 | **128 MiB zram**，`lzo-rle`，优先级 `100` |
| HAProxy | 系统服务默认关闭，由 Passwall 负载均衡按需启动 |

## 下载与构建

- [下载最新发布固件](https://github.com/feng1126/openwrt-build/releases/latest)
- [查看构建进度与日志](https://github.com/feng1126/openwrt-build/actions/workflows/build-xg040gmd.yml)
- [查看编译配置](configs/xg040gmd.config)

每日北京时间 03:17 的自动构建与发布已迁移至 [immortal-build](https://github.com/feng1126/immortal-build)，使用最新 ImmortalWrt `master`。本仓库保留官方 OpenWrt 手动构建，成功后仍可发布固件。

本仓库手动构建使用获取源码时最新的官方 OpenWrt `main`，不再固定底版提交。实际提交记录在 `source.txt` 和发布说明中。本地软件包与 PON 移植来源仍保留各自版本记录，不会因此自动更新。PON 集成仍检查 Linux 6.18、覆盖文件校验值和补丁兼容性；遇到不兼容的上游变更会停止构建，不会自动回退旧底版或发布失败产物。

手动构建：

1. 打开 **Actions → Build XG-040G-MD OpenWrt → Run workflow**。
2. 仓库分支选择 `main`，`base_branch` 通常保持 `main`。
3. 等待构建完成，从 Releases 或 `xg040gmd-openwrt-main` 产物下载固件。

`base_branch` 选择上游源码分支，编译该分支在获取源码时的最新提交。其他分支也必须通过现有 PON 内核与补丁兼容性检查。

每次构建上传独立的 `xg040gmd-build-logs-<run>-<attempt>` 诊断产物，保留 14 天。记录包含源码提交、配置、下载与编译日志。并行编译失败后会单线程重试，输出保存为 `build-retry.log`。

## 固件与设备说明

- 这是自行构建的 OpenWrt Snapshot 固件，不是官方稳定版。
- TC U-Boot 安装使用 UBI 目标的 `sysupgrade.itb`，不要混用非 UBI 目标的 `sysupgrade.bin`。
- 编译成功不代表所有光接入模式均已在本设备验证；具体 PON 状态见文末。
- 构建不会自动刷写设备，也不内置代理节点、WAN 密码、DDNS 或 Cloudflare 凭据。

## 内存优化与 HAProxy

固件包含同次编译生成的 `kmod-zram` 和官方 `zram-swap` 启动脚本，开机启用压缩交换。默认配置如下：

```text
system.@system[0].zram_size_mb=128
system.@system[0].zram_comp_algo=lzo-rle
system.@system[0].zram_priority=100
```

[初始化脚本](files/etc/uci-defaults/99-zzz-xg040gmd-zram)在首次启动或保留配置升级时补齐缺失项，保留已有自定义值。zram 按实际压缩数据占用物理内存，128 MiB 是逻辑容量，并非启动时立即占用 128 MiB RAM。

查看运行状态：

```sh
free
cat /proc/swaps
cat /sys/block/zram0/mm_stat
```

[HAProxy 初始化脚本](files/etc/uci-defaults/99-zzz-xg040gmd-haproxy)停止并禁用系统独立服务，包括保留配置升级，避免默认示例配置常驻。软件包仍保留；在 Passwall 开启 **HAProxy 负载均衡**并保存应用后，由 Passwall 启动专用实例，停止或重启时清理。Xray 自带的节点均衡不依赖 HAProxy。

这些设置用于减少无用常驻占用、缓冲内存峰值；没有额外修改 Passwall 的网络事件、规则更新或重启逻辑。

## 编译配置与主要组件

修改 [configs/xg040gmd.config](configs/xg040gmd.config)选择软件包。工作流在 `make defconfig` 后检查设备目标、主要组件、zram 和压缩算法，避免配置静默失效。下载缓存和编译器缓存用于加快后续构建。

PassWall and its dependency packages are vendored from the official
[Openwrt-Passwall](https://github.com/Openwrt-Passwall) GitHub repositories.
The source commits are recorded in `local_packages/passwall-upstream.json`
and copied to the build logs. The build uses Xray, including its Hysteria2 support;
standalone Sing-box, Hysteria and V2Ray plugin binaries are disabled to reduce image size.
The GeoIP package is locally changed to the pinned China/private-only asset;
other component choices use upstream defaults. There are no custom SOCKS forwarding,
DNS bypass controls, automatic node migrations or rule-update overrides.

## MosDNS 与 DNS 默认配置

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

## NPU 与硬件加速

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
NPU firmware is installed by the official OpenWrt `linux-firmware` package;
this repository does not override its binaries in the image overlay.
The NPU LuCI application and PON driver adaptations are retained.

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
CPU frequency controls and overclocking RPC methods have been removed from
the application. The current build configuration enables kernel `/dev/mem`
and BusyBox `devmem`; the read-only status page does not use them.
The only settings provided by this app are the manual firewall flow-offloading
switches under **Network > Airoha NPU**; opening either page does not enable them.

## 网络默认配置

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

## Geo 数据体积与更新

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


## ZeroTier 局域网访问

ZeroTier 页面提供“允许局域网访问 ZeroTier”开关，控制 `lan → zerotier` 转发及 IPv4 地址伪装，按 `zt+` 匹配 ZeroTier 接口。新安装默认关闭，保留已有开关状态；保存并应用后生效。IP、网段和路由由实际 LAN 配置及 ZeroTier 网络下发，不固定虚拟 IP 或网关。局域网客户端需以本路由器为网关，ZeroTier 节点仍需在控制台授权。未配置 ZeroTier 到 LAN 的主动转发。

当 ZeroTier 使用 `/etc/` 下的自定义配置目录时，默认脚本会创建该目录并将其加入 `/etc/sysupgrade.conf`，保留已有身份文件。ZeroTier 的启用状态保持用户原设置。

## Nokia XG-040G-MD PON 移植

main 分支保留官方 OpenWrt 底版，并通过 `scripts/apply-pon.py` 集成 PonWrt 的 PON 内核接口、PCS 和 Nokia UBI 板级适配，以及两个 PON feed 的软件包源码。源码提交和文件校验值见 `patches/pon/sources.json`。工作流跟随官方 OpenWrt 所选分支的最新提交，默认 main；`sources.json` 中的 OpenWrt 提交仅记录 PON 移植参考底版。内核版本、覆盖文件和补丁检查继续保留，上游变化不兼容时需要重新适配。

编译配置包含 `kmod-airoha-xpon`、`kmod-airoha-en7572`、`airoha-ponctl`、`airoha-pond`、诊断工具、PON 和 IPTV LuCI 页面。`airoha-paged-bosa` 保留在源码中，目标 Nokia 使用 EN7572，无需选中。所有 PON 包保持同级目录，确保驱动共享头文件和符号版本依赖正确。

适用目标为 `nokia_xg-040g-md-ubi`、Linux 6.18。现有用户配置会覆盖首次启动的网络默认值；升级后应在 LuCI 检查 WAN 设备是否为 `pon0`，并按线路需要设置 VLAN 和上网协议。PON 模式默认留空，需要在“网络 → PON”配置。使用设备自身的 BOSA 校准和 RI 数据；迁移不会自动生成认证信息，也不会刷写设备。

上游协议状态：XG-PON 和 10G/1G EPON 已测试；XGS-PON 和 10G/10G EPON 尚未测试；GPON 和 1G EPON 尚未实现。固件编译通过不代表已经完成光线路注册和业务实测。

PON 补丁清理：不再重复覆盖官方已有的 pinctrl SCU 查找补丁；未启用实验桥接卸载，因此移除原生 L2B 布局补丁。官方底版自带的相关补丁继续保留。PON 数据/控制通道、PCS/光模块 GPIO、PPE GEM/T-CONT 元数据、共享 QDMA/DMA、VLAN MTU、NPU mailbox 超时和外部 SerDes NBQ 修复保留，分别服务于光接入、数据通道正确性和驱动稳定性。

# Nokia XG-040G-MD OpenWrt 固件编译

通过 GitHub Actions 为 Nokia/Bell XG-040G-MD 编译 OpenWrt，基于官方 OpenWrt，集成 PON 适配、LuCI 中文界面、Passwall、AdGuardHome、NATMap 和内存优化配置。

| 项目 | 当前配置 |
| --- | --- |
| 编译仓库分支 | `main` |
| 平台 / 设备 | Airoha AN7581 / `nokia_xg-040g-md-ubi` |
| OpenWrt 底版 | 每次获取所选上游分支的最新提交，默认 `openwrt/openwrt` 的 `main` |
| 自动构建 | 每日北京时间 03:27，保留手动构建 |
| 自动发布 | 构建成功后发布 GitHub Release，标记为 Latest |
| 压缩交换 | **128 MiB zram**，`lzo-rle`，优先级 `100` |
| HAProxy | 系统服务默认关闭，由 Passwall 负载均衡按需启动 |

## 下载与构建

- [下载最新发布固件](https://github.com/feng1126/openwrt-build/releases/latest)
- [查看构建进度与日志](https://github.com/feng1126/openwrt-build/actions/workflows/build-xg040gmd.yml)
- [查看编译配置](configs/xg040gmd.config)

每日北京时间 03:27 自动构建最新官方 OpenWrt `main` 并在成功后发布固件，GitHub 调度可能延迟。[immortal-build](https://github.com/feng1126/immortal-build) 独立构建 ImmortalWrt。

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

PassWall 的 DNS 页面增加“其他直连 DNS”列表，适用于 ChinaDNS-NG + UDP
直连解析。多个服务器一起交给 ChinaDNS-NG 查询，Xray 仍只使用主 DNS。
例如主 DNS 为 `211.137.58.20`，额外添加 `211.137.64.163`、`119.29.29.29`。
此功能不会覆盖现有 DNS 配置，新增列表默认为空。

## AdGuard Home 增强界面

固件包含官方 `adguardhome` 核心、固定 v1.21 的
[stevenjoezhang 增强版 LuCI](https://github.com/stevenjoezhang/luci-app-adguardhome)
和中文语言包，来源记录在 `local_packages/adguardhome-upstream.json`。
界面保留运行日志、YAML 编辑、路径设置和通过 firewall4/nftables 管理的 DNS
重定向选项，已移除 GitHub 关注提示，并修正进程检测和跨文件系统保存 YAML。

默认工作目录为 `/mnt/sda1/AdGuardHome`，配置文件为该目录下的
`adguardhome.yaml`，运行日志为 `runtime.log`。硬盘未挂载时跳过启动，避免把数据
写入路由器闪存；硬盘挂载后可在“服务 → AdGuard Home”启用或重启。
已有硬盘配置继续使用；没有配置时通过 `http://路由器地址:3000` 完成初始化。
默认不接管 DNS，也不内置账号、密码、设备 UUID 或当前硬盘的 swap 配置。
启用重定向前需要确认监听地址、IPv6 和 Passwall 的 DNS 链路。
只启用增强界面管理的 `AdGuardHome` 服务，禁用核心附带的同名小写服务，避免重复启动。

## DNS 软件与升级兼容

固件包含 AdGuardHome、Passwall 和可选的 SmartDNS，不再编译 MosDNS、LuCI 页面及其专用 geo2txt 工具。首次安装不预设 DNS 劫持；按实际网络配置 AdGuardHome 或 Passwall。保留配置升级时，如 DNS 仍指向已移除的 127.0.0.1:6053，首次启动脚本会将 Passwall 直连 DNS 改为 223.5.5.5、远程 DNS 改为 1.1.1.1，并将 dnsmasq 的该上游替换为 223.5.5.5。其他现有 DNS 设置不变。

The firmware includes the ASIX AX88179 USB Ethernet driver; matching USB networking
module APKs and PHY/MII dependencies are attached to each release.

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
to enable IPv4 / IPv6 Full Cone for masquerading zones. This improves UDP peer
connectivity, not bandwidth. See [patch sources and verification](patches/fullcone/README.md).

## Geo 数据体积与更新

Firmware embeds the pinned `geoip-only-cn-private.dat` asset (about 134 KiB)
to reduce image size. GeoSite remains complete. Passwall uses its upstream GeoIP update settings; other country tags require the
full GeoIP database. The former MosDNS update migration is no longer included.

The workflow fixes the legacy SmartDNS LuCI array-to-boolean status bug after
feeds installation. The fix applies to the included SmartDNS LuCI interface.


## ZeroTier 局域网访问

ZeroTier 页面提供“允许局域网访问 ZeroTier”开关，控制 `lan → zerotier` 转发及 IPv4 地址伪装，按 `zt+` 匹配 ZeroTier 接口。新安装默认关闭，保留已有开关状态；保存并应用后生效。IP、网段和路由由实际 LAN 配置及 ZeroTier 网络下发，不固定虚拟 IP 或网关。局域网客户端需以本路由器为网关，ZeroTier 节点仍需在控制台授权。未配置 ZeroTier 到 LAN 的主动转发。

当 ZeroTier 使用 `/etc/` 下的自定义配置目录时，默认脚本会创建该目录并将其加入 `/etc/sysupgrade.conf`，保留已有身份文件。ZeroTier 的启用状态保持用户原设置。

构建还会修复 ZeroTier 后端启动脚本：每次启动时，如果 `/etc/` 下的持久目录缺失，自动创建并设为 `0700`，再按原配置复制或链接。即使首次启动后目录被删除或用户重新指定 `/etc/zerotier`，也不会因目录不存在而直接退出。已有目录内容、节点密钥和网络配置沿用原启动逻辑；外部磁盘目录缺失仍会报错，不在未挂载时自动创建替代目录。构建日志保存为 `zerotier-startup-fix.log`。

## Nokia XG-040G-MD PON 移植

main 分支保留官方 OpenWrt 底版，并通过 `scripts/apply-pon.py` 集成 PonWrt 的 PON 内核接口、PCS 和 Nokia UBI 板级适配，以及两个 PON feed 的软件包源码。源码提交和文件校验值见 `patches/pon/sources.json`。工作流跟随官方 OpenWrt 所选分支的最新提交，默认 main；`sources.json` 中的 OpenWrt 提交仅记录 PON 移植参考底版。内核版本、覆盖文件和补丁检查继续保留，上游变化不兼容时需要重新适配。

编译配置包含 `kmod-airoha-xpon`、`kmod-airoha-en7572`、`airoha-ponctl`、`airoha-pond`、诊断工具、PON 和 IPTV LuCI 页面。`airoha-paged-bosa` 保留在源码中，目标 Nokia 使用 EN7572，无需选中。所有 PON 包保持同级目录，确保驱动共享头文件和符号版本依赖正确。

适用目标为 `nokia_xg-040g-md-ubi`、Linux 6.18。现有用户配置会覆盖首次启动的网络默认值；升级后应在 LuCI 检查 WAN 设备是否为 `pon0`，并按线路需要设置 VLAN 和上网协议。PON 模式默认留空，需要在“网络 → PON”配置。使用设备自身的 BOSA 校准和 RI 数据；迁移不会自动生成认证信息，也不会刷写设备。

上游协议状态：XG-PON 和 10G/1G EPON 已测试；XGS-PON 和 10G/10G EPON 尚未测试；GPON 和 1G EPON 尚未实现。固件编译通过不代表已经完成光线路注册和业务实测。

PON 补丁清理：不再重复覆盖官方已有的 pinctrl SCU 查找补丁；原生 L2B 布局修复已单独移植，但不启用实验桥接卸载。官方底版自带的相关补丁继续保留。PON 数据/控制通道、PCS/光模块 GPIO、PPE GEM/T-CONT 元数据、共享 QDMA/DMA、VLAN MTU、NPU mailbox 超时和外部 SerDes NBQ 修复保留，分别服务于光接入、数据通道正确性和驱动稳定性。

PON 启动修复：同步 openwrt-pon-drivers 的 `383e43f3619e`，在数据通道未就绪时停止 TX 队列使用 `netif_tx_stop_all_queues()`，避免延迟探测阶段的 `netif_tx_disable()` 锁竞争导致启动卡住。上游驱动版本及文件校验值记录在 `patches/pon/sources.json`。

2026-10-17 main 适配：使用上游新版 LRO、MIB 统计、BQL、skb 分片 DMA 和包含 VLAN 二层开销的 MTU 实现，移除重复补丁。重新合并 phylink/PCS 与 PON 控制、数据通道：OMCI/OAM 原始控制帧独立于以太网 LRO 接收；共享发送完成路径只对以太网私有结构访问 `txq_lock`，避免将控制接口私有数据当成以太网结构；保留 GEM/T-CONT/LLID 映射和配置去重。工作流下载内核后先以 `--fuzz=0` 验证完整内核补丁序列，再进入编译，日志为 `pon-kernel-patches.log`。此适配的实际光线路行为仍需新固件验证。

PON 配置优化：在 `flow_offload_mutex` 内按字段比较业务映射和 QDMA 承载参数，相同配置不再替换映射、清除 PPE 表项或等待网络 RCU 同步。映射顺序及字段变化、清空和恢复业务仍按原路径处理；逐字段比较避免结构体填充字节影响判断。此优化减少重复配置的开销，不改变光线路检测、注册时序或动态 P-bit 卸载限制。验证命令：`python3 tests/test-pon-config-dedup.py`。实机性能收益仍需新固件负载测试。

PON 重复业务配置优化：确认本次激活周期的 T-CONT 分配后，只有已配置、carrier 有效且完整业务映射相同才跳过 GEM 重写及 carrier/TX 队列切换。T-CONT 重分配、断线恢复、配置失败重试和单播/组播变化仍执行配置。验证命令：`python3 tests/test-pon-data-path-dedup.py`。

PON 状态查询内存优化：OMCI/OAM 控制请求共用 256 字节读缓冲（原默认 8 KiB），单行请求限制为 1024 字节，保持 STATUS、DATAPATH、EVENTS 命令及响应格式不变。减少查询时临时缓冲分配，限制异常长请求的内存增长；不缩减业务队列、诊断事件历史或 OMCI 重传缓存。用户态测试：在 `local_packages/pon/airoha-pon-daemons/src` 执行 `cargo test --locked`。

EN7572 校准诊断：A0 TX DDMI 回退只接受有效 A2 校准表中非擦除的 TSSI 字段，保留原生 A0 字段；回退只修改内存中的四字节检测字段。新增 `calibration_profile` 和 `tx_ddmi_calibration` 状态，区分整表校准与发射功率校准来源，LuCI 对 A2 回退明确标注测量未验证。此改动不补齐缺失的 A0 校准，也不保证修复发射功率读数。验证：`python3 tests/test-en7572-calibration.py`。

## NPS 客户端

固件内置 `npc` v0.26.38 ARM64 官方发布客户端与 `luci-app-nps`，下载文件使用 SHA256 校验。入口为 **服务 → NPS 客户端**，支持连接配置、运行状态及启停。公网端口转发在 NPS 服务端管理。新安装默认不启用，不内置服务器地址或密钥；保留配置升级沿用 `/etc/config/npc` 的设置。

FullCone uses one IPv4 / IPv6 toggle in LuCI; enabling or disabling it updates both `fullcone` and `fullcone6`. IPv6 rules apply only to zones with IPv6 masquerading enabled; native IPv6 routing is unchanged.

FullCone 补丁根据 nftables 版本自动选择：旧版本沿用原补丁，1.1.7 及更新版本使用适配全局 NAT 词法规则的补丁。构建前仍执行源码准备和关键符号检查。

libnftnl 1.3.2 及更新版本的 FullCone 回调使用新增 `byteorder` 参数；脚本按库版本选择对应补丁，兼容旧库接口。

2026-10-17 PonWrt 兼容性修复：移植 `8fb27e6f5c6a`，将 fraglist GRO 恢复为默认关闭、按需开启，保留普通 GRO，避免 IPv4 组播转发因 GRO 大包和 DF 检查丢弃 IPTV 数据。移植 `e4d0908bb06a`，使用 AN7581 原生 L2B 表项布局，保留硬件学习的入口键和源 MAC，修正桥接查表与 debugfs 解码；原生 L2B 暂不使用未经验证的 NPU 统计布局。不改变现有桥接卸载开关。补丁来源与 SHA256 记录在 `patches/pon/sources.json`，实际 IPTV 和桥接转发需新固件验证。

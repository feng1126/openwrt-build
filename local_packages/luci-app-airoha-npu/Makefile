# This is free software, licensed under the Apache License, Version 2.0 .

include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-airoha-npu
PKG_VERSION:=1.0.2
PKG_RELEASE:=6

PKG_LICENSE:=Apache-2.0

LUCI_TITLE:=LuCI Airoha NPU Control
LUCI_DEPENDS:=+luci-base +luci-app-firewall +kmod-nft-offload @TARGET_airoha

include $(TOPDIR)/feeds/luci/luci.mk

# call BuildPackage - OpenWrt buildroot signature

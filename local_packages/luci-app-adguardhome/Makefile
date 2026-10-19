# Copyright (C) 2018-2019 Lienol
#
# This is free software, licensed under the Apache License, Version 2.0 .
#

include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-adguardhome
PKG_VERSION:=1.21
PKG_RELEASE:=2
PKG_MAINTAINER:=<https://github.com/stevenjoezhang/luci-app-adguardhome>

LUCI_TITLE:=LuCI app for AdGuard Home
LUCI_DEPENDS:=+adguardhome +luci-compat +curl
LUCI_PKGARCH:=all
LUCI_DESCRIPTION:=A powerful LuCI interface for managing AdGuard Home - a DNS-based ad and tracker blocker that protects all devices on your network

define Package/$(PKG_NAME)/conffiles
/etc/config/AdGuardHome
endef

include $(TOPDIR)/feeds/luci/luci.mk

# call BuildPackage - OpenWrt buildroot signature

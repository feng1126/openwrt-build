include $(TOPDIR)/rules.mk

PKG_NAME:=mt7603u
PKG_RELEASE:=1
PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/ChalesYu/buildroot_platform_hardware_wifi_mtk_drivers_mt7603.git
PKG_SOURCE_VERSION:=963ca6ea0bfa0045848cb0c3f0631ac35823d213
PKG_SOURCE_DATE:=2022-03-04
PKG_MIRROR_HASH:=skip
PKG_LICENSE:=GPL-2.0
PKG_BUILD_PARALLEL:=1

include $(INCLUDE_DIR)/kernel.mk
include $(INCLUDE_DIR)/package.mk

define KernelPackage/mt7603u
  SUBMENU:=Wireless Drivers
  TITLE:=Experimental MediaTek MT7603U USB wireless driver
  DEPENDS:=+kmod-usb-core +kmod-cfg80211 +mt7603-firmware
  FILES:=$(PKG_BUILD_DIR)/mt7603usta.ko
endef

define Build/Prepare
	$(call Build/Prepare/Default)
	$(CP) $(PKG_BUILD_DIR)/Makefile.backports $(PKG_BUILD_DIR)/Makefile
endef

NOSTDINC_FLAGS := \
  $(KERNEL_NOSTDINC_FLAGS) \
  -I$(STAGING_DIR)/usr/include/mac80211-backport/uapi \
  -I$(STAGING_DIR)/usr/include/mac80211-backport \
  -I$(STAGING_DIR)/usr/include/mac80211/uapi \
  -I$(STAGING_DIR)/usr/include/mac80211 \
  -include backport/autoconf.h \
  -include backport/backport.h

define Build/Compile
	+$(KERNEL_MAKE) $(PKG_JOBS) M="$(PKG_BUILD_DIR)" \
    NOSTDINC_FLAGS="$(NOSTDINC_FLAGS)" modules
endef

define KernelPackage/mt7603u/install
	$(INSTALL_DIR) $(1)/lib/firmware
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/mt7603_firmware/MT7603USTA.dat $(1)/lib/firmware/
endef

$(eval $(call KernelPackage,mt7603u))

require("luci.sys")
require("luci.util")
require("io")
local m,s,o,o1
local fs=require"nixio.fs"
local uci=require"luci.model.uci".cursor()
local configpath=uci:get("AdGuardHome","AdGuardHome","configpath") or "/etc/AdGuardHome.yaml"
local binpath=uci:get("AdGuardHome","AdGuardHome","binpath") or "/usr/bin/AdGuardHome/AdGuardHome"
local manual_gfw_update = false
httpport=uci:get("AdGuardHome","AdGuardHome","httpport") or "3000"
m = Map("AdGuardHome", "AdGuard Home")
m.description = translate("A powerful LuCI interface for managing AdGuard Home - a DNS-based ad and tracker blocker that protects all devices on your network")
m:section(SimpleSection).template  = "AdGuardHome/status"

s = m:section(TypedSection, "AdGuardHome")
s.anonymous=true
s.addremove=false

---- Basic Settings ----
s:tab("basic", translate("Basic Settings"))

-- enable
o = s:taboption("basic", Flag, "enabled", translate("Enable"))
o.default = 0
o.optional = false

-- httpport
o = s:taboption("basic", Value, "httpport", translate("Browser management port"))
o.default=3000
o.datatype="port"
o.optional = false
o.description = translate("<input type=\"button\" class=\"cbi-button cbi-button-apply\" value=\"AdGuardHome Web: "..httpport.."\" onclick=\"window.open('http://'+window.location.hostname+':"..httpport.."/')\"/>")

-- username
o = s:taboption("basic", Value, "username", translate("Browser management username"), translate("If no change is needed, leave it empty"))
o.default     = ""
o.datatype    = "string"
o.optional = false

-- chpass
o = s:taboption("basic", Value, "hashpass", translate("Browser management password"), translate("Press calculate and then save/apply").."<br/>"..translate("If no change is needed, leave it empty"))
o.default     = ""
o.datatype    = "string"
o.template = "AdGuardHome/chpass"
o.optional = false

-- update warning not safe
local e = ""
if not fs.access(binpath) then
	e = "<font color=red>"..translate("No core").."</font>"
else
	local tmp = luci.sys.exec(binpath.." --version 2>/dev/null | grep -m 1 -E '[0-9]+[.][Bbeta0-9\.\-]+' -o")
	local version = string.sub(tmp, 1, -2)
	if version == "" then
		e = "<font color=red>"..translate("Core error").."</font>"
	else
		e = "<font color=green>"..version.."</font>"
	end
end
if not fs.access(configpath) then
	e = e.." ".."<font color=red>"..translate("No config").."</font>"
end
o = s:taboption("basic", Button,"restart",translate("Update"))
o.inputtitle=translate("Update core version")
o.template = "AdGuardHome/update"
o.showfastconfig = (not fs.access(configpath))
o.description = string.format(translate("Core version:").." <strong><font color=green>%s</font></strong><br/>"..translate("If you've modified any related core settings, please save/apply the changes before clicking Update"), e)

-- Redirect
o = s:taboption("basic", ListValue, "redirect", translate("DNS redirect mode"))
o:value("none", translate("None"))
o:value("redirect", translate("Redirect 53 port to AdGuardHome"))
o:value("dnsmasq-upstream", translate("Run as dnsmasq upstream server"))
o:value("exchange", translate("Use port 53 to replace dnsmasq"))
o.default     = "none"
o.optional = false

-- wait net on boot
o = s:taboption("basic", Flag, "waitonboot", translate("Restart when the network is ready after boot"))
o.default = 1
o.optional = false

---- Core Settings ----
s:tab("core", translate("Core Settings"))

-- bin path
o = s:taboption("core", Value, "binpath", translate("AdGuardHome executable file path"), translate("If the executable file does not exist, it will be downloaded automatically"))
o.default     = "/usr/bin/AdGuardHome/AdGuardHome"
o.datatype    = "string"
o.optional = false
o.rmempty=false
o.validate=function(self, value)
if value=="" then return nil end
if fs.stat(value,"type")=="dir" then
	fs.rmdir(value)
end
if fs.stat(value,"type")=="dir" then
	if (m.message) then
	m.message =m.message.."\nerror!bin path is a dir"
	else
	m.message ="error!bin path is a dir"
	end
	return nil
end
return value
end
--- arch
o = s:taboption("core", ListValue, "arch", translate("Executable file architecture"))
o:value("",translate("Auto"))
o:value("386", "i386")
o:value("amd64", "x86_64")
o:value("armv5", "armv5")
o:value("armv6", "armv6")
o:value("armv7", "armv7")
o:value("arm64", "aarch64")
o:value("mips_softfloat", "mips")
o:value("mips64_softfloat", "mips64")
o:value("mipsle_softfloat", "mipsel")
o:value("mips64le_softfloat", "mips64el")
o:value("ppc64le", "powerpc64")
o:value("riscv64", "riscv64")
o.default=""
o.rmempty=true

--- upx
o = s:taboption("core", ListValue, "upxflag", translate("Use upx to compress executable"))
o:value("", translate("None"))
o:value("-1", translate("Compress faster"))
o:value("-9", translate("Compress better"))
o:value("--best", translate("Compress best (slow)"))
o:value("--brute", translate("Try all available compression methods & filters (slower)"))
o:value("--ultra-brute", translate("Try even more compression variants (very slow)"))
o.default     = ""
o.description=translate("Reduce executable size, but may have compatibility issues after compression")
o.rmempty = true

-- work dir
o = s:taboption("core", Value, "workdir", translate("Work dir"), translate("Enter the full directory path. The configuration file is stored in this directory."))
o.default     = "/mnt/sda1/AdGuardHome"
o.datatype    = "string"
o.optional = false
o.rmempty=false
o.validate=function(self, value)
if not value or not value:match("^/[A-Za-z0-9_./-]+$") or value:find("..", 1, true) or value:find("//", 1, true) then
	return nil, translate("Enter an absolute directory path without spaces or '..'.")
end
value = value:gsub("/+$", "")
if value == "" then return nil end
if fs.stat(value,"type")=="reg" then
	if m.message then
	m.message =m.message.."\nerror!work dir is a file"
	else
	m.message ="error!work dir is a file"
	end
	return nil
end
local mount = value:match("^(/mnt/[^/]+)")
if mount and not (fs.readfile("/proc/mounts") or ""):find(" " .. mount .. " ", 1, true) then
	return nil, translate("The selected storage device is not mounted.")
end
return value
end
o.write=function(self, section, value)
	local olddir = uci:get("AdGuardHome", section, "workdir") or ""
	if olddir ~= value then
		local oldconfig = uci:get("AdGuardHome", section, "configpath") or (olddir .. "/adguardhome.yaml")
		local newconfig = value .. "/adguardhome.yaml"
		if not fs.mkdirr(value) then
			error("Cannot create AdGuard Home work directory")
		end
		if not fs.access(newconfig) and fs.access(oldconfig) then
			local contents = assert(fs.readfile(oldconfig), "Cannot read AdGuard Home configuration")
			local oldrules_pattern = (olddir .. "/upstreams-gfw.txt"):gsub("([^%w])", "%%%1")
			contents = contents:gsub(oldrules_pattern, value .. "/upstreams-gfw.txt")
			assert(fs.writefile(newconfig, contents), "Cannot copy AdGuard Home configuration")
		end
		local oldrules = olddir .. "/upstreams-gfw.txt"
		local newrules = value .. "/upstreams-gfw.txt"
		if not fs.access(newrules) and fs.access(oldrules) then
			assert(fs.writefile(newrules, fs.readfile(oldrules)), "Cannot copy DNS upstream list")
		end
		self.map.uci:set("AdGuardHome", section, "configpath", newconfig)
		local logfile = uci:get("AdGuardHome", section, "logfile")
		if logfile == olddir .. "/runtime.log" then
			self.map.uci:set("AdGuardHome", section, "logfile", value .. "/runtime.log")
		end
	end
	Value.write(self, section, value)
end

-- log file
o = s:taboption("core", Value, "logfile", translate("Runtime log file path"), translate("If set to syslog, logs will be written to the system log; if left empty, no logs will be recorded"))
o.datatype    = "string"
o.rmempty = true
o.validate=function(self, value)
if fs.stat(value,"type")=="dir" then
	fs.rmdir(value)
end
if fs.stat(value,"type")=="dir" then
	if m.message then
	m.message =m.message.."\nerror!log file is a dir"
	else
	m.message ="error!log file is a dir"
	end
	return nil
end
return value
end

-- debug
o = s:taboption("core", Flag, "verbose", translate("Verbose log"))
o.default = 0
o.optional = false

-- downloadpath
o = s:taboption("core", TextValue, "downloadlinks",translate("Download links for update"))
o.optional = false
o.rows = 4
o.wrap = "soft"
o.default = [[https://static.adguard.com/adguardhome/release/AdGuardHome_linux_${Arch}.tar.gz
#https://static.adguard.com/adguardhome/beta/AdGuardHome_linux_${Arch}.tar.gz
https://github.com/AdguardTeam/AdGuardHome/releases/download/${latest_ver}/AdGuardHome_linux_${Arch}.tar.gz]]

---- Backup Settings ----
s:tab("backup", translate("Backup Settings"))

-- upgrade protect
o = s:taboption("backup", DynamicList, "upprotect", translate("Keep files when system upgrade"))
o:value("$binpath",translate("core executable"))
o:value("$configpath",translate("config file"))
o:value("$logfile",translate("log file"))
o:value("$workdir/data/filters","filters")
o:value("$workdir/data/stats.db","stats.db")
o:value("$workdir/data/querylog.json","querylog.json")
o:value("$workdir/data/sessions.db","sessions.db")
o.default = nil
o.optional = false

-- backup workdir on shutdown
local workdir=uci:get("AdGuardHome","AdGuardHome","workdir") or "/usr/bin/AdGuardHome"
o = s:taboption("backup", MultiValue, "backupfile", translate("Backup workdir files when shutdown"))
o1 = s:taboption("backup", Value, "backupwdpath", translate("Backup workdir path"))
local name
o:value("filters","filters")
o:value("stats.db","stats.db")
o:value("querylog.json","querylog.json")
o:value("sessions.db","sessions.db")
o1:depends ("backupfile", "filters")
o1:depends ("backupfile", "stats.db")
o1:depends ("backupfile", "querylog.json")
o1:depends ("backupfile", "sessions.db")
for name in fs.glob(workdir.."/data/*")
do
	name=fs.basename (name)
	if name~="filters" and name~="stats.db" and name~="querylog.json" and name~="sessions.db" then
		o:value(name,name)
		o1:depends ("backupfile", name)
	end
end
o.widget = "checkbox"
o.default = nil
o.optional=false
o.description=translate("Will be restore when workdir/data is empty")

-- backup workdir path

o1.default     = "/usr/bin/AdGuardHome"
o1.datatype    = "string"
o1.optional = false
o1.validate=function(self, value)
if fs.stat(value,"type")=="reg" then
	if m.message then
	m.message =m.message.."\nerror!backup dir is a file"
	else
	m.message ="error!backup dir is a file"
	end
	return nil
end
if string.sub(value,-1)=="/" then
	return string.sub(value, 1, -2)
else
	return value
end
end

---- Crontab Settings ----
s:tab("crontab", translate("Crontab Settings"))

o = s:taboption("crontab", MultiValue, "crontab", translate("Crontab task"),translate("Please change time and args in crontab"))
o:value("autohost",translate("Auto update ipv6 hosts and restart AdGuardHome"))
o:value("autogfwipset",translate("Auto update ipset list and restart AdGuardHome"))
o.widget = "checkbox"
o.default = nil
o.optional = false

---- GFWList Settings ----
s:tab("gfwlist", "GFW DNS 分流")

o = s:taboption("gfwlist", Flag, "gfw_enabled", "启用 GFW DNS 分流",
    "启用后默认走国内 DNS，GFW 域名走国外 DNS；.lan 也走国内上游，局域网主机名可能无法解析。")
o.default = "0"
o.rmempty = false

o = s:taboption("gfwlist", Button, "gfw_update_now", "手动更新 GFW 列表",
    "先保存本页新填写的 DNS 和下载地址，再下载并转换规则。")
o.inputtitle = "立即下载并转换"
o.inputstyle = "apply"
o:depends("gfw_enabled", "1")
o.write = function()
    manual_gfw_update = true
end

o = s:taboption("gfwlist", DynamicList, "gfw_domestic_dns", "国内 DNS 上游",
    "每行一个，可填写 IP、IP:端口或 DoH/DoT 地址；支持多个。添加后点“保存并应用”，或直接点上方“立即下载并转换”。")
o:value("223.5.5.5")
o:value("119.29.29.29")
o:depends("gfw_enabled", "1")

o = s:taboption("gfwlist", DynamicList, "gfw_foreign_dns", "GFW 域名 DNS 上游",
    "每行一个，可填写 IP、IP:端口或 DoH/DoT 地址；支持多个。GFW 模式启用时，请在这里修改上游；AdGuard Home 原生页面的上游列表会被规则文件覆盖。")
o:value("https://dns.google/dns-query")
o:value("https://cloudflare-dns.com/dns-query")
o:depends("gfw_enabled", "1")

o = s:taboption("gfwlist", Flag, "gfw_auto_update", "自动更新并转换 GFW 列表",
    "每周日 03:30 更新一次；也可以随时使用上方的手动更新按钮。下载和转换在内存中完成，仅在规则变化时写入磁盘并重启 AdGuard Home。")
o.default = "0"
o.rmempty = false
o:depends("gfw_enabled", "1")

o = s:taboption("gfwlist", DynamicList, "gfw_download_urls", "GFW 列表下载地址",
    "按从上到下的顺序尝试：第一条为首选，其余为备用；可添加、删除或调整顺序。")
o:value("https://gcore.jsdelivr.net/gh/gfwlist/gfwlist/gfwlist.txt")
o:value("https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt")
o:value("https://fastly.jsdelivr.net/gh/gfwlist/gfwlist/gfwlist.txt")
o:depends("gfw_enabled", "1")

o = s:taboption("gfwlist", Flag, "gfw_use_backup", "首选失败时尝试备用地址")
o.default = "1"
o.rmempty = false
o:depends("gfw_enabled", "1")

o = s:taboption("gfwlist", DummyValue, "gfw_download_status", "最近成功使用的下载地址")
o.cfgvalue = function()
    local workdir = uci:get("AdGuardHome", "AdGuardHome", "workdir") or "/mnt/sda1/AdGuardHome"
    return fs.readfile("/tmp/adguardhome-gfw-download-status") or fs.readfile(workdir .. "/gfw-download-status.txt") or "本次启动后尚未更新"
end
o:depends("gfw_enabled", "1")

function m.on_after_save()
    -- A plain LuCI Save calls on_after_save but does not call on_after_commit.
    -- Commit the new upstream list before regenerating its on-disk rule file.
    m.uci:commit("AdGuardHome")
    local mode = manual_gfw_update and "update" or "sync"
    luci.sys.call("/usr/share/AdGuardHome/update-gfw-upstreams.sh " .. mode .. " >/tmp/adguardhome-gfw-update.log 2>&1")
end

return m

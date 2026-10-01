if not api.is_finded("ipt2socks") then
	return
end

-- [[ Socks ]]
local m, s1 = ...
local type_name = "Socks"

s1.fields["type"]:value(type_name, "Socks")

if s1.val["type"] and s1.val["type"] ~= type_name then
	return
end

local s = NamedSection(m, arg[1], "tmp_" .. s1.sectiontype)
s.parent = s1
s.type_name = type_name
s.option_prefix = "socks_"
api.set_type_cbi(s)

o = s:option(ListValue, "del_protocol", "��") --ʼ�����أ�����ɾ�� protocol
o:depends({ __hide = "1" })
o.rewrite_option = "protocol"

o = s:option(Value, "address", translate("Address (Support Domain Name)"))

o = s:option(Value, "port", translate("Port"))
o.datatype = "port"

o = s:option(Value, "username", translate("Username"))

o = s:option(Value, "password", translate("Password"))
o.password = true

o = s:option(Flag, "native_socks", "轻量透明转发", "使用 ipt2socks 转发到本机 SOCKS 服务，减少内存占用。作为全局节点使用时，需在 DNS 设置中选择 SmartDNS 和 Socks 模式。")
o.rewrite_option = "native_socks"
o.default = "0"
o.rmempty = false
o:depends({ address = "127.0.0.1" })

api.type_cbi_section(s1, s)

#!/bin/sh
# Keep AdGuard Home's per-domain upstreams in sync with the GFW list.
set -eu
set -f

section=AdGuardHome.AdGuardHome
workdir="$(uci -q get "$section.workdir" || echo /mnt/sda1/AdGuardHome)"
config="$(uci -q get "$section.configpath" || echo "$workdir/adguardhome.yaml")"
rules="$workdir/upstreams-gfw.txt"
remote_domains="$workdir/gfwlist-remote-domains.txt"
source_domains=/usr/share/passwall/rules/gfwlist
cron_file=/etc/crontabs/root
cron_command=/usr/share/AdGuardHome/update-gfw-upstreams.sh
cron_entry="30 3 * * 0 $cron_command update"
enabled="$(uci -q get "$section.gfw_enabled" || echo 0)"
auto_update="$(uci -q get "$section.gfw_auto_update" || echo 0)"
domestic="$(uci -q get "$section.gfw_domestic_dns" || echo 223.5.5.5)"
foreign="$(uci -q get "$section.gfw_foreign_dns" || echo https://dns.google/dns-query)"
download_urls="$(uci -q get "$section.gfw_download_urls" || printf '%s\n' 'https://gcore.jsdelivr.net/gh/gfwlist/gfwlist/gfwlist.txt https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt https://fastly.jsdelivr.net/gh/gfwlist/gfwlist/gfwlist.txt')"
use_backup="$(uci -q get "$section.gfw_use_backup" || echo 1)"
source_status=/tmp/adguardhome-gfw-download-status
mode="${1:-sync}"

mkdir -p "$workdir" "${cron_file%/*}"
if [ ! -e "$cron_file" ]; then
    : > "$cron_file"
    chmod 600 "$cron_file"
fi

# Update the cron entry even when DNS list generation later fails.
if [ "$enabled" = 1 ] && [ "$auto_update" = 1 ]; then
    if ! grep -Fq "$cron_entry" "$cron_file"; then
        sed -i "\|$cron_command|d" "$cron_file"
        printf '%s\n' "$cron_entry" >> "$cron_file"
        /etc/init.d/cron restart
    fi
elif grep -Fq "$cron_command" "$cron_file"; then
    sed -i "\|$cron_command|d" "$cron_file"
    /etc/init.d/cron restart
fi

if [ "$enabled" != 1 ]; then
    if grep '^  upstream_dns_file:' "$config" | grep -Fq "$rules"; then
        sed -i 's#^  upstream_dns_file:.*#  upstream_dns_file: ""#' "$config"
        /etc/init.d/AdGuardHome restart
    fi
    exit 0
fi

validate_dns() {
    [ -n "$1" ] || return 1
    for dns in $1; do
        case "$dns" in
            *"'"*|*'"'*|*'#'*|*'['*|*']'*|*'\\'*|*'?'*|*'&'*|*'='*) return 1 ;;
        esac
        printf '%s\n' "$dns" | grep -Eq '^(https://[A-Za-z0-9._:-]+/[A-Za-z0-9/_-]+|tls://[A-Za-z0-9._:-]+|tcp://[A-Za-z0-9._:-]+|[0-9.]+(:[0-9]+)?)$' || return 1
    done
}
validate_dns "$domestic" && validate_dns "$foreign" || { echo 'Invalid DNS upstream' >&2; exit 1; }

scratch="$(mktemp -d /tmp/agh-gfw.XXXXXX)"
trap 'rm -rf "$scratch"' EXIT

if [ "$mode" = update ]; then
    encoded="$scratch/download"
    decoded="$scratch/decoded"
    parsed="$scratch/parsed"
    source_number=0
    downloaded=0
    for url in $download_urls; do
        source_number=$((source_number + 1))
        [ "$source_number" -eq 1 ] || [ "$use_backup" = 1 ] || break
        case "$url" in https://*) ;; *) echo "Skipping non-HTTPS GFW source: $url" >&2; continue ;; esac
        if ! curl -fsSL --max-time 15 -o "$encoded" -- "$url" \
            || ! base64 -d "$encoded" > "$decoded" 2>/dev/null; then
            echo "GFW source unavailable: $url" >&2
            continue
        fi
        awk '
            /^@@/ { next }
            /^\|\|[A-Za-z0-9.-]+\^?/ {
                domain=$0
                sub(/^\|\|/, "", domain)
                sub(/[^A-Za-z0-9.-].*$/, "", domain)
                if (domain ~ /^[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]$/ && domain ~ /\./) print domain
            }
        ' "$decoded" | sort -u > "$parsed"
        if [ "$(wc -l < "$parsed")" -le 100 ]; then
            echo "GFW source contained too few domains: $url" >&2
            continue
        fi
        if ! cmp -s "$parsed" "$remote_domains"; then
            cp "$parsed" "$remote_domains.new"
            chmod 644 "$remote_domains.new"
            mv "$remote_domains.new" "$remote_domains"
        fi
        printf '%s | %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$url" > "$source_status"
        downloaded=1
        break
    done
    [ "$downloaded" = 1 ] || echo 'All selected GFW sources failed; using cached/local domains' >&2
fi

temporary="$scratch/upstreams"
{
    for dns in $domestic; do printf '%s\n' "$dns"; done
    printf '[/cn/]%s\n' "$domestic"
    printf '[/lan/]%s\n' "$domestic"
    cat "$source_domains" "$remote_domains" 2>/dev/null | \
        awk '/^[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]$/ && /\./ { print tolower($0) }' | \
        sort -u | awk -v upstream="$foreign" '{print "[/" $0 "/]" upstream}'
} > "$temporary"

if [ "$(wc -l < "$temporary")" -lt 100 ]; then
    echo 'GFW source list is missing or empty' >&2
    exit 1
fi

changed=0
if ! cmp -s "$temporary" "$rules"; then
    cp "$temporary" "$rules.new"
    chmod 644 "$rules.new"
    mv "$rules.new" "$rules"
    changed=1
fi

if ! grep '^  upstream_dns_file:' "$config" | grep -Fq "$rules"; then
    cp -p "$config" "$config.before-gfw-switch"
    sed -i "s#^  upstream_dns_file:.*#  upstream_dns_file: \"$rules\"#" "$config"
    changed=1
fi

# Remove the old local .lan override from AdGuard Home's YAML: it would
# otherwise take precedence over the generated upstream file.
if grep -Fq '[/lan/]127.0.0.1:1745' "$config"; then
    cp -p "$config" "$config.before-gfw-switch"
    sed -i '\#\[/lan/\]127\.0\.0\.1:1745#d' "$config"
    changed=1
fi

if [ "$changed" = 1 ]; then
    if ! /usr/bin/AdGuardHome -c "$config" --check-config >/dev/null 2>&1; then
        [ -f "$config.before-gfw-switch" ] && cp -p "$config.before-gfw-switch" "$config"
        echo 'AdGuard Home configuration validation failed' >&2
        exit 1
    fi
    /etc/init.d/AdGuardHome restart
fi

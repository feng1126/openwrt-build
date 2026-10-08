# AN7581 bridge offload port

This bundle targets the pinned OpenWrt 6.18 base used by the XG-040G-MD PON
build. It imports bridge flowtable support and correctness fixes from
OpenWRT-fanboy/OpenW1700k, commit
`8b3dbccb8cd4eb8f2830c292f9ed22367aeaadc1` (ubi2 branch).
The W1700K published builds already carry the corresponding changes:
https://github.com/w1700k/builds/releases

Included upstream work:

- Two flowtable backports: forward-path context and stale-route teardown.
- A separate bridge-family flowtable, native bridge conntrack with VLAN/PPPoE
  parsing, and firewall4 generation respecting existing offload toggles.
- Egress single-VLAN restoration in the software fast path.
- Conntrack protection for connections crossing a bridge more than once.
- Native L2B TTL preservation and cross-ingress L2-key collision protection.
- Network hotplug refresh for bridge membership changes.

Local adaptations:

- The bridge path patch retains OpenWrt's existing out.ifindex fallback and
  follows pending patch 699; this series is numbered 702 rather than 675.
- The L2 collision patch retains the PON flow's gc_node and egress_dev fields.
- Patch 962 explicitly carries bridge metadata to the Airoha classifier.
  IP-keyed bridge rules need TTL preservation too; checking only the native
  BRIDGE packet type misses these flows. Software bridge flows also preserve
  TTL/hop limit, DSCP, and addresses; bridge hardware actions omit NAT.
- Double-tag and PPPoE bridge paths fall back to ordinary forwarding. The
  imported software fast path only restores a single VLAN tag. This limit
  applies to transparent bridging, not the existing routed PPPoE WAN.

The existing PON patch 930 remains responsible for native AN7581 L2B entry
layout. These patches do not make arbitrary Ethernet protocols eligible:
the generated flowtable rules select TCP and UDP IP traffic.

Patch 962 extends an internal kernel structure. All kernel modules must be
built against this kernel; do not mix modules from a different build.

## Validation performed

- Zero-fuzz application against the existing patched Linux 6.18.55 sources.
- Compilation of 13 affected kernel objects, including the Airoha PPE/NPU,
  bridge conntrack, flowtable paths, core networking and the MediaTek caller.
- Full Cone and bridge firewall4 patches apply together to the pinned fw4.
- ucode module and template compilation on the router.
- Read-only ruleset rendering against the router's actual configuration:
  bridge fw4 fb contains lan1 through lan4 with flags offload. Active rules
  were not replaced.

Full firmware CI and hardware forwarding validation are separate checks.
After booting the new image, verify:

1. `nft list flowtable bridge fw4 fb` lists the intended physical bridge ports.
2. LAN-to-LAN TCP and UDP work in both directions with IPv4 and IPv6.
3. Endpoint captures show unchanged IPv4 TTL / IPv6 hop limit and correct MACs.
4. Tagged and untagged VLAN paths preserve isolation and do not double-tag.
5. A flow routed through another router on the same bridge remains correct.
6. Disabling flow offload and reloading firewall removes the bridge flowtable.
7. PON PPPoE WAN and ordinary routed/NAT traffic still work.

PPE BND entries alone do not prove throughput, packet correctness or working
hardware counters; use endpoint captures and bidirectional traffic tests.

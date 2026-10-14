#!/usr/bin/env python3
"""Run the actual PON apply function with simulated hardware and link state."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]
src=root/'local_packages/pon/airoha-xpon/src'
h=(src/'airoha-xpon-private.h').read_text()
structs=h[h.index('struct airoha_xpon_data_path_entry {'):h.index('struct airoha_xpon {')]
s=(src/'airoha-xpon-ploam.c').read_text()
code=s[s.index('static bool\nairoha_xpon_data_path_has_gem'):s.index('\nint airoha_xpon_replace_data_paths(')]
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
typedef unsigned short u16;
typedef unsigned char u8;
#define AIROHA_XPON_MAX_DATA_PATHS 32
#define AIROHA_XGPON_O5 5
#define WRITE_ONCE(x,y) ((x)=(y))
#define lockdep_assert_held(x) ((void)0)
#define mutex_lock(x) ((void)0)
#define mutex_unlock(x) ((void)0)
#define dev_info(...) ((void)0)
struct net_device { bool carrier; };
struct airoha_pon_flow_config { u8 tcont; u16 gem_id, vlan_id; u8 pbit_mask; };
'''
mock=r'''
struct airoha_xpon {
 int state_lock, ploam_lock; bool mac_initialized;
 int onu_state; u16 onu_id;
 struct airoha_xpon_data_path_state data_path;
 struct net_device *pon_netdev;
};
static int lookups, writes, replacements, link_changes, lookup_error, gem_error;
static u8 assigned=1;
static bool netif_carrier_ok(struct net_device *n) { return n->carrier; }
static int airoha_xpon_find_tcont(struct airoha_xpon *x,u16 id,u8 *idx,void *unused) {
 ++lookups; *idx=assigned; return lookup_error;
}
static int airoha_xpon_find_or_create_tcont(struct airoha_xpon *x,u16 id,u8 *idx) {
 return airoha_xpon_find_tcont(x,id,idx,0);
}
static int airoha_xpon_set_gem(struct airoha_xpon *x,u16 id,bool valid,bool uni) {
 ++writes; return gem_error;
}
static void airoha_xpon_set_data_path_link(struct airoha_xpon *x,bool ready) {
 ++link_changes; x->pon_netdev->carrier=ready;
}
static int airoha_eth_pon_replace_flows(struct net_device *n,struct airoha_pon_flow_config *f,unsigned int count) {
 ++replacements; return 0;
}
'''
main=r'''
int main(void) {
 struct net_device n={0};
 struct airoha_xpon x={.mac_initialized=true,.onu_state=5,.onu_id=10,.pon_netdev=&n};
 struct airoha_xpon_data_path_entry a={.alloc_id=11,.gem_id=100,.vlan_id=41,.pbit_mask=255};
 assert(!airoha_xpon_apply_data_paths_locked(&x,&a,1));
 assert(writes==1 && replacements==1 && link_changes==2);
 assert(!airoha_xpon_apply_data_paths_locked(&x,&a,1));
 assert(lookups==2 && writes==1 && replacements==1 && link_changes==2);
 assigned=2;
 assert(!airoha_xpon_apply_data_paths_locked(&x,&a,1)); assert(writes==2);
 lookup_error=-ENOENT;
 assert(airoha_xpon_apply_data_paths_locked(&x,&a,1)==-EAGAIN);
 assert(x.data_path.pending_count==1 && writes==2);
 lookup_error=0; n.carrier=false;
 assert(!airoha_xpon_apply_data_paths_locked(&x,&a,1)); assert(writes==3);
 x.data_path.configured=false;
 assert(!airoha_xpon_apply_data_paths_locked(&x,&a,1)); assert(writes==4);
 a.vlan_id=42; gem_error=-EIO;
 assert(airoha_xpon_apply_data_paths_locked(&x,&a,1)==-EIO); assert(!n.carrier);
 a.vlan_id=41; gem_error=0;
 assert(!airoha_xpon_apply_data_paths_locked(&x,&a,1)); assert(writes==6);
 x.onu_state=1;
 assert(airoha_xpon_apply_data_paths_locked(&x,&a,1)==-ENOLINK);
 x.onu_state=5; a.multicast=true; a.alloc_id=65535;
 assert(!airoha_xpon_apply_data_paths_locked(&x,&a,1)); assert(writes==7);
 assert(!airoha_xpon_apply_data_paths_locked(&x,&a,1)); assert(writes==7);
 struct airoha_xpon_data_path_entry b=a;
 b.gem_id++; assert(!airoha_xpon_same_data_paths(&x.data_path,&b,1)); b=a;
 b.pbit_mask=1; assert(!airoha_xpon_same_data_paths(&x.data_path,&b,1)); b=a;
 b.alloc_id--; assert(!airoha_xpon_same_data_paths(&x.data_path,&b,1));
 assert(!airoha_xpon_same_data_paths(&x.data_path,&a,2));
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='pon-path-test-') as tmp:
 p=Path(tmp)/'test.c'; exe=Path(tmp)/'test';p.write_text(pre+structs+mock+code+main)
 subprocess.run(['gcc','-std=gnu11','-Wall','-Werror',str(p),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PASS: actual apply path, duplicates, reassignment, deferral, recovery, failures and multicast')

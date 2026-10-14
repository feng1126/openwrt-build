#!/usr/bin/env python3
"""Exercise the actual patched commit path with host-side RCU/PPE mocks."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
patch = root / 'patches/pon/overlay/target/linux/airoha/patches-6.18/925-net-airoha-add-PON-PPE-offload-metadata.patch'
added = '\n'.join(line[1:] for line in patch.read_text().splitlines()
                  if line.startswith('+') and not line.startswith('+++'))
start = added.index('/* Compare fields')
end = added.index('\n}\n', added.index('airoha_eth_pon_commit_config')) + 3
code = added[start:end]
preamble = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned int u32;
struct entry { u32 tag; unsigned short vlan_id; unsigned char pbit_mask; };
struct airoha_pon_flow_table { unsigned int count; struct entry entries[2]; };
struct airoha_gdm_dev { struct airoha_pon_flow_table *pon_flow_table; u32 pon_qdma_tag; };
static int flow_offload_mutex, locked, evictions, syncs;
#define mutex_lock(x) do { assert(!locked); locked = 1; } while (0)
#define mutex_unlock(x) do { assert(locked); locked = 0; } while (0)
#define lockdep_is_held(x) (locked)
#define rcu_dereference_protected(x, cond) (assert(cond), (x))
#define rcu_replace_pointer(x, y, cond) ({ assert(cond); __typeof__(x) prev=(x); (x)=(y); prev; })
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x, y) ((x)=(y))
#define kfree(x) free(x)
#define synchronize_net() (++syncs)
#define airoha_ppe_remove_egress_flows(x) do { assert(locked); ++evictions; } while (0)
static struct airoha_pon_flow_table *table(unsigned int n, unsigned char fill) {
 struct airoha_pon_flow_table *t = malloc(sizeof(*t));
 memset(t, fill, sizeof(*t)); t->count=n;
 for (unsigned int i=0; i<n; i++) {
  t->entries[i].tag=100+i; t->entries[i].vlan_id=41+i; t->entries[i].pbit_mask=255;
 }
 return t;
}
'''
main = r'''
int main(void) {
 struct airoha_gdm_dev d={0};
 airoha_eth_pon_commit_config(&d, NULL, 0); assert(!evictions && !syncs);
 airoha_eth_pon_commit_config(&d, table(2, 0), 0); assert(evictions==1);
 void *saved=d.pon_flow_table;
 airoha_eth_pon_commit_config(&d, table(2, 255), 0);
 assert(d.pon_flow_table==saved && evictions==1 && syncs==1);
 struct airoha_pon_flow_table *t=table(2,0); t->entries[0].tag++;
 airoha_eth_pon_commit_config(&d,t,0); assert(evictions==2);
 t=table(2,0); t->entries[0].vlan_id++;
 airoha_eth_pon_commit_config(&d,t,0); assert(evictions==3);
 t=table(2,0); t->entries[0].pbit_mask=1;
 airoha_eth_pon_commit_config(&d,t,0); assert(evictions==4);
 airoha_eth_pon_commit_config(&d,table(1,0),0); assert(evictions==5);
 airoha_eth_pon_commit_config(&d,NULL,123); assert(evictions==6);
 airoha_eth_pon_commit_config(&d,NULL,123); assert(evictions==6);
 airoha_eth_pon_commit_config(&d,NULL,124); assert(evictions==7);
 airoha_eth_pon_commit_config(&d,NULL,0); assert(evictions==8);
 airoha_eth_pon_commit_config(&d,table(1,0),0); assert(evictions==9);
 assert(syncs==evictions && !locked);
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='pon-dedup-') as tmp:
 src=Path(tmp)/'test.c'; exe=Path(tmp)/'test'
 src.write_text(preamble+code+main)
 subprocess.run(['gcc','-std=gnu11','-Wall','-Werror','-Wno-unused-variable',str(src),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PASS: duplicate mappings, padding, field/count/tag changes, teardown and restoration')

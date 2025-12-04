# Run this ONCE to index all Maxar NTF files.
import os
import json

imagery_root = "/ceoas/Vandenhoek_Lab/Uganda"
index_path = "/home/ceoas/mondschz/uganda/data/footprints/ntf_index.json"

ntf_map = {}

"""

Builds a persistent index that can be looked up in less than 100 ms 
instead of walking the entire filesystem in each iteration.

Example key-value pair (filename -> filepath mapping):

    {
        "21DEC23083136-M2AS-507744547070_01_P004.NTF":
            /ceoas/Vandenhoek_Lab/Uganda/ID177_AOI3/WV320211223083136M00/
            21DEC23083136-M2AS-507744547070_01_P004/
            21DEC23083136-M2AS-507744547070_01_P004.NTF"
    }
    
 """
# 
for root, dirs, files in os.walk(imagery_root):
    for f in files:
        if f.lower().endswith(".ntf"):
            ntf_map[f] = os.path.join(root, f)

with open(index_path, "w") as f:
    json.dump(ntf_map, f, indent=2) 

print("Indexed", len(ntf_map), "NTF scenes.")

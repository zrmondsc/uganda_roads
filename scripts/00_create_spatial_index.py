# Run this ONCE to index all Maxar NTF files.
import os
import json

imagery_root = "/ceoas/Vandenhoek_Lab/Uganda"
index_path = "/home/ceoas/mondschz/uganda/data/footprints/ntf_index.json"

ntf_map = {}

for root, dirs, files in os.walk(imagery_root):
    for f in files:
        if f.lower().endswith(".ntf"):
            ntf_map[f] = os.path.join(root, f)

with open(index_path, "w") as f:
    json.dump(ntf_map, f, indent=2)

print("Indexed", len(ntf_map), "NTF scenes.")

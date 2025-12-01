"""
Adapted from a Maxar clipping workflow developed by Zhanpei (Z. Fang)

Clip Maxar imagery to sampled 1km grid cells in Nakivale.

Maxar source imagery is located in:
/ceoas/Vandenhoek_Lab/Uganda

This script:
1. Loops through 1km gridcells
2. Finds intersecting Maxar footprints
3. Locates matching .NTF scenes
4. Clips the raster to the gridcell
5. Saves each chip as GeoTIFF

Enhancements:
- Uses fast ntf_index.json (no os.walk)
- Copies IMD/XML/RPB/TIL metadata for every chip
- Works with JP2-enabled GDAL (NO NITF_OPEN_UNDERLYING_DS hack)
- Writes success messages when clipping is successful
"""

import os
import json
import shutil
import geopandas as gpd
import subprocess


# --------------------------------------------------------------------
# PATHS
# --------------------------------------------------------------------
project_root = "/home/ceoas/mondschz/uganda"

grid_path = os.path.join(
    project_root,
    "data/boundaries/gridcells_random_sample_300_nakivale_1000m_wgs1984.geojson"
)

footprints_path = os.path.join(
    project_root,
    "data/footprints/maxar_footprints_with_sensor.geojson"
)

ntf_index_path = os.path.join(
    project_root,
    "data/footprints/ntf_index.json"
)

out_path = os.path.join(
    project_root,
    "data/outputs/imagery/nakivale_sample"
)
os.makedirs(out_path, exist_ok=True)

# --------------------------------------------------------------------
# LOAD DATA
# --------------------------------------------------------------------
print("Loading grid cells…")
grid_cells = gpd.read_file(grid_path)

print("Loading Maxar footprints…")
maxar_footprints = gpd.read_file(footprints_path)

# Align CRS
grid_cells = grid_cells.to_crs(maxar_footprints.crs)

# Spatial index
sindex = maxar_footprints.sindex

# NTF index
with open(ntf_index_path, "r") as f:
    ntf_index = json.load(f)


# --------------------------------------------------------------------
# FUNCTION: COPY METADATA FILES
# --------------------------------------------------------------------
def copy_metadata(image_path, out_dir):
    """
    Copy IMD, XML, RPB, TIL from the source directory to the chip output folder.
    """
    src_dir = os.path.dirname(image_path)
    exts = [".IMD", ".XML", ".RPB", ".TIL"]

    for f in os.listdir(src_dir):
        for ext in exts:
            if f.upper().endswith(ext):
                src = os.path.join(src_dir, f)
                dst = os.path.join(out_dir, f)
                shutil.copy(src, dst)
                print(f"   ✓ Copied metadata → {f}")
                break


# --------------------------------------------------------------------
# MAIN LOOP
# --------------------------------------------------------------------
for idx, grid_cell in grid_cells.iterrows():

    cell_id = int(grid_cell["OID"])
    print(f"\n=== Processing grid_cell {cell_id} ({idx+1}/{len(grid_cells)}) ===")

    cell_dir = os.path.join(out_path, str(cell_id))
    os.makedirs(cell_dir, exist_ok=True)

    # footprints whose bbox intersects gridcell
    possible_ix = sindex.query(grid_cell.geometry)
    fp_subset = maxar_footprints.iloc[possible_ix]

    for j, fp in fp_subset.iterrows():

        filename = fp["filename"]
        tif_name = f"{cell_id}_{filename[:-4]}.tif"
        tif_path = os.path.join(cell_dir, tif_name)

        # Must still test exact intersection
        if not grid_cell.geometry.intersects(fp.geometry):
            continue

        print(f"Match found with: {filename}")

        # Get image path
        image_path = ntf_index.get(filename)
        if image_path is None:
            print(f"   Missing in NTF index: {filename}")
            continue

        print(f"Found image: {image_path}")

        # ALWAYS COPY METADATA, even if chip exists
        copy_metadata(image_path, cell_dir)

        # If chip exists do not redo clipping
        if os.path.exists(tif_path):
            print(f"   → Chip already exists, metadata updated.")
            continue

        # ---------------------------------------------------------
        # CLIP WITH VRT + GDALWARP (reads REAL JP2 image now)
        # ---------------------------------------------------------
        try:
            cut_gdf = gpd.GeoDataFrame(
                geometry=[grid_cell.geometry],
                crs=grid_cells.crs
            ).to_crs("EPSG:4326")

            cutline_path = os.path.join(cell_dir, "cutline.geojson")
            cut_gdf.to_file(cutline_path, driver="GeoJSON")

            vrt_path = os.path.join(cell_dir, f"{cell_id}_{filename[:-4]}.vrt")

            # build vrt
            subprocess.run(
                ["gdalbuildvrt", vrt_path, image_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # run warp
            result = subprocess.run(
                [
                    "gdalwarp",
                    "-cutline", cutline_path,
                    "-crop_to_cutline",
                    "-of", "GTiff",
                    vrt_path,
                    tif_path
                ],
                capture_output=True,
                text=True
            )

            if result.returncode != 0 or not os.path.exists(tif_path):
                print("   → gdalwarp produced no output (possibly outside footprint). Skipping.")
                continue

            print(f"   ✓ Saved chip → {tif_path}")

        except Exception as e:
            print(f"ERROR clipping {filename}: {e}")
            continue

print("\n=== ALL DONE ===")

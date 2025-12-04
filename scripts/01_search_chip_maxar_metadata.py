"""
Adapted from a Maxar clipping workflow developed by Zhanpei (Z. Fang), and 
uses her maxar_footprints_with_sensor.geojson file.

===============================================================================

Clip Maxar imagery to sampled 1km grid cells in Nakivale.

Maxar source imagery is located in: /ceoas/Vandenhoek_Lab/Uganda

This script:
1. Loops through 1km gridcells
2. Finds intersecting Maxar footprints
3. Locates matching .NITF scenes
4. Clips the raster to the gridcell
5. Saves each chip as GeoTIFF

Enhancements:
- Uses fast ntf_index.json <- big performance improvement w/o multithreading
- Copies IMD/XML/RPB/TIL metadata for every chip

===================================================================================

NOTE: there is still plenty to optimize here for the future. BUT this is good enough for now!
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
) # substitute with path/to/your/aoi.geojson

footprints_path = os.path.join(
    project_root,
    "data/footprints/maxar_footprints_with_sensor.geojson"
) # maxar scene footprints, thanks zhanpei!

ntf_index_path = os.path.join(
    project_root,
    "data/footprints/ntf_index.json"
) # generate this file using the 00_create_spatial_index.py script

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

# align the crs of the gridcells to the crs of the maxar footprints
grid_cells = grid_cells.to_crs(maxar_footprints.crs)

# build spatial index over geometry column in geodataframe
sindex = maxar_footprints.sindex

# NTF index
with open(ntf_index_path, "r") as f:
    ntf_index = json.load(f)


# --------------------------------------------------------------------
# FUNCTION DEFINITION: COPY METADATA FILES
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
                print(f"   :) Copied metadata --> {f}")
                break # time saving, exits inner loop


# --------------------------------------------------------------------
# MAIN LOOP
# --------------------------------------------------------------------
for idx, grid_cell in grid_cells.iterrows():

    cell_id = int(grid_cell["OID"]) # change to reflect your UID column
    print(f"\n~~~~ Processing grid_cell {cell_id} ({idx+1}/{len(grid_cells)}) ~~~")

    # create grid cell level output directory
    cell_dir = os.path.join(out_path, str(cell_id))
    os.makedirs(cell_dir, exist_ok=True)

    # footprints whose bounding box intersects gridcell
    possible_ix = sindex.query(grid_cell.geometry) # <- bounding box based intersection additional performance improvement
    fp_subset = maxar_footprints.iloc[possible_ix] # later we'll do a more computationally expensive but more thorough intersection

    for j, fp in fp_subset.iterrows():

        # build eventual output_fp
        filename = fp["filename"]
        tif_name = f"{cell_id}_{filename[:-4]}.tif"
        tif_path = os.path.join(cell_dir, tif_name)

        # test exact intersection on subset of footprints (previously did bbox intersection on entire footprint dataset)
        if not grid_cell.geometry.intersects(fp.geometry):
            continue

        print(f"Match found with: {filename}")

        # get image path
        image_path = ntf_index.get(filename)
        if image_path is None:
            print(f"   Missing in NTF index: {filename}")
            continue

        print(f"Found image: {image_path}")

        # ALWAYS COPY METADATA, even if chip exists
        copy_metadata(image_path, cell_dir)

        # If chip exists do not redo clipping
        if os.path.exists(tif_path):
            print(f"   --> Chip already exists, metadata updated.")
            continue

        # ---------------------------------------------------------
        # CLIP WITH VRT + GDALWARP (reads REAL JP2 image now)
        # ---------------------------------------------------------
        # ---------------------------------------------------------
        # DIRECT GDALWARP CLIP (no VRT)
        # ---------------------------------------------------------
        try:
            # build a single-feature geodataframe that contains one grid cell, reprojected to GCS
            cut_gdf = gpd.GeoDataFrame(
                geometry=[grid_cell.geometry],
                crs=grid_cells.crs
            ).to_crs("EPSG:4326") # reproject to GCS, i think GDALWARP will automatically reproject into the target CRS anyway

            # builds a cutline file for GDALWARP from our single feature gdf
            cutline_path = os.path.join(cell_dir, "cutline.geojson")
            cut_gdf.to_file(cutline_path, driver="GeoJSON")

            # run warp directly on the JP2/NTF image (previous was using VRT just because, may be better with future workflows)
            # clips the JP2 image stored in the NTF and writes the output raster as a GeoTIFF
            # gdalwarp -cutline <cutline_path> -crop_to_cutline -of GTiff <image_path> <tif_path>
            result = subprocess.run(
                [
                    "gdalwarp",
                    "-cutline", cutline_path,
                    "-crop_to_cutline",
                    "-of", "GTiff",
                    image_path,
                    tif_path
                ],
                capture_output=True,
                text=True
            )

            # check if output is valid
            if result.returncode != 0 or not os.path.exists(tif_path):
                print("   --> gdalwarp produced no output (possibly outside footprint). Skipping.") # .returncode = 0 is GDALs way of indicating a successful operation
                continue

            print(f"   :) SAVED CHIP --> {tif_path}") # SUCCESS if the returncode is 0

        except Exception as e:
            print(f"ERROR clipping {filename}: {e}")
            continue


print("\n=== DONEZO ===")

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
"""

import os
import geopandas as gpd
import rasterio
from rasterio.mask import mask


# -------------------------------------------------------------------------
# BUILD FILE PATHS
# -------------------------------------------------------------------------

# path to project root
project_root = "/home/ceoas/mondschz/uganda"

# path to 1km x 1km grid cells
grid_path = os.path.join(
    project_root,
    "data/boundaries/gridcells_random_sample_300_nakivale_1000m_wgs1984.geojson"
)

# path to maxar footprints
footprints_path = os.path.join(
    project_root,
    "data/footprints/maxar_footprints_with_sensor.geojson"
)

# Output directory
out_path = os.path.join(project_root, "data/outputs/imagery/nakivale_sample")
os.makedirs(out_path, exist_ok=True)

# path to root directory of maxar archive
imagery_path = "/ceoas/Vandenhoek_Lab/Uganda"

# -------------------------------------------------------------------------
# LOAD DATA
# -------------------------------------------------------------------------

# load grid cell dataset
print("Loading grid cells…")
grid_cells = gpd.read_file(grid_path)

# load maxar footprint dataset
print("Loading Maxar footprints…")
maxar_footprints = gpd.read_file(footprints_path)

# make sure crs's align
grid_cells = grid_cells.to_crs(maxar_footprints.crs)

# -------------------------------------------------------------------------
# MAIN PROCESSING LOOP
# -------------------------------------------------------------------------

for i, grid_cell in grid_cells.iterrows():

    cell_id = int(grid_cell["OID"])
    print(f"\n=== Processing grid_cell {cell_id} ({i+1}/{len(grid_cell)}) ===")

    # create output subfolder for this cell
    cell_dir = os.path.join(out_path, str(cell_id))
    os.makedirs(cell_dir, exist_ok=True)

    for j, maxar_fp in maxar_footprints.iterrows():

        filename = maxar_fp["filename"]  # e.g. "23APR0408....P010.NTF"
        tif_name = f"{cell_id}_{filename[:-4]}.tif"
        tif_path = os.path.join(cell_dir, tif_name)

        # skip if exists
        if os.path.exists(tif_path):
            print(f"→ Already exists: {tif_name}")
            continue

        # check intersection
        if not grid_cell.geometry.intersects(maxar_fp.geometry):
            continue

        print(f"Match found with: {filename}")

        # -----------------------------------------------------------------
        # Locate NTF file using simple os.walk
        # -----------------------------------------------------------------

        image_path = None
        for root, dirs, files in os.walk(imagery_path):
            if filename in files:
                image_path = os.path.join(root, filename)
                break

        if image_path is None:
            print(f"Could not find {filename} under {imagery_path}")
            continue

        print(f"Found image: {image_path}")

        # -----------------------------------------------------------------
        # Clip raster
        # -----------------------------------------------------------------
        try:
            with rasterio.open(image_path) as src:

                # Reproject block to raster CRS
                cell_proj = (
                    gpd.GeoDataFrame(geometry=[grid_cell.geometry], crs=grid_cells.crs)
                    .to_crs(src.crs)
                )

                out_image, out_transform = mask(
                    src,
                    cell_proj.geometry,
                    crop=True
                )

                out_meta = src.meta.copy()
                out_meta.update({
                    "driver": "GTiff",
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform
                })

                # Write clipped image
                with rasterio.open(tif_path, "w", **out_meta) as dst:
                    dst.write(out_image)

                print(f"   Saved chip → {tif_path}")

        except Exception as e:
            print(f"   ERROR clipping {filename}: {e}")
            continue

print("\n=== ALL DONE ===")

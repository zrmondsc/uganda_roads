# **uganda_roads**
### *Automated road and footpath extraction in Ugandan refugee settlements using VHR multispectral imagery and lightweight CNNs.*

This repository contains the data processing pipeline and preprocessing scripts for a deep-learning workflow designed to extract road and footpath networks from **very high-resolution (0.5 m) Maxar imagery** in **Nakivale Refugee Settlement**, southwestern Uganda. 

My research questions are threefold: 
1. Can a lightweight CNN architecture, originally developed and benchmarked on urban road systems, be adapted to humanitarian settings where infrastructure is informal and sometimes ephemeral? 
2. Can we train a model using annotations for roads and footpaths that are adapted from OpenStreetMap data, despite incomplete and uneven coverage in the training dataset?
3.  Does adding small amounts of high-quality annotations significantly improve model accuracy?

Although model training has not yet begun, this repository includes:

- An **HPC-compatible preprocessing pipeline**
- Automated **Maxar scene indexing**, clipping, cutline generation, and tiling
- Integration with **OpenStreetMap (OSM)** road data via `osmnx`
- A GitHub compatible repository structure designed for future modeling tasks

---

## **Project Motivation**

Refugee settlements are among the fastest-growing and least-mapped landscapes in the world. In Uganda, more than **1.4 million refugees** live in refugee settlements, yet maps of infrastructure are often incomplete or outdated in OpenStreetMap and global datasets.

Accurate maps of roads and footpaths are important for:
- Modeling mobility and accessibility 
- Understanding settlement morphology  
- Identifying other data inequities

The performance of deep learning road extraction in **rural humanitarian contexts** is still largely unexplored. Settlements like Nakivale contain unpaved, highly diverse, and sometimes ambiguous infrastructure networks. This project investigates whether modern CNNs can address these challenges.

---

## **Repo Structure**

uganda/
│
├── configs/
│ └── paths.yaml # YAML file to build paths to important datasets
│
├── data/
│ ├── external/ # external datasets
│ ├── interim/ # intermediate datasets
│ ├── processed/ # cleaned datasets
│ ├── imagery/ # VHR imagery downloaded from the HPC
│
├── docs/ # files for writing, presenting, communicating progress
│
├── libs/
│ └── init.py # Local Python package, currently empty
│
├── notebooks/ # Jupyter notebooks for EDA
│ ├── 00_exploratory_osm.ipynb # Learning osmnx library
│ ├── 00b_exploratory_hexbins.ipynb # Building hexagonal mesh for zonal statistics
│ ├── 00c_exploratory_grids.ipynb # Building rectangular mesh for zonal statistics
│ ├── 00d_exploratory_region_hexbins.ipynb # Building hexagonal mesh for zonal statistics pt. 2
│ ├── 00e_exploratory_distance_calculations_hexbins.ipynb # PostGIS and SQL to calculate hexagon-wise distance to various OSM features (roads, markets, rivers, population centers)
│ ├── 00f_exploratory_region_grids.ipynb # Building rectangular mesh for zonal statistics pt. 2
│ ├── 00g_exploratory_distance_calculations_grids.ipynb # # PostGIS and SQL to calculate cell-wise distance to various OSM features (roads, markets, rivers, population centers)
│ ├── 01a_visualize_maxar_chips_copy.ipynb # Visualizing maxar images clipped to 1km x 1km grid cells with OSM feature overlay
│ └── 01b_cloud_mask_maxar_imagery.ipynb # Visualizing a potential cloud masking approach (threshold based, does not work)
│
├── outputs/
│ ├── maps/
│ │ ├── dynamic/ # Interactive or animated map outputs built with leaflet
│ │ └── static/ # Static maps/figures for papers & slides
│
├── scripts/ 
│ └── 00_create_spatial_index.py # (Run this on the HPC) Generates a .json file containing an .json file of all maxar images. Key-Value pairs map filenames with full filepaths.
│ └── 01_search_chip_maxar_metadata.py # (Run this on the HPC) Downloads Maxar images that overlap with AOI, uses 00 spatial index to avoid repeated recursive searches through the full filesystem.
│
├── .gitignore
├── environment.yml # Conda environment specification
└── README.md

---

## **Data Sources**

### **Maxar VHR Imagery (0.5 m)**
- Downloaded from OSU’s HPC archive  
- Preprocessed with GDAL 

### **OpenStreetMap (OSM) Roads and Paths**
- Downloaded using `osmnx` (Overpass API)  
- Will be adapted for use as baseline road and footpath annotations 
- Supplemented with manually digitized paths in priority areas  

---

## **Preprocessing Pipeline (Current Project Stage)**

### **1. Maxar Scene Indexing**
- Python utility scans the Maxar archive and creates a JSON index mapping each filename to its full filepath. This speeds up repeated access during experimentation.
- Maxar images are accessed via GDALINFO and converted to .TIF files via GDALWARP, full metadata is preserved. 

### **2. AOI Clipping**
- Python notebook creates 1km x 1km grid cells over Nakivale, Uganda (with 500m buffer), randomly subsets 300 grid cells and exports as .geojson.
- .geojson file used with `gdalwarp -cutline` to download and crop overlapping Maxar scenes. Processed 1km x 1km maxar images are saved as GeoTiffs. 

### **3. Tiling**
Images are tiled into **512 × 512 px** chips (~256 × 256 m).  
This produces analysis-ready data for future CNN training.

### **4. Rasterizing Training Labels**
- OSM + manual footpaths --> raster masks aligned to image tiles  
- Masks will serve as training labels for the segmentation model
- We will test several training datasets from low effort --> high effort where low effort is buffered OSM data and high effort is manual annotations + manually adapted OSM data. 

---

## **Planned Model Workflow (Future Work)**

- Compare several CNN architectures, starting with a **U-Net**, another architecture that is of special interest is **CE-RoadNet** a cascaded network approach
- Loss: potentially clDice 
- Postprocessing to vectorize and enforce topography  
- Evaluation vs. OSM and manual labels

---

## **Installation**

Clone the repository:

```bash
git clone https://github.com/zrmondsc/uganda_roads.git
cd uganda_roads

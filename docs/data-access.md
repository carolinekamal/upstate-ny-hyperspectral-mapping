# Accessing NASA EMIT data

## Product identification

- Product short name: `EMITL2ARFL`
- Collection concept ID: `C2408750690-LPCLOUD`
- DOI: `10.5067/EMIT/EMITL2ARFL.001`
- Spatial resolution: approximately 60 m
- Spectral range: approximately 381–2493 nm
- Band count: 285

Official product page: https://www.earthdata.nasa.gov/data/catalog/lpcloud-emitl2arfl-001

## Install the optional dependencies

```bash
python -m pip install -e '.[nasa]'
```

These dependencies provide NASA search and authentication, NetCDF access, and optional GeoTIFF export.

## Search before making coverage claims

Finger Lakes:

```bash
python -m upstate_hyperspectral search \
  --region finger-lakes \
  --start 2022-08-09 \
  --end 2026-10-31 \
  --save outputs/finger-lakes-inventory.json
```

Lake Erie grape belt:

```bash
python -m upstate_hyperspectral search \
  --region lake-erie \
  --start 2022-08-09 \
  --end 2026-10-31 \
  --save outputs/lake-erie-inventory.json
```

A zero-result search is meaningful: the region may not have a suitable EMIT acquisition, or available scenes may not overlap the selected time window. Because the mission emphasizes arid dust-source regions, upstate New York is not guaranteed coverage.

If EMIT scenes are unavailable, consider an authorized airborne imaging-spectroscopy dataset such as AVIRIS, or adapt the workflow to another public reflectance product. Preserve instrument provenance and never label another sensor's imagery as EMIT.

## Authenticate and download

Create a free NASA Earthdata account at https://urs.earthdata.nasa.gov/.

```bash
python -m upstate_hyperspectral search \
  --region finger-lakes \
  --start 2023-05-01 \
  --end 2026-10-31 \
  --download \
  --download-dir data/raw
```

`data/raw/` is ignored by Git. Do not commit Earthdata credentials, access tokens, a `.netrc` file, or private research datasets.

## Process a downloaded scene

```bash
python -m upstate_hyperspectral process \
  --input data/raw/EMIT_L2A_RFL_001_YYYYMMDDTHHMMSS_ORBIT_SCENE.nc \
  --mask data/raw/EMIT_L2A_MASK_001_YYYYMMDDTHHMMSS_ORBIT_SCENE.nc \
  --mask-flags 0,1 \
  --region finger-lakes \
  --output-dir outputs/real-finger-lakes
```

The example filenames above are placeholders. Inspect the mask product's band metadata and select quality flags appropriate to your research question before using `--mask-flags`.

## NASA tutorials

- https://github.com/nasa/EMIT-Data-Resources
- https://nasa.github.io/VITALS/python/Exploring_EMIT_L2A_RFL.html
- https://earth.jpl.nasa.gov/emit/data/trainings/

# Methodology

## 1. Study design

The project asks how imaging spectroscopy can characterize surface variability in three upstate New York agricultural regions. Its purpose is methodological: demonstrate a responsible workflow for linking remote-sensing physics, unsupervised learning, and materials-related interpretation.

The Finger Lakes and Lake Erie grape belt are appropriate geographic case studies because their landscapes include water, cropland, forest, and exposed soils. However, EMIT was designed primarily for arid mineral-dust source regions, so local observation availability cannot be presumed.

## 2. EMIT Level 2A reflectance

NASA's EMIT L2A product contains 285 reflectance bands from approximately 381 to 2493 nm. Its nominal spatial resolution is 60 m. The distributed NetCDF product uses raw downtrack/crosstrack coordinates and includes a geometry lookup table for projection onto a WGS84 grid.

The reader in `nasa.py`:

1. Opens the root, `location`, and `sensor_band_parameters` NetCDF groups.
2. Computes geographic pixel-center coordinates from the scene geotransform.
3. Crops the geometry lookup table to the selected region.
4. Loads only the raw-space subset required for those pixels.
5. Converts the lookup table's one-indexed coordinates into NumPy indices.
6. Applies available quality flags and removes fill values.
7. Retains the mission-provided `good_wavelengths` flags when available.

Cropping before constructing the orthorectified cube is important because a full EMIT scene may require several gigabytes of memory.

## 3. Atmospheric-band filtering

Atmospheric water absorption reduces usable information around approximately 1320–1440 nm and 1770–1970 nm. The preferred filter is the product's own `good_wavelengths` variable. If that variable is absent, the demonstration applies approximate exclusion windows and documents the assumption.

## 4. Vegetation and water screening

Vegetation is evaluated using:

```text
NDVI = (R850 − R665) / (R850 + R665)
```

Water screening uses a green/NIR normalized difference:

```text
NDWI = (R560 − R850) / (R560 + R850)
```

Default thresholds are exploratory, not universal calibration constants. Thresholds should be adjusted and independently checked against each real scene.

Pixels interpreted as dense vegetation or open water are excluded from exposed-surface absorption maps. This prevents incorrectly treating a vegetation spectrum as evidence of concealed soil or bedrock mineralogy.

## 5. PCA and clustering

The workflow selects usable bands, subsamples the spectral axis, standardizes features, and applies principal component analysis. It then fits k-means in PCA space and calculates a sampled silhouette score.

PCA separates dominant modes of variation. K-means groups pixels by spectral similarity. Neither method independently identifies a mineral or diagnoses vineyard disease. Cluster interpretation requires external observations and reference data.

## 6. Continuum-removed absorption features

Exploratory absorption depth is calculated as:

```text
depth = 1 − R(center) / R(continuum)
```

The continuum is linearly interpolated between shoulder wavelengths.

| Approximate center | Shoulders | Exploratory interpretation |
| --- | --- | --- |
| 900 nm | 740 and 1080 nm | Ferric-oxide-related spectral behavior |
| 2200 nm | 2120 and 2270 nm | Al–OH / clay-related behavior |
| 2335 nm | 2260 and 2400 nm | Carbonate-related behavior |

These features are not unique to individual minerals. Illumination, moisture, grain size, mixture composition, and instrument noise can all produce ambiguous behavior.

## 7. Reproducibility

- The demonstration scene uses a fixed random seed.
- The scene is labeled synthetic in the README, figure footer, CLI output, and JSON summary.
- All region bounds are versioned in Python and GeoJSON.
- PCA and k-means use fixed random states.
- The automated tests validate masks, wavelength handling, region coordinates, provenance, and NASA collection identifiers.

## 8. Validation required for real scientific claims

Before interpreting an observed map, compare against field samples, laboratory Raman or XRD measurements, validated spectral reference libraries, and independently documented land-cover information. For region-specific vineyard applications, obtain permission before publishing private parcel boundaries or collaborators' imagery.

"""Optional NASA Earthdata discovery and memory-conscious EMIT L2A ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from upstate_hyperspectral.regions import StudyRegion
from upstate_hyperspectral.synthetic import HyperspectralScene

EMIT_REFLECTANCE_COLLECTION = "C2408750690-LPCLOUD"
EMIT_REFLECTANCE_SHORT_NAME = "EMITL2ARFL"


def _earthaccess():
    try:
        import earthaccess
    except ImportError as exc:
        raise RuntimeError(
            "NASA access requires the optional dependencies. Install them with: "
            "python -m pip install -e '.[nasa]'"
        ) from exc
    return earthaccess


def search_emit_granules(
    region: StudyRegion,
    start: str,
    end: str,
    *,
    count: int = 25,
) -> list[Any]:
    """Query actual coverage; never infer scene availability from latitude alone."""
    earthaccess = _earthaccess()
    return list(
        earthaccess.search_data(
            concept_id=EMIT_REFLECTANCE_COLLECTION,
            bounding_box=region.bbox,
            temporal=(start, end),
            count=count,
        )
    )


def summarize_granules(results: list[Any]) -> list[dict[str, Any]]:
    summaries = []
    for item in results:
        umm = item.get("umm", {})
        temporal = umm.get("TemporalExtent", {}).get("RangeDateTime", {})
        data_links = item.data_links() if hasattr(item, "data_links") else []
        summaries.append(
            {
                "granule_ur": umm.get("GranuleUR", "Unknown granule"),
                "start": temporal.get("BeginningDateTime"),
                "end": temporal.get("EndingDateTime"),
                "file_count": len(data_links),
                "files": data_links,
            }
        )
    return summaries


def download_granules(results: list[Any], destination: str | Path) -> list[Path]:
    """Download real NASA files after the user authenticates with Earthdata."""
    earthaccess = _earthaccess()
    earthaccess.login(strategy="interactive", persist=False)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    return [Path(path) for path in earthaccess.download(results, local_path=str(destination))]


def orthorectify_emit_subset(
    reflectance_path: str | Path,
    region: StudyRegion,
    *,
    mask_path: str | Path | None = None,
    mask_flags: tuple[int, ...] = (0, 1),
) -> HyperspectralScene:
    """Subset an EMIT geometric lookup table before loading the reflectance cube.

    NASA distributes EMIT L2A in raw downtrack/crosstrack geometry. The GLT is
    one-indexed, with zero signifying no data. We crop the GLT to the requested
    region before allocating the orthorectified cube to reduce memory pressure.
    """
    try:
        import xarray as xr
    except ImportError as exc:
        raise RuntimeError("Install the NASA extras first: python -m pip install -e '.[nasa]'") from exc

    reflectance_path = Path(reflectance_path)
    with (
        xr.open_dataset(reflectance_path, engine="h5netcdf") as root,
        xr.open_dataset(reflectance_path, engine="h5netcdf", group="location") as location,
        xr.open_dataset(
            reflectance_path, engine="h5netcdf", group="sensor_band_parameters"
        ) as sensor,
    ):
        geotransform = np.asarray(root.attrs.get("geotransform", []), dtype=float)
        if geotransform.size != 6:
            raise ValueError("EMIT granule does not contain a six-value geotransform attribute.")

        glt_x = np.asarray(location["glt_x"].values)
        glt_y = np.asarray(location["glt_y"].values)
        longitude_vector = (geotransform[0] + geotransform[1] / 2) + np.arange(
            glt_x.shape[1]
        ) * geotransform[1]
        latitude_vector = (geotransform[3] + geotransform[5] / 2) + np.arange(
            glt_x.shape[0]
        ) * geotransform[5]

        columns = np.flatnonzero((longitude_vector >= region.west) & (longitude_vector <= region.east))
        rows = np.flatnonzero((latitude_vector >= region.south) & (latitude_vector <= region.north))
        if rows.size == 0 or columns.size == 0:
            raise ValueError(f"This EMIT granule does not overlap {region.name}.")

        row_slice = slice(int(rows.min()), int(rows.max()) + 1)
        column_slice = slice(int(columns.min()), int(columns.max()) + 1)
        local_x = np.nan_to_num(glt_x[row_slice, column_slice], nan=0).astype(np.int64)
        local_y = np.nan_to_num(glt_y[row_slice, column_slice], nan=0).astype(np.int64)
        valid_lookup = (local_x > 0) & (local_y > 0)
        if not np.any(valid_lookup):
            raise ValueError("The requested region intersects the granule extent but has no valid GLT pixels.")

        raw_columns = local_x[valid_lookup] - 1
        raw_rows = local_y[valid_lookup] - 1
        raw_row_min, raw_row_max = int(raw_rows.min()), int(raw_rows.max())
        raw_column_min, raw_column_max = int(raw_columns.min()), int(raw_columns.max())

        raw_subset = np.asarray(
            root["reflectance"]
            .isel(
                downtrack=slice(raw_row_min, raw_row_max + 1),
                crosstrack=slice(raw_column_min, raw_column_max + 1),
            )
            .values,
            dtype=np.float32,
        )

        wavelengths = np.asarray(sensor["wavelengths"].values, dtype=np.float32)
        quality = np.zeros(local_x.shape, dtype=bool)
        cube = np.full((*local_x.shape, wavelengths.size), np.nan, dtype=np.float32)
        cube[valid_lookup] = raw_subset[
            raw_rows - raw_row_min,
            raw_columns - raw_column_min,
        ]
        cube[cube <= -9990] = np.nan
        quality[valid_lookup] = np.isfinite(cube[valid_lookup]).any(axis=1)

        if mask_path is not None:
            with xr.open_dataset(mask_path, engine="h5netcdf") as mask_ds:
                raw_mask = np.asarray(
                    mask_ds["mask"]
                    .isel(
                        downtrack=slice(raw_row_min, raw_row_max + 1),
                        crosstrack=slice(raw_column_min, raw_column_max + 1),
                    )
                    .values
                )
            selected_flags = raw_mask[..., list(mask_flags)]
            flagged = np.any(selected_flags > 0, axis=-1)
            quality[valid_lookup] &= ~flagged[
                raw_rows - raw_row_min,
                raw_columns - raw_column_min,
            ]
            cube[~quality] = np.nan

        if "good_wavelengths" in sensor:
            good = np.asarray(sensor["good_wavelengths"].values, dtype=bool)
        else:
            good = ~(
                ((wavelengths >= 1320) & (wavelengths <= 1440))
                | ((wavelengths >= 1770) & (wavelengths <= 1970))
            )

    longitude, latitude = np.meshgrid(longitude_vector[column_slice], latitude_vector[row_slice])
    return HyperspectralScene(
        reflectance=cube,
        wavelengths_nm=wavelengths,
        longitude=longitude,
        latitude=latitude,
        good_wavelengths=good,
        quality_mask=quality,
        provenance=f"NASA EMIT L2A observed reflectance: {reflectance_path.name}",
        region=region,
    )


def export_geotiff(path: str | Path, values: np.ndarray, scene: HyperspectralScene) -> Path:
    """Export a north-up WGS84 raster for use in QGIS or ArcGIS."""
    try:
        import rasterio
        from rasterio.transform import from_bounds
    except ImportError as exc:
        raise RuntimeError("GeoTIFF export requires: python -m pip install -e '.[nasa]'") from exc

    values = np.asarray(values, dtype=np.float32)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    transform = from_bounds(
        float(scene.longitude.min()),
        float(scene.latitude.min()),
        float(scene.longitude.max()),
        float(scene.latitude.max()),
        values.shape[1],
        values.shape[0],
    )
    with rasterio.open(
        output,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=np.nan,
        compress="deflate",
    ) as raster:
        raster.write(values, 1)
    return output

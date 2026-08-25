"""Generate a clearly identified synthetic scene for a no-credentials demonstration.

These arrays illustrate an analysis workflow. They are never represented as NASA
observations, field measurements, a real mineral map, or verified crop conditions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter

from upstate_hyperspectral.regions import StudyRegion


@dataclass(frozen=True)
class HyperspectralScene:
    reflectance: np.ndarray
    wavelengths_nm: np.ndarray
    longitude: np.ndarray
    latitude: np.ndarray
    good_wavelengths: np.ndarray
    quality_mask: np.ndarray
    provenance: str
    region: StudyRegion

    @property
    def shape(self) -> tuple[int, int, int]:
        return tuple(self.reflectance.shape)


def _gaussian(wavelengths: np.ndarray, center: float, width: float) -> np.ndarray:
    return np.exp(-0.5 * ((wavelengths - center) / width) ** 2)


def reference_endmembers(wavelengths_nm: np.ndarray) -> dict[str, np.ndarray]:
    """Return deliberately approximate teaching signatures, not reference spectra."""
    w = np.asarray(wavelengths_nm, dtype=np.float64)
    red_edge = 1 / (1 + np.exp(-(w - 710.0) / 20.0))
    moisture_1450 = _gaussian(w, 1450, 50)
    moisture_1950 = _gaussian(w, 1940, 75)

    water = 0.044 * np.exp(-(w - 400) / 370) + 0.005
    forest = 0.043 + 0.43 * red_edge - 0.10 * moisture_1450 - 0.14 * moisture_1950
    cropland = 0.066 + 0.31 * red_edge - 0.07 * moisture_1450 - 0.10 * moisture_1950
    clay_soil = 0.16 + 0.000075 * (w - 400) - 0.077 * _gaussian(w, 2200, 33)
    carbonate_soil = 0.21 + 0.00006 * (w - 400) - 0.073 * _gaussian(w, 2335, 38)
    ferric_soil = (
        0.115
        + 0.00012 * (w - 400)
        + 0.045 * _gaussian(w, 660, 80)
        - 0.067 * _gaussian(w, 900, 85)
    )

    spectra = {
        "water": water,
        "forest": forest,
        "cropland": cropland,
        "clay-rich soil proxy": clay_soil,
        "carbonate-bearing soil proxy": carbonate_soil,
        "ferric-oxide soil proxy": ferric_soil,
    }
    return {name: np.clip(value, 0.005, 0.78).astype(np.float32) for name, value in spectra.items()}


def _landscape_classes(
    region: StudyRegion,
    longitude: np.ndarray,
    latitude: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    height, width = longitude.shape
    landscape = gaussian_filter(rng.normal(size=(height, width)), sigma=max(3, width / 32))
    landscape = (landscape - landscape.min()) / (np.ptp(landscape) + 1e-9)

    classes = np.full((height, width), 2, dtype=np.uint8)
    classes[landscape > 0.62] = 1
    classes[(landscape >= 0.36) & (landscape < 0.47)] = 3
    classes[(landscape >= 0.47) & (landscape < 0.55)] = 4
    classes[landscape < 0.28] = 5

    if region.slug == "lake-erie":
        shoreline = 42.70 - 0.28 * (longitude + 79.90)
        lake = latitude > shoreline
    else:
        # Idealized lake-shaped masks roughly oriented along Seneca/Cayuga;
        # these are visual landmarks, not shoreline or remotely sensed data.
        seneca_center = -76.92 + 0.055 * (latitude - 42.65)
        cayuga_center = -76.68 + 0.045 * (latitude - 42.65)
        seneca = (np.abs(longitude - seneca_center) < 0.030) & (latitude > 42.40) & (latitude < 42.88)
        cayuga = (np.abs(longitude - cayuga_center) < 0.028) & (latitude > 42.47) & (latitude < 42.95)
        lake = seneca | cayuga

    classes[lake] = 0
    return classes


def generate_demo_scene(
    region: StudyRegion,
    *,
    height: int = 154,
    width: int = 224,
    seed: int = 2026,
) -> HyperspectralScene:
    """Create an EMIT-shaped, explicitly simulated 285-band teaching dataset."""
    if min(height, width) < 8:
        raise ValueError("Synthetic scene dimensions must each be at least eight pixels.")

    rng = np.random.default_rng(seed)
    wavelengths = np.linspace(381, 2493, 285, dtype=np.float32)
    longitude_values = np.linspace(region.west, region.east, width, dtype=np.float64)
    latitude_values = np.linspace(region.north, region.south, height, dtype=np.float64)
    longitude, latitude = np.meshgrid(longitude_values, latitude_values)

    signatures = reference_endmembers(wavelengths)
    classes = _landscape_classes(region, longitude, latitude, rng)
    ordered_signatures = np.stack(list(signatures.values()))
    reflectance = ordered_signatures[classes]

    illumination = gaussian_filter(rng.normal(size=(height, width)), sigma=7)
    illumination = 1.0 + 0.065 * illumination / (np.max(np.abs(illumination)) + 1e-9)
    reflectance = reflectance * illumination[..., np.newaxis]
    reflectance += rng.normal(0, 0.006, size=reflectance.shape)
    reflectance = np.clip(reflectance, 0.001, 0.95).astype(np.float32)

    # EMIT's actual good_wavelengths flags should be used on real observations.
    good_wavelengths = ~(
        ((wavelengths >= 1320) & (wavelengths <= 1440))
        | ((wavelengths >= 1770) & (wavelengths <= 1970))
    )

    cloud_field = gaussian_filter(rng.random((height, width)), sigma=width / 35)
    quality_mask = cloud_field <= np.quantile(cloud_field, 0.973)
    reflectance[~quality_mask] = np.nan

    return HyperspectralScene(
        reflectance=reflectance,
        wavelengths_nm=wavelengths,
        longitude=longitude,
        latitude=latitude,
        good_wavelengths=good_wavelengths,
        quality_mask=quality_mask,
        provenance="SYNTHETIC DEMONSTRATION — not NASA imagery or observed mineralogy",
        region=region,
    )

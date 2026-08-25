"""Spectral indices, atmospheric filtering, and unsupervised surface analysis."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from upstate_hyperspectral.synthetic import HyperspectralScene


@dataclass(frozen=True)
class AnalysisResult:
    ndvi: np.ndarray
    ndwi: np.ndarray
    clay_absorption: np.ndarray
    carbonate_absorption: np.ndarray
    ferric_absorption: np.ndarray
    water_mask: np.ndarray
    vegetation_mask: np.ndarray
    exposed_surface_mask: np.ndarray
    cluster_map: np.ndarray
    pca_scores: np.ndarray
    cluster_labels: np.ndarray
    explained_variance_ratio: np.ndarray
    silhouette: float
    cluster_spectra: dict[int, np.ndarray]


def nearest_band_index(wavelengths_nm: np.ndarray, target_nm: float) -> int:
    wavelengths = np.asarray(wavelengths_nm, dtype=float)
    if wavelengths.ndim != 1 or wavelengths.size == 0:
        raise ValueError("Wavelengths must be a non-empty one-dimensional array.")
    return int(np.abs(wavelengths - target_nm).argmin())


def band_at(scene: HyperspectralScene, wavelength_nm: float) -> np.ndarray:
    return scene.reflectance[..., nearest_band_index(scene.wavelengths_nm, wavelength_nm)]


def normalized_difference(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    first = np.asarray(first, dtype=np.float64)
    second = np.asarray(second, dtype=np.float64)
    denominator = first + second
    result = np.full(first.shape, np.nan, dtype=np.float64)
    np.divide(first - second, denominator, out=result, where=np.abs(denominator) > 1e-10)
    return np.clip(result, -1, 1)


def continuum_band_depth(
    scene: HyperspectralScene,
    center_nm: float,
    left_nm: float,
    right_nm: float,
) -> np.ndarray:
    """Estimate absorption depth from a linear two-point continuum."""
    if not left_nm < center_nm < right_nm:
        raise ValueError("Absorption wavelengths must satisfy left < center < right.")

    center = band_at(scene, center_nm)
    left = band_at(scene, left_nm)
    right = band_at(scene, right_nm)
    fraction = (center_nm - left_nm) / (right_nm - left_nm)
    continuum = left + fraction * (right - left)
    depth = np.full(center.shape, np.nan, dtype=np.float64)
    np.divide(center, continuum, out=depth, where=continuum > 1e-10)
    return np.clip(1.0 - depth, -0.2, 1.0)


def analyze_scene(
    scene: HyperspectralScene,
    *,
    n_clusters: int = 6,
    random_state: int = 42,
    max_fit_pixels: int = 14000,
) -> AnalysisResult:
    if n_clusters < 2:
        raise ValueError("At least two clusters are needed for spectral clustering.")

    red = band_at(scene, 665)
    nir = band_at(scene, 850)
    green = band_at(scene, 560)
    ndvi = normalized_difference(nir, red)
    ndwi = normalized_difference(green, nir)

    finite = scene.quality_mask & np.isfinite(red) & np.isfinite(nir)
    water_mask = finite & (((ndwi > 0.10) & (nir < 0.13)) | ((nir < 0.045) & (red < 0.07)))
    vegetation_mask = finite & ~water_mask & (ndvi >= 0.38)
    exposed_surface_mask = finite & ~water_mask & ~vegetation_mask

    clay = continuum_band_depth(scene, 2200, 2120, 2270)
    carbonate = continuum_band_depth(scene, 2335, 2260, 2400)
    ferric = continuum_band_depth(scene, 900, 740, 1080)

    usable_band_indices = np.flatnonzero(scene.good_wavelengths)[::3]
    fit_mask = finite & ~water_mask
    features = scene.reflectance[..., usable_band_indices][fit_mask]
    valid_features = np.isfinite(features).all(axis=1)
    if not np.all(valid_features):
        fit_coordinates = np.argwhere(fit_mask)[valid_features]
        fit_mask = np.zeros_like(fit_mask)
        fit_mask[fit_coordinates[:, 0], fit_coordinates[:, 1]] = True
        features = features[valid_features]

    if len(features) < n_clusters * 2:
        raise ValueError("Not enough valid, non-water pixels to fit the requested clusters.")

    rng = np.random.default_rng(random_state)
    fit_indices = (
        rng.choice(len(features), size=max_fit_pixels, replace=False)
        if len(features) > max_fit_pixels
        else np.arange(len(features))
    )

    scaler = StandardScaler()
    scaled_training = scaler.fit_transform(features[fit_indices])
    component_count = min(6, scaled_training.shape[0], scaled_training.shape[1])
    pca = PCA(n_components=component_count, random_state=random_state)
    training_scores = pca.fit_transform(scaled_training)

    clusterer = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    clusterer.fit(training_scores)

    scores = pca.transform(scaler.transform(features))
    labels = clusterer.predict(scores)

    cluster_map = np.full(scene.quality_mask.shape, -1, dtype=np.int16)
    cluster_map[fit_mask] = labels

    score_indices = (
        rng.choice(len(labels), size=2500, replace=False)
        if len(labels) > 2500
        else np.arange(len(labels))
    )
    silhouette = float(silhouette_score(scores[score_indices], labels[score_indices]))

    cluster_spectra = {
        int(label): np.nanmedian(scene.reflectance[cluster_map == label], axis=0)
        for label in range(n_clusters)
    }

    return AnalysisResult(
        ndvi=ndvi,
        ndwi=ndwi,
        clay_absorption=clay,
        carbonate_absorption=carbonate,
        ferric_absorption=ferric,
        water_mask=water_mask,
        vegetation_mask=vegetation_mask,
        exposed_surface_mask=exposed_surface_mask,
        cluster_map=cluster_map,
        pca_scores=scores,
        cluster_labels=labels,
        explained_variance_ratio=pca.explained_variance_ratio_,
        silhouette=silhouette,
        cluster_spectra=cluster_spectra,
    )


def build_summary(scene: HyperspectralScene, result: AnalysisResult) -> dict:
    valid = int(np.count_nonzero(scene.quality_mask))
    cluster_counts = {
        str(label): int(np.count_nonzero(result.cluster_map == label))
        for label in np.unique(result.cluster_labels)
    }
    return {
        "project": "Upstate New York hyperspectral surface mapping",
        "region": scene.region.name,
        "region_bbox_wgs84": list(scene.region.bbox),
        "provenance": scene.provenance,
        "is_synthetic": scene.provenance.startswith("SYNTHETIC"),
        "scene_shape": list(scene.shape),
        "wavelength_range_nm": [float(scene.wavelengths_nm.min()), float(scene.wavelengths_nm.max())],
        "total_bands": int(len(scene.wavelengths_nm)),
        "usable_bands": int(np.count_nonzero(scene.good_wavelengths)),
        "valid_pixels": valid,
        "water_pixels": int(np.count_nonzero(result.water_mask)),
        "vegetation_pixels": int(np.count_nonzero(result.vegetation_mask)),
        "exposed_surface_pixels": int(np.count_nonzero(result.exposed_surface_mask)),
        "exposed_surface_fraction": round(float(np.count_nonzero(result.exposed_surface_mask) / valid), 4),
        "pca_explained_variance_ratio": [round(float(value), 5) for value in result.explained_variance_ratio],
        "pca_cumulative_explained_variance": round(float(result.explained_variance_ratio.sum()), 5),
        "cluster_count": len(cluster_counts),
        "cluster_pixel_counts": cluster_counts,
        "silhouette_score": round(result.silhouette, 4),
        "interpretation_note": (
            "Clusters and absorption features are exploratory surface-spectral proxies. "
            "They are not validated mineral identifications, crop diagnoses, or maps of "
            "materials beneath vegetation."
        ),
    }

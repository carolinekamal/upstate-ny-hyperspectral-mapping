"""Publication-style figures that preserve the provenance of every scene."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

from upstate_hyperspectral.analysis import AnalysisResult, band_at
from upstate_hyperspectral.synthetic import HyperspectralScene

NAVY = "#17324d"
TEAL = "#167e79"
MUTED = "#657687"
PAPER = "#f7f8f6"
CLUSTER_COLORS = ["#218a7c", "#e1b85e", "#7086ae", "#ba6a4e", "#78a36d", "#826a95", "#d78653", "#647a82"]

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
        "axes.titlecolor": NAVY,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "figure.facecolor": PAPER,
        "axes.facecolor": PAPER,
        "savefig.facecolor": PAPER,
    }
)


def _extent(scene: HyperspectralScene) -> tuple[float, float, float, float]:
    return (
        float(scene.longitude.min()),
        float(scene.longitude.max()),
        float(scene.latitude.min()),
        float(scene.latitude.max()),
    )


def _provenance(fig: plt.Figure, scene: HyperspectralScene) -> None:
    layout_engine = fig.get_layout_engine()
    if layout_engine is not None:
        layout_engine.set(rect=(0, 0.078, 1, 0.922))
    prefix = "SYNTHETIC DEMONSTRATION" if scene.provenance.startswith("SYNTHETIC") else "NASA EMIT OBSERVATION"
    fig.text(
        0.99,
        0.012,
        f"{prefix}  |  Caroline Kamal  |  {scene.region.name}",
        ha="right",
        va="bottom",
        fontsize=8,
        color=MUTED,
    )


def _landmarks(axis: plt.Axes, scene: HyperspectralScene, color: str = "white") -> None:
    for label, longitude, latitude in scene.region.landmarks:
        if scene.region.contains(longitude, latitude):
            axis.plot(longitude, latitude, "o", markersize=3.3, color=color, markeredgecolor=NAVY, markeredgewidth=0.5)
            axis.annotate(
                label,
                (longitude, latitude),
                xytext=(5, 4),
                textcoords="offset points",
                color=color,
                fontsize=7,
                weight="bold",
                bbox={"boxstyle": "round,pad=0.12", "fc": NAVY, "ec": "none", "alpha": 0.62},
            )


def _map_axes(axis: plt.Axes) -> None:
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.tick_params(labelsize=7.5)


def _save(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def save_study_overview(scene: HyperspectralScene, result: AnalysisResult, path: Path) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(16.4, 5.5), constrained_layout=True)
    fig.suptitle("UPSTATE NEW YORK  /  HYPERSPECTRAL LANDSCAPE", x=0.03, ha="left", fontsize=17, color=NAVY, weight="bold")

    red = band_at(scene, 850)
    green = band_at(scene, 665)
    blue = band_at(scene, 560)
    stack = np.stack([red, green, blue], axis=-1)
    low, high = np.nanpercentile(stack, [2, 98])
    false_color = np.clip((stack - low) / (high - low), 0, 1)
    false_color = np.nan_to_num(false_color, nan=0.90)

    axes[0].imshow(false_color, extent=_extent(scene), aspect="auto")
    axes[0].set_title("01  /  FALSE-COLOR REFLECTANCE")
    _landmarks(axes[0], scene)

    ndvi = axes[1].imshow(result.ndvi, extent=_extent(scene), cmap="RdYlGn", vmin=-0.5, vmax=0.9, aspect="auto")
    axes[1].set_title("02  /  VEGETATION SIGNAL · NDVI")
    fig.colorbar(ndvi, ax=axes[1], fraction=0.047, pad=0.03, label="NDVI")

    visible_clusters = np.ma.masked_where(result.cluster_map < 0, result.cluster_map)
    axes[2].imshow(
        visible_clusters,
        extent=_extent(scene),
        cmap=ListedColormap(CLUSTER_COLORS[: len(result.cluster_spectra)]),
        interpolation="nearest",
        aspect="auto",
    )
    axes[2].set_title("03  /  PCA + K-MEANS SURFACE GROUPS")
    _landmarks(axes[2], scene)

    for axis in axes:
        _map_axes(axis)
    _provenance(fig, scene)
    return _save(fig, path)


def save_spectral_signatures(scene: HyperspectralScene, result: AnalysisResult, path: Path) -> Path:
    fig, axis = plt.subplots(figsize=(12.5, 5.8), constrained_layout=True)
    fig.suptitle("MEDIAN SPECTRAL SIGNATURES  /  SURFACE CLUSTERS", x=0.06, ha="left", fontsize=16, color=NAVY, weight="bold")

    for cluster, spectrum in result.cluster_spectra.items():
        plot_spectrum = np.array(spectrum, copy=True)
        plot_spectrum[~scene.good_wavelengths] = np.nan
        axis.plot(scene.wavelengths_nm, plot_spectrum, lw=2, color=CLUSTER_COLORS[cluster], label=f"Cluster {cluster + 1}")

    for lower, upper in ((1320, 1440), (1770, 1970)):
        axis.axvspan(lower, upper, color=NAVY, alpha=0.055)
    for center, label in ((900, "Fe-oxide proxy"), (2200, "Al-OH / clay proxy"), (2335, "carbonate proxy")):
        axis.axvline(center, linestyle="--", linewidth=0.9, color=MUTED, alpha=0.75)
        axis.text(center + 10, axis.get_ylim()[1] * 0.93, label, fontsize=7, rotation=90, color=MUTED, va="top")

    axis.set_xlabel("Wavelength (nm)")
    axis.set_ylabel("Surface reflectance")
    axis.set_xlim(380, 2495)
    axis.legend(frameon=False, ncol=3, loc="upper left")
    axis.grid(axis="y", color="#dce3e4", alpha=0.8, linewidth=0.7)
    _provenance(fig, scene)
    return _save(fig, path)


def save_pca_clusters(scene: HyperspectralScene, result: AnalysisResult, path: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13.4, 5.3), gridspec_kw={"width_ratios": [1.8, 1]}, constrained_layout=True)
    fig.suptitle("SPECTRAL DIMENSIONALITY  /  INTERPRETABLE UNSUPERVISED LEARNING", x=0.04, ha="left", fontsize=15, color=NAVY, weight="bold")

    rng = np.random.default_rng(12)
    sample = rng.choice(len(result.cluster_labels), size=min(5500, len(result.cluster_labels)), replace=False)
    for cluster in result.cluster_spectra:
        cluster_sample = sample[result.cluster_labels[sample] == cluster]
        axes[0].scatter(
            result.pca_scores[cluster_sample, 0],
            result.pca_scores[cluster_sample, 1],
            s=8,
            alpha=0.55,
            color=CLUSTER_COLORS[cluster],
            label=f"Cluster {cluster + 1}",
            rasterized=True,
        )
    axes[0].set_xlabel(f"PC1  ·  {result.explained_variance_ratio[0]:.1%} explained variance")
    axes[0].set_ylabel(f"PC2  ·  {result.explained_variance_ratio[1]:.1%} explained variance")
    axes[0].legend(frameon=False, ncol=2, fontsize=8)
    axes[0].set_title(f"Pixel separation in PCA space  ·  silhouette {result.silhouette:.2f}", loc="left")

    component_numbers = np.arange(1, len(result.explained_variance_ratio) + 1)
    axes[1].bar(component_numbers, result.explained_variance_ratio * 100, color=TEAL, alpha=0.86)
    axes[1].plot(component_numbers, np.cumsum(result.explained_variance_ratio) * 100, "o-", color=NAVY, lw=1.7)
    axes[1].set_xticks(component_numbers)
    axes[1].set_xlabel("Principal component")
    axes[1].set_ylabel("Explained variance (%)")
    axes[1].set_title("Variance retained", loc="left")
    axes[1].grid(axis="y", color="#dce3e4", alpha=0.8, linewidth=0.7)
    _provenance(fig, scene)
    return _save(fig, path)


def save_surface_proxies(scene: HyperspectralScene, result: AnalysisResult, path: Path) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(16.4, 5.6), constrained_layout=True)
    fig.suptitle("EXPOSED SURFACES ONLY  /  EXPLORATORY ABSORPTION FEATURES", x=0.025, ha="left", fontsize=16, color=NAVY, weight="bold")

    layers = [
        (result.clay_absorption, "01  /  2200 nm · Al-OH PROXY", "viridis"),
        (result.carbonate_absorption, "02  /  2335 nm · CARBONATE PROXY", "cividis"),
        (result.ferric_absorption, "03  /  900 nm · Fe-OXIDE PROXY", "magma"),
    ]
    for axis, (values, title, cmap) in zip(axes, layers):
        mapped = np.where(result.exposed_surface_mask, values, np.nan)
        vmax = max(0.05, float(np.nanpercentile(mapped, 98)))
        image = axis.imshow(mapped, extent=_extent(scene), cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
        axis.set_title(title)
        _map_axes(axis)
        fig.colorbar(image, ax=axis, fraction=0.047, pad=0.03, label="Continuum-removed band depth")

    fig.text(
        0.028,
        0.047,
        "Vegetation, open water, and invalid pixels are excluded; absorption features do not confirm mineral identity.",
        color=MUTED,
        fontsize=8,
    )
    _provenance(fig, scene)
    return _save(fig, path)

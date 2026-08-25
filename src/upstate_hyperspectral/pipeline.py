"""Reproducible analysis pipeline and human-readable output artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from upstate_hyperspectral.analysis import analyze_scene, build_summary
from upstate_hyperspectral.regions import StudyRegion
from upstate_hyperspectral.synthetic import HyperspectralScene, generate_demo_scene
from upstate_hyperspectral.visualization import (
    save_pca_clusters,
    save_spectral_signatures,
    save_study_overview,
    save_surface_proxies,
)


def run_scene_analysis(
    scene: HyperspectralScene,
    output_dir: str | Path,
    *,
    n_clusters: int = 6,
) -> dict:
    output = Path(output_dir)
    figure_dir = output / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    result = analyze_scene(scene, n_clusters=n_clusters)
    summary = build_summary(scene, result)

    figure_paths = {
        "study_area_overview": save_study_overview(scene, result, figure_dir / "study-area-overview.png"),
        "spectral_signatures": save_spectral_signatures(scene, result, figure_dir / "spectral-signatures.png"),
        "pca_clusters": save_pca_clusters(scene, result, figure_dir / "pca-clusters.png"),
        "surface_proxies": save_surface_proxies(scene, result, figure_dir / "surface-proxies.png"),
    }
    summary["figures"] = {name: str(path.relative_to(output)) for name, path in figure_paths.items()}

    summary_path = output / "analysis-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    signature_table = pd.DataFrame({"wavelength_nm": scene.wavelengths_nm})
    for label, spectrum in result.cluster_spectra.items():
        signature_table[f"cluster_{label + 1}_reflectance"] = spectrum
    signature_table["good_wavelength"] = scene.good_wavelengths
    signature_table.to_csv(output / "cluster-spectral-signatures.csv", index=False)

    return summary


def run_demo(
    region: StudyRegion,
    output_dir: str | Path,
    *,
    n_clusters: int = 6,
    seed: int = 2026,
    height: int = 154,
    width: int = 224,
) -> dict:
    scene = generate_demo_scene(region, height=height, width=width, seed=seed)
    return run_scene_analysis(scene, output_dir, n_clusters=n_clusters)

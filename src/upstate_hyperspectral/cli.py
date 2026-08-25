"""Friendly command-line entry points for demos and real NASA data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from upstate_hyperspectral.nasa import (
    download_granules,
    orthorectify_emit_subset,
    search_emit_granules,
    summarize_granules,
)
from upstate_hyperspectral.pipeline import run_demo, run_scene_analysis
from upstate_hyperspectral.regions import REGIONS, get_region


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="upstate-hyperspectral",
        description="Responsible hyperspectral surface mapping across upstate New York.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    demo = subcommands.add_parser("demo", help="Run the explicitly synthetic, no-login demonstration.")
    demo.add_argument("--region", choices=sorted(REGIONS), default="finger-lakes")
    demo.add_argument("--output-dir", default="outputs/finger-lakes")
    demo.add_argument("--clusters", type=int, default=6)
    demo.add_argument("--seed", type=int, default=2026)

    search = subcommands.add_parser("search", help="Check actual NASA EMIT coverage for a region.")
    search.add_argument("--region", choices=sorted(REGIONS), default="finger-lakes")
    search.add_argument("--start", required=True, help="Start date in YYYY-MM-DD format.")
    search.add_argument("--end", required=True, help="End date in YYYY-MM-DD format.")
    search.add_argument("--limit", type=int, default=25)
    search.add_argument("--save", type=Path, help="Optional JSON path for the scene inventory.")
    search.add_argument("--download", action="store_true", help="Download found scenes after Earthdata login.")
    search.add_argument("--download-dir", default="data/raw")

    process = subcommands.add_parser("process", help="Orthorectify and analyze a real downloaded EMIT scene.")
    process.add_argument("--input", required=True, type=Path, help="Path to an EMIT_L2A_RFL_*.nc file.")
    process.add_argument("--region", choices=sorted(REGIONS), default="finger-lakes")
    process.add_argument("--mask", type=Path, help="Optional paired EMIT_L2A_MASK_*.nc file.")
    process.add_argument("--mask-flags", default="0,1", help="Comma-separated QA flag indices; verify against product metadata.")
    process.add_argument("--output-dir", default="outputs/real-emit-scene")
    process.add_argument("--clusters", type=int, default=6)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    region = get_region(args.region)

    try:
        if args.command == "demo":
            print("Mode: SYNTHETIC DEMONSTRATION — no real NASA imagery is included.")
            print(f"Study area: {region.name}")
            summary = run_demo(region, args.output_dir, n_clusters=args.clusters, seed=args.seed)
            print(f"Output directory: {Path(args.output_dir).resolve()}")
            print(f"Valid pixels: {summary['valid_pixels']:,}")
            print(f"Exposed-surface pixels: {summary['exposed_surface_pixels']:,}")
            print(f"PCA explained variance: {summary['pca_cumulative_explained_variance']:.1%}")
            print(f"Silhouette score: {summary['silhouette_score']:.3f}")
            return 0

        if args.command == "search":
            print(f"Searching real EMIT L2A coverage for {region.name} ...")
            print(f"WGS84 bounding box: {region.bbox}")
            results = search_emit_granules(region, args.start, args.end, count=args.limit)
            inventory = summarize_granules(results)
            print(f"Matching granules: {len(results)}")
            if not results:
                print(
                    "No scene was found for this region and date range. EMIT focuses primarily "
                    "on arid regions, so lack of upstate-New-York coverage is scientifically "
                    "plausible. Try a broader search window or investigate authorized AVIRIS data."
                )
            else:
                for record in inventory:
                    print(f"- {record['granule_ur']}  |  {record['start']}")

            if args.save:
                args.save.parent.mkdir(parents=True, exist_ok=True)
                args.save.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
                print(f"Scene inventory written to {args.save}")

            if args.download and results:
                downloaded = download_granules(results, args.download_dir)
                print(f"Downloaded {len(downloaded)} file(s) to {args.download_dir}")
            return 0

        if args.command == "process":
            flags = tuple(int(value.strip()) for value in args.mask_flags.split(",") if value.strip())
            scene = orthorectify_emit_subset(args.input, region, mask_path=args.mask, mask_flags=flags)
            summary = run_scene_analysis(scene, args.output_dir, n_clusters=args.clusters)
            print(f"Analyzed real NASA observation: {args.input.name}")
            print(f"Output directory: {Path(args.output_dir).resolve()}")
            print(f"Valid pixels: {summary['valid_pixels']:,}")
            print(f"Exposed-surface pixels: {summary['exposed_surface_pixels']:,}")
            return 0

    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")

    return 1

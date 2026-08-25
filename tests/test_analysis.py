import unittest

import numpy as np

from upstate_hyperspectral.analysis import (
    analyze_scene,
    build_summary,
    continuum_band_depth,
    nearest_band_index,
    normalized_difference,
)
from upstate_hyperspectral.regions import get_region
from upstate_hyperspectral.synthetic import generate_demo_scene


class SpectralMathTests(unittest.TestCase):
    def test_normalized_difference_matches_known_values(self):
        first = np.array([0.8, 0.1, 0.0])
        second = np.array([0.2, 0.3, 0.0])
        actual = normalized_difference(first, second)
        np.testing.assert_allclose(actual[:2], [0.6, -0.5])
        self.assertTrue(np.isnan(actual[2]))

    def test_nearest_band_uses_absolute_distance(self):
        self.assertEqual(nearest_band_index(np.array([450, 550, 660, 850]), 665), 2)

    def test_invalid_absorption_window_is_rejected(self):
        scene = generate_demo_scene(get_region("finger-lakes"), height=18, width=24)
        with self.assertRaisesRegex(ValueError, "left < center < right"):
            continuum_band_depth(scene, 2200, 2300, 2400)


class SceneAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene = generate_demo_scene(get_region("finger-lakes"), height=45, width=64)
        cls.result = analyze_scene(cls.scene, n_clusters=5, max_fit_pixels=1000)

    def test_scene_has_emit_compatible_band_count(self):
        self.assertEqual(self.scene.shape, (45, 64, 285))

    def test_demo_provenance_cannot_be_confused_with_observed_data(self):
        self.assertTrue(self.scene.provenance.startswith("SYNTHETIC"))

    def test_water_is_excluded_from_cluster_map(self):
        self.assertTrue(np.all(self.result.cluster_map[self.result.water_mask] == -1))

    def test_exposed_mask_excludes_water_and_vegetation(self):
        self.assertFalse(np.any(self.result.exposed_surface_mask & self.result.water_mask))
        self.assertFalse(np.any(self.result.exposed_surface_mask & self.result.vegetation_mask))

    def test_expected_atmospheric_windows_are_removed(self):
        self.assertFalse(self.scene.good_wavelengths[nearest_band_index(self.scene.wavelengths_nm, 1400)])
        self.assertFalse(self.scene.good_wavelengths[nearest_band_index(self.scene.wavelengths_nm, 1900)])

    def test_summary_is_honest_and_consistent(self):
        summary = build_summary(self.scene, self.result)
        self.assertTrue(summary["is_synthetic"])
        self.assertEqual(summary["total_bands"], 285)
        self.assertEqual(summary["cluster_count"], 5)
        self.assertGreater(summary["valid_pixels"], 0)
        self.assertIn("not validated", summary["interpretation_note"])

    def test_at_least_two_clusters_are_required(self):
        with self.assertRaisesRegex(ValueError, "At least two"):
            analyze_scene(self.scene, n_clusters=1)


if __name__ == "__main__":
    unittest.main()

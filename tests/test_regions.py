import unittest

from upstate_hyperspectral.regions import REGIONS, get_region


class RegionTests(unittest.TestCase):
    def test_all_regions_have_valid_wgs84_bounding_boxes(self):
        for region in REGIONS.values():
            self.assertLess(region.west, region.east)
            self.assertLess(region.south, region.north)
            self.assertTrue(-180 <= region.west <= 180)
            self.assertTrue(-90 <= region.south <= 90)

    def test_geneva_is_inside_finger_lakes(self):
        self.assertTrue(get_region("finger-lakes").contains(-76.9777, 42.8689))

    def test_fredonia_is_inside_lake_erie_region(self):
        self.assertTrue(get_region("lake-erie").contains(-79.3317, 42.4401))

    def test_unknown_region_reports_available_presets(self):
        with self.assertRaisesRegex(ValueError, "finger-lakes"):
            get_region("not-a-real-region")


if __name__ == "__main__":
    unittest.main()

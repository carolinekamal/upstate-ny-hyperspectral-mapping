import unittest

from upstate_hyperspectral.nasa import (
    EMIT_REFLECTANCE_COLLECTION,
    EMIT_REFLECTANCE_SHORT_NAME,
    summarize_granules,
)


class MockGranule(dict):
    def data_links(self):
        return ["https://example.test/EMIT_L2A_RFL_example.nc"]


class NasaMetadataTests(unittest.TestCase):
    def test_collection_identifiers_match_nasa_documentation(self):
        self.assertEqual(EMIT_REFLECTANCE_COLLECTION, "C2408750690-LPCLOUD")
        self.assertEqual(EMIT_REFLECTANCE_SHORT_NAME, "EMITL2ARFL")

    def test_granule_metadata_is_extracted_without_network_access(self):
        granule = MockGranule(
            umm={
                "GranuleUR": "EMIT_L2A_RFL_test",
                "TemporalExtent": {
                    "RangeDateTime": {
                        "BeginningDateTime": "2025-07-01T12:00:00Z",
                        "EndingDateTime": "2025-07-01T12:01:00Z",
                    }
                },
            }
        )
        inventory = summarize_granules([granule])
        self.assertEqual(inventory[0]["granule_ur"], "EMIT_L2A_RFL_test")
        self.assertEqual(inventory[0]["file_count"], 1)


if __name__ == "__main__":
    unittest.main()

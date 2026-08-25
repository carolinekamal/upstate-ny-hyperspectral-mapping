"""Transparent geographic presets for upstate New York study areas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StudyRegion:
    """A WGS84 bounding box plus landmarks used for readable visualizations."""

    slug: str
    name: str
    bbox: tuple[float, float, float, float]
    description: str
    landmarks: tuple[tuple[str, float, float], ...]

    @property
    def west(self) -> float:
        return self.bbox[0]

    @property
    def south(self) -> float:
        return self.bbox[1]

    @property
    def east(self) -> float:
        return self.bbox[2]

    @property
    def north(self) -> float:
        return self.bbox[3]

    def contains(self, longitude: float, latitude: float) -> bool:
        return self.west <= longitude <= self.east and self.south <= latitude <= self.north


REGIONS: dict[str, StudyRegion] = {
    "finger-lakes": StudyRegion(
        slug="finger-lakes",
        name="Finger Lakes, New York",
        bbox=(-77.35, 42.30, -76.30, 43.08),
        description="Seneca and Cayuga lake corridors, Geneva, Ithaca, and surrounding agricultural landscapes.",
        landmarks=(
            ("Geneva", -76.9777, 42.8689),
            ("Ithaca", -76.5019, 42.4430),
            ("Watkins Glen", -76.8733, 42.3806),
            ("Penn Yan", -77.0547, 42.6609),
        ),
    ),
    "seneca-cayuga": StudyRegion(
        slug="seneca-cayuga",
        name="Seneca-Cayuga Wine Corridor, New York",
        bbox=(-77.12, 42.38, -76.45, 42.94),
        description="Focused study area around Seneca Lake, Cayuga Lake, and the Cornell AgriTech region.",
        landmarks=(
            ("Geneva", -76.9777, 42.8689),
            ("Trumansburg", -76.6661, 42.5428),
            ("Ovid", -76.8230, 42.6765),
        ),
    ),
    "lake-erie": StudyRegion(
        slug="lake-erie",
        name="Lake Erie Grape Belt, New York",
        bbox=(-79.90, 42.05, -78.72, 42.82),
        description="Chautauqua County, the Lake Erie shoreline, and the western New York grape belt.",
        landmarks=(
            ("Dunkirk", -79.3339, 42.4795),
            ("Fredonia", -79.3317, 42.4401),
            ("Westfield", -79.5781, 42.3223),
            ("Jamestown", -79.2353, 42.0970),
        ),
    ),
}


def get_region(slug: str) -> StudyRegion:
    try:
        return REGIONS[slug]
    except KeyError as exc:
        available = ", ".join(sorted(REGIONS))
        raise ValueError(f"Unknown study region {slug!r}. Choose from: {available}.") from exc

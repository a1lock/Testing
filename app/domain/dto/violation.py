from dataclasses import dataclass, field


@dataclass
class LocationDTO:
    """Exact coordinates and context snippet of a detected violation."""

    page_number: int | None = None
    paragraph_index: int | None = None
    item_title: str | None = None
    snippet: str | None = None


@dataclass
class ViolationDTO:
    """Domain model representing a single rule violation in the document."""

    rule_id: str
    message: str
    location: LocationDTO = field(default_factory=LocationDTO)
    severity: str = "WARNING"
    actual_value: str | None = None
    expected_value: str | None = None


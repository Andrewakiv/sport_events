"""Validate the documented Jolpica discovery fixtures without network access."""

import json
from pathlib import Path
from typing import Any

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "jolpica_f1_events.json"


def load_cases() -> dict[str, dict[str, Any]]:
    document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {case["name"]: case for case in document["cases"]}


def test_fixture_covers_scheduled_and_completed_non_sprint_weekends() -> None:
    cases = load_cases()

    assert set(cases) == {
        "scheduled_non_sprint_weekend",
        "completed_non_sprint_weekend",
    }
    assert all("Sprint" not in case["calendar"] for case in cases.values())

    scheduled = cases["scheduled_non_sprint_weekend"]
    assert all(
        response == {"total": "0", "Races": []} for response in scheduled["responses"].values()
    )

    completed = cases["completed_non_sprint_weekend"]
    assert completed["responses"]["qualifying"]["total"] == "20"
    assert completed["responses"]["race"]["total"] == "20"
    assert completed["responses"]["sprint"] == {"total": "0", "Races": []}


def test_fixture_preserves_provider_keys_and_optional_classification_fields() -> None:
    completed = load_cases()["completed_non_sprint_weekend"]
    calendar = completed["calendar"]
    qualifying = completed["responses"]["qualifying"]["Races"][0]
    race = completed["responses"]["race"]["Races"][0]

    assert (calendar["season"], calendar["round"]) == ("2025", "8")
    assert calendar["Circuit"]["circuitId"] == "monaco"
    assert (qualifying["season"], qualifying["round"]) == ("2025", "8")
    assert (race["season"], race["round"]) == ("2025", "8")

    qualifying_rows = qualifying["QualifyingResults"]
    assert qualifying_rows[0]["Driver"]["driverId"] == "norris"
    assert qualifying_rows[0]["Constructor"]["constructorId"] == "mclaren"
    assert "Q2" not in qualifying_rows[1]
    assert "Q3" not in qualifying_rows[1]

    race_rows = race["Results"]
    assert race_rows[0]["Time"]["millis"] == "6033843"
    assert race_rows[1]["positionText"] == "R"
    assert race_rows[1]["status"] == "Retired"
    assert "Time" not in race_rows[1]

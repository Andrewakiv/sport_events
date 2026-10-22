"""Export the backend OpenAPI document for frontend type generation."""

import json
from pathlib import Path

from sport_events.main import app


def main() -> None:
    output = Path(__file__).parent.parent / "openapi" / "sport-events.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

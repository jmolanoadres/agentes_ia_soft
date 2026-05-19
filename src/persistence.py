import json
from pathlib import Path
from typing import Any, cast


class Persistence:
    def __init__(self, path: str = "data/state.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, data: Any) -> None:
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return cast(dict[str, Any], json.loads(self.path.read_text()))

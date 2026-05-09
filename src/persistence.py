import json
from pathlib import Path

class Persistence:

    def __init__(self, path="data/state.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, data):
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def load(self):
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())
from pathlib import Path
from typing import List

import yaml

from .models import Adventure

DATA_PATH = Path(__file__).parent / "seed.yaml"


def load_adventures() -> List[Adventure]:
    with DATA_PATH.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file)

    return [Adventure(**item) for item in raw]

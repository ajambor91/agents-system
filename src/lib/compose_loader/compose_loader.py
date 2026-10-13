"""Read Compose YAML without running Docker or evaluating configuration."""
from pathlib import Path

import yaml

from ._parser import _compose
from .models import ComposeData


class ComposeLoader:
    @staticmethod
    def loadYaml(path: Path | str) -> ComposeData:
        """Read a UTF-8 file; propagate file, YAML and model-shape errors."""
        with Path(path).open("r", encoding="utf-8") as stream:
            return _compose(yaml.safe_load(stream))

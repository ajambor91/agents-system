from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from lib.configuration import Configuration

if TYPE_CHECKING:
    from .. import InstanceManager


@dataclass
class DataClass:
    configuration: Configuration
    instance_manager: InstanceManager

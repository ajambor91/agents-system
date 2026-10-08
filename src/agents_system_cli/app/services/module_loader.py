
import logging
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from ..exceptions import ApiError
from lib.modules_catalog import Module


LOGGER = logging.getLogger(__name__)


class ModuleLoader:
    def __init__(self, configuration):
        self.configuration = configuration
        self.instances: dict[str, object] = {}

    def load(self, section: Module) -> object:
        LOGGER.debug('Resolving local module')
        try:
            directory = Path(
                section.absolute_module_path
            ).expanduser().resolve(strict=True)

            main_file = directory / "__main__.py"

            if not main_file.is_file():
                raise FileNotFoundError(
                    f"Brak pliku __main__.py w {directory}"
                )

            key = str(main_file)

            if key in self.instances:
                LOGGER.debug("Using cached local module: module=%s", getattr(section, "module_name", directory.name))
                return self.instances[key]

            digest = hashlib.sha256(
                key.encode()
            ).hexdigest()

            package_name = f"agents_system_cli_module_{digest}"
            if package_name not in sys.modules:
                package = ModuleType(package_name)
                package.__path__ = [str(directory)]
                package.__package__ = package_name
                sys.modules[package_name] = package
            module_name = f"{package_name}.__main__"

            spec = importlib.util.spec_from_file_location(
                module_name,
                main_file,
            )

            if spec is None or spec.loader is None:
                raise ImportError(
                    f"Nie można załadować {main_file}"
                )

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
            except BaseException:
                sys.modules.pop(module_name, None)
                raise

            factory = getattr(
                module,
                "get_main_app",
                None,
            )

            if not callable(factory):
                raise TypeError(
                    "__main__.py musi eksportować funkcję get_main_app(config)"
                )

            instance = factory(
                self.configuration
            )

            self.instances[key] = instance
            LOGGER.info("Local module loaded: module=%s entrypoint=%s", getattr(section, "module_name", directory.name), main_file)

            return instance

        except Exception as exc:
            LOGGER.exception("Local module load failed: module=%s", getattr(section, "module_name", "unknown"))
            raise ApiError(
                f"Nie można załadować modułu "
                f"{section.module_name}: {exc}",
                exit_code=1,
            ) from exc

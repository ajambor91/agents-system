import importlib
import inspect
import keyword
import os
import sys

from pathlib import Path
from types import ModuleType
from importlib.machinery import ModuleSpec
from typing import Any


class ClassBuildError(RuntimeError):
    pass


class ClassBuilder:

    def __init__(self, class_loader):
        self.class_loader = class_loader

        self._instances: dict[str, object] = {}

    def build_class_tree(self) -> dict[str, object]:
        """
        Build application instances from discovered modules.
        """

        if self._instances:
            return self._instances.copy()

        found_classes = self.class_loader.getClasses()

        imported_classes = {}

        for module_name, module_entry in found_classes.items():

            try:
                instance = self._build_instance(
                    module_entry
                )

                imported_classes[module_name] = instance

            except Exception as exc:
                raise ClassBuildError(
                    f"Failed to build module '{module_name}': {exc}"
                ) from exc

        self._instances = imported_classes

        return self._instances.copy()

    def _build_instance(self, module_entry) -> object:
        """
        Import and instantiate an application class.
        """

        application_class = self._load_class(
            module_entry
        )

        return application_class()

    def _load_class(self, module_entry) -> type[Any]:
        """
        Load the application class using module metadata.
        """

        metadata = module_entry.meta_data

        module_dir = Path(
            os.path.expandvars(
                module_entry.absolute_module_path
            )
        ).expanduser().resolve()

        if not module_dir.is_dir():
            raise FileNotFoundError(
                f"Module directory not found: {module_dir}"
            )

        # Register the module namespace.
        namespace = self._register_namespace(
            metadata.namespace,
            module_dir
        )

        # Import the application module.
        module_path = (
            f"{namespace}.{metadata.module}"
        )
        print(f"{namespace}.{metadata.module}")
        imported_module = importlib.import_module(
            module_path
        )

        # Retrieve the application class.
        application_class = getattr(
            imported_module,
            metadata.class_name
        )

        if not inspect.isclass(application_class):
            raise TypeError(
                f"{module_path}.{metadata.class_name} "
                "is not a class"
            )

        return application_class

    @staticmethod
    def _register_namespace(
        namespace: str,
        module_dir: Path
    ) -> str:
        """
        Register an isolated Python package namespace.
        """

        if (
            not namespace.isidentifier()
            or keyword.iskeyword(namespace)
        ):
            raise ValueError(
                f"Invalid namespace: {namespace}"
            )

        package_name = (
            f"runtime_plugin_{namespace}"
        )

        if package_name in sys.modules:

            package = sys.modules[package_name]

            existing_paths = list(
                getattr(package, "__path__", [])
            )

            if existing_paths != [str(module_dir)]:
                raise RuntimeError(
                    f"Namespace collision: {package_name}"
                )

            return package_name

        package = ModuleType(package_name)

        package.__path__ = [str(module_dir)]
        package.__package__ = package_name

        package.__spec__ = ModuleSpec(
            package_name,
            loader=None,
            is_package=True
        )

        sys.modules[package_name] = package

        return package_name

    def get_instance(
        self,
        module_name: str
    ) -> object:

        return self._instances[module_name]

    def get_instances(self) -> dict[str, object]:

        return self._instances.copy()
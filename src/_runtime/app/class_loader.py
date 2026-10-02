from __future__ import annotations

from pathlib import Path

from shared.json_loader import JsonLoader

from .models.meta_data_class import MetaDataClass
from .models.module_entry import ModuleEntry


class ClassLoader:
    _META_FILE_NAME = "meta.json"

    def __init__(self, modules_list: dict) -> None:
        self._modules_list = modules_list
        self._found_classes = self._get_modules_list()

    def loadClasses(self) -> "ClassLoader":
        self._found_classes = self._get_modules_list()
        return self

    def getClasses(self) -> dict[str, ModuleEntry]:
        return self._found_classes.copy()

    def _get_modules_list(self) -> dict[str, ModuleEntry]:
        children = self._modules_list.get("children")
        if not isinstance(children, list):
            raise ValueError("Modules manifest must contain a children list")

        extracted: dict[str, ModuleEntry] = {}
        for module in children:
            runtime_methods = module.get("runtime")
            if not isinstance(runtime_methods, list) or not runtime_methods:
                continue

            module_name = module["module_name"]
            module_dir = Path(module["absolute_module_path"]).expanduser().resolve()
            metadata_path = module_dir / self._META_FILE_NAME
            if not metadata_path.is_file():
                continue
            metadata = JsonLoader.getJsonFileContent(metadata_path)
            application = metadata.get("application")
            if not isinstance(application, dict):
                raise ValueError(f"{module_dir}: missing application metadata")

            meta_class = MetaDataClass(
                namespace=metadata["namespace"],
                entrypoint=metadata["entrypoint"],
                module=application["module"],
                class_name=application["class"],
            )
            extracted[module_name] = ModuleEntry(
                absolute_module_path=str(module_dir),
                is_runtime=bool(module.get("is_runtime")),
                meta_data=meta_class,
                runtime=[str(method) for method in runtime_methods],
                module_name=module_name,
            )

        return extracted

from .instance_manager import InstanceManager


class InstanceManagerWrapper:
    def __init__(self, instance_manager: InstanceManager):
        self._instance_manager = instance_manager

    def get_instance_manager(self) -> InstanceManager:
        return self._instance_manager

    def get_running_modules(self) -> dict[str, list[dict[str, str]]]:
        """Return JSON-safe public instances currently held by the runtime."""
        instances = self._instance_manager.list_managed_instances()
        return {
            "modules": [
                {"name": item.get_class_name(), "class": item.instance_class.__name__}
                for item in sorted(instances, key=lambda item: item.get_class_name())
                if not item.get_class_name().endswith("_block")
            ]
        }

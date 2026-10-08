class ManagedInstance:
    """Pair a managed application class with its initialized instance."""

    def __init__(
        self,
        instance_object: object,
        instance_class: type,
        class_name: str,
        absolute_path: str | None = None
    ) -> None:
        self._instance_object = instance_object
        self._instance_class = instance_class
        self._class_name = class_name
        self._absolute_path = absolute_path
        self._check_self()

    @property
    def instance_object(self) -> object:
        return self._instance_object

    @property
    def instance_class(self) -> type:
        return self._instance_class

    @property
    def class_name(self) -> str:
        return self._class_name

    @property
    def absolute_path(self) -> str | None:
        return self._absolute_path
    
    def get_class_name(self) -> str:
        return self._class_name

    def _check_self(self) -> None:
        if (
            self._instance_object is None
            or self._instance_class is None
            or not self._class_name
        ):
            raise RuntimeError("ManagedInstance is not properly initialized.")

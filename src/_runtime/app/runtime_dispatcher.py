import threading

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from . import InstanceManager
from .exceptions import RuntimeDispatchError
from .models import Request

class RuntimeDispatcher:
    """
    Dispatch requests directly to managed instances.

    Every managed instance has its own single-thread executor.
    Available methods are resolved dynamically with getattr().
    """

    def __init__(
        self,
        instance_manager: InstanceManager,
    ) -> None:

        self._instance_manager = instance_manager

        self._executors: dict[
            str,
            ThreadPoolExecutor,
        ] = {}

        self._lock = threading.RLock()

        self._initialize_executors()

    def _initialize_executors(self) -> None:

        with self._lock:

            for managed_instance in (
                self._instance_manager.list_managed_instances()
            ):

                name = managed_instance.get_class_name()

                if name not in self._executors:

                    self._executors[name] = ThreadPoolExecutor(
                        max_workers=1,
                        thread_name_prefix=f"runtime-{name}",
                    )

    def refresh_instances(self) -> None:

        managed_names = {
            managed_instance.get_class_name()
            for managed_instance
            in self._instance_manager.list_managed_instances()
        }

        removed_executors: list[
            ThreadPoolExecutor
        ] = []

        with self._lock:

            for name in managed_names:

                if name not in self._executors:

                    self._executors[name] = ThreadPoolExecutor(
                        max_workers=1,
                        thread_name_prefix=f"runtime-{name}",
                    )

            removed_names = (
                set(self._executors)
                - managed_names
            )

            for name in removed_names:

                executor = self._executors.pop(
                    name
                )

                removed_executors.append(
                    executor
                )

        for executor in removed_executors:

            executor.shutdown(
                wait=False,
                cancel_futures=True,
            )

    def dispatch(
        self,
        request_obj: Request,
    ) -> Any:
        print("REQUESTSSREQUESTSSREQUESTSSREQUESTSSREQUESTSSREQUESTSSREQUESTSSREQUESTSSREQUESTSSREQUESTSSREQUESTSSREQUESTSSREQUESTSSREQUESTSSREQUESTSS")
        instance_name = request_obj.payload['module_name']

        method_name = request_obj.payload['method']



        kwargs = request_obj.payload['kwargs']

        

        if instance_name.endswith("_block"):
            raise RuntimeDispatchError(
                "SERVICE_BLOCKED",
                f"Service is not available through runtime API: "
                f"{instance_name}",
            )

        try:

            managed_instance = (
                self._instance_manager.get(
                    instance_name
                )
            )

        except KeyError as exc:

            raise RuntimeDispatchError(
                "INSTANCE_NOT_FOUND",
                f"Managed instance not found: "
                f"{instance_name}",
            ) from exc

        instance = managed_instance.instance_object

        try:

            action = getattr(
                instance,
                method_name,
            )

        except AttributeError as exc:

            raise RuntimeDispatchError(
                "METHOD_NOT_FOUND",
                f"Method not found: "
                f"{instance_name}.{method_name}",
            ) from exc

        if not callable(action):

            raise RuntimeDispatchError(
                "NOT_CALLABLE",
                f"Attribute is not callable: "
                f"{instance_name}.{method_name}",
            )

        with self._lock:

            executor = self._executors.get(
                instance_name
            )

        if executor is None:

            raise RuntimeDispatchError(
                "INSTANCE_NOT_RUNNING",
                f"Runtime executor not found for: "
                f"{instance_name}",
            )

        try:
            print(kwargs)
            print("RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR")
            future = executor.submit(
                action,
                **kwargs,
            )

            return future.result()

        except Exception as exc:

            raise RuntimeDispatchError(
                "ACTION_FAILED",
                f"Action failed: "
                f"{instance_name}.{method_name}",
                details={
                    "exception": type(exc).__name__,
                    "message": str(exc),
                },
            ) from exc

    @staticmethod
    def _validate_request(
        instance_name: Any,
        method_name: Any,
        args: Any,
        kwargs: Any,
    ) -> None:

        if not isinstance(
            instance_name,
            str,
        ):

            raise RuntimeDispatchError(
                "INVALID_SERVICE",
                "'service' must be a string",
            )

        if not isinstance(
            method_name,
            str,
        ):

            raise RuntimeDispatchError(
                "INVALID_METHOD",
                "'method' must be a string",
            )

        if not isinstance(
            args,
            list,
        ):

            raise RuntimeDispatchError(
                "INVALID_ARGS",
                "'args' must be a list",
            )

        if not isinstance(
            kwargs,
            dict,
        ):

            raise RuntimeDispatchError(
                "INVALID_KWARGS",
                "'kwargs' must be an object",
            )

    def shutdown(
        self,
        *,
        wait: bool = True,
    ) -> None:

        with self._lock:

            executors = list(
                self._executors.values()
            )

            self._executors.clear()

        for executor in executors:

            executor.shutdown(
                wait=wait,
                cancel_futures=True,
            )
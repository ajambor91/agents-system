
import logging

import threading

from concurrent.futures import ThreadPoolExecutor
from typing import Any
from ..app import Application
from .runtime_dispatch_error import RuntimeDispatchError
from .request import Request

LOGGER = logging.getLogger(__name__)


class RuntimeDispatcher:
    """
    Dispatch requests directly to managed instances.

    Every managed instance has its own single-thread executor.
    Available methods are resolved dynamically with getattr().
    """
    _executor: ThreadPoolExecutor
    def __init__(
        self,
        app: Application,
    ) -> None:

        self._app = app


        self._lock = threading.RLock()

        self._initialize_executors()

    def _initialize_executors(self) -> None:

        with self._lock:
            self._executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix=f"agent-manager-runtime",
            )

    def refresh_instances(self) -> None:

        LOGGER.debug('Starting runtime_dispatcher.refresh_instances')
        self._initialize_executors()

    def dispatch(
        self,
        request_obj: Request,
    ) -> Any:
        LOGGER.debug("Dispatching runtime request: request_id=%s", request_obj.request_id)
        method_name = request_obj.payload['method']



        kwargs = request_obj.payload['kwargs']


        try:

            action = getattr(
                self._app,
                method_name,
            )

        except AttributeError as exc:

            raise RuntimeDispatchError(
                "METHOD_NOT_FOUND",
                f"Method not found: "
                f"{method_name}",
            ) from exc

        if not callable(action):

            raise RuntimeDispatchError(
                "NOT_CALLABLE",
                f"Attribute is not callable: "
                f"{method_name}",
            )

        try:
            LOGGER.debug("Submitting runtime action: method=%s argument_names=%s", method_name, sorted(kwargs))
            future = self._executor.submit(
                action,
                **kwargs,
            )

            return future.result()

        except Exception as exc:
            LOGGER.exception("Runtime action failed: method=%s", method_name)

            raise RuntimeDispatchError(
                "ACTION_FAILED",
                f"Action failed: "
                f"{method_name}",
                details={
                    "exception": type(exc).__name__,
                    "message": str(exc),
                },
            ) from exc

    @staticmethod
    def _validate_request(
        method_name: Any,
        args: Any,
        kwargs: Any,
    ) -> None:

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

        LOGGER.debug('Starting runtime_dispatcher.shutdown')
        with self._lock:


            self._executor.shutdown(
                wait=wait,
                cancel_futures=True,
            )
from functools import wraps
from typing import (
    Awaitable,
    Callable,
    Self,
    TypeAlias,
)

from smart_rpc.errors import (
    MethodInternalError,
    UnknownMethodError,
    ValidationError,
)
from smart_rpc.ifaces import UserIface
from smart_rpc.messages import (
    Request,
    Response,
    response_from_error,
)

HandlerMethod: TypeAlias = Callable[[Request, UserIface], Awaitable[Response]]


class MessageHandler:
    methods: dict[str, HandlerMethod]

    def __init__(self) -> None:
        self.methods = {}

    def include(
        self,
        message_handler: Self,
    ) -> None:
        self.methods.update(message_handler.methods)

    def add_method(
        self,
        method_name: str,
        func: HandlerMethod,
    ) -> None:
        self.methods[method_name] = func

    def method(
        self,
        method_name: str,
    ) -> HandlerMethod:
        def decorator(func: HandlerMethod) -> HandlerMethod:
            self.add_method(
                method_name=method_name,
                func=func,
            )

            @wraps(func)
            async def wrapper(
                request: Request,
                user: UserIface,
            ) -> Response:
                return await func(
                    request,
                    user,
                )

            return wrapper
        return decorator # type:ignore[return-value]

    async def handle(
        self,
        message: bytes,
        user: UserIface,
    ) -> Response:
        try:
            request = Request.load(message)
        except ValidationError as error:
            return response_from_error(error)

        method = self.methods.get(request.method_name)
        if not method or request.method_name not in self.methods:
            return response_from_error(UnknownMethodError(request.method_name))

        try:
            return await method(request, user)
        except BaseException as error:  # noqa: BLE001
            return response_from_error(
                MethodInternalError.from_base_exception(error),
            )

from typing import (
    Any,
    Callable,
    Coroutine,
    TypeAlias,
)

SyncFunction: TypeAlias = Callable[..., Any]
AsyncFunction: TypeAlias = Callable[..., Coroutine[Any, Any, Any]]

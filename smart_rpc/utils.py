from datetime import UTC, datetime
from functools import wraps
from typing import Any

from rich import print

from smart_rpc.types import SyncFunction

AVERAGE_TEST_COUNT = 10


def time_it(
    function: SyncFunction,
) -> SyncFunction:
    @wraps(function)
    def wrapper(
        *args: list[Any],
        **kwargs: dict[str, Any],
    ) -> Any:  # noqa:ANN401
        started_at = datetime.now(tz=UTC)
        result = function(*args, **kwargs)
        finished_at = datetime.now(tz=UTC)

        duration = finished_at - started_at

        print(
            f'[turquoise4][TIME][/turquoise4] Function [bold]{function.__name__}[/bold] finished at '
            f'[medium_spring_green][bold]{duration.seconds}:{duration.microseconds}[/medium_spring_green][/bold]',
        )

        return result
    return wrapper


def compute_average_time(
    function: SyncFunction,
) -> SyncFunction:
    @wraps(function)
    def wrapper(
        *args: list[Any],
        **kwargs: dict[str, Any],
    ) -> Any:  # noqa:ANN401
        started_at = datetime.now(tz=UTC)
        result = None

        for _ in range(AVERAGE_TEST_COUNT):
            result = function(*args, **kwargs)

        finished_at = datetime.now(tz=UTC)

        duration = finished_at - started_at
        average_duration = duration / AVERAGE_TEST_COUNT

        print(
            f'[turquoise4][TIME][/turquoise4] Function [bold]{function.__name__}[/bold]:\n'
            f' - Average \t [medium_spring_green][bold]{average_duration.seconds}:'
            f'{average_duration.microseconds}[/bold][/medium_spring_green]\n'
            f' - Total \t [medium_spring_green][bold]{duration.seconds}:'
            f'{duration.microseconds}[/bold][/medium_spring_green]\n',
        )

        return result
    return wrapper


def get_class_methods(cls: object) -> list[str]:
    return [
        attribute
        for attribute in dir(cls)
        if callable(getattr(cls, attribute))
        and attribute.startswith('_') is False
    ]

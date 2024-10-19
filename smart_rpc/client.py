import asyncio
import logging
from asyncio import open_connection
from logging import getLogger
from socket import socket
from uuid import uuid4

from smart_rpc.constants import MESSAGE_SEPARATOR
from smart_rpc.errors import ClientFatalError
from smart_rpc.messages import Request, Response


class BaseClient:
    host: str
    port: int
    server: socket
    max_message_size: int
    timeout_ms: int

    locking_event: asyncio.Event

    writer: asyncio.StreamWriter
    reader: asyncio.StreamReader
    logger: logging.Logger

    def __init__(
        self,
        host: str,
        port: int,
        max_message_size: int = 20,  # 1 MB
        timeout_ms: int = 5000,  # 5 second
    ) -> None:
        self.host = host
        self.port = port
        self.max_message_size = max_message_size
        self.timeout_ms = timeout_ms

        self.locking_event = asyncio.Event()
        self.logger = getLogger(self.__class__.__name__)

    async def connect(self) -> None:
        try:
            self.reader, self.writer = await open_connection(
                host=self.host,
                port=self.port,
            )
        except ConnectionRefusedError as error:
            raise ClientFatalError.from_base_exception(error) from error

    async def send(self, request: Request) -> Response:
        request.trace_id = str(uuid4())

        await self.locking_event.wait()
        self.locking_event.set()

        self.writer.write(request.dump() + MESSAGE_SEPARATOR)
        await self.writer.drain()
        data = await self.reader.readuntil(MESSAGE_SEPARATOR)

        self.locking_event.clear()

        return Response.load(data[:-1])


if __name__ == '__main__':
    from rich import print

    from smart_rpc.examples import (
        ExampleRequest,
        ExampleResponse,
        example_request_values,
    )


    class Client(BaseClient):
        async def first_method(self, send_this: str) -> ExampleResponse:
            request = ExampleRequest(
                method_name='first_method',
                payload={
                    **example_request_values,
                    'send_this': send_this,
                },
            )

            return await self.send(request)  # type:ignore[return-value]

    client = Client(
        host='127.0.0.1',
        port=7777,
    )

    async def main() -> None:
        await client.connect()

        response = await client.first_method(
            send_this='back',
        )
        print(response)

    asyncio.run(main())

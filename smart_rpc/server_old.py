import asyncio
import logging
import socket
import sys
from asyncio import run
from typing import Any, Type

from smart_rpc.constants import MESSAGE_SEPARATOR
from smart_rpc.errors import MaxMessageSizeReceivedError, ExternalError, ServerFatalError, BaseError, \
    handle_error
from smart_rpc.examples import ExampleRequest, ExampleResponse
from smart_rpc.ifaces import UserIface
from smart_rpc.message_hander import MessageHandler
from smart_rpc.messages import Response, response_from_error, Request
from smart_rpc.user import User

CLIENT_CHECK_MESSAGE = b'heartbeat'


class Server:
    message_handler: MessageHandler
    user_class: Type[UserIface]

    host: str
    port: int
    heartbeat_s: float
    chunk_size: int
    max_message_size: int
    log_level: int
    log_messages: bool

    socket: socket.socket
    clients: dict[str, Any]
    logger: logging.Logger


    def __init__(
        self,
        host: str,
        port: int,
        message_handler: MessageHandler,
        *,
        user_class: Type[UserIface] = User,
        heartbeat_ms: int = 1 * 1000,  # 1 times per second
        chunk_size: int = 2**10,  # 1 KB
        max_message_size: int = 2**20,  # 1 MB
        log_level: int = logging.INFO,
        log_messages: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.message_handler = message_handler
        self.user_class = user_class

        self.heartbeat_s = heartbeat_ms / 1000
        self.chunk_size = chunk_size
        self.max_message_size = max_message_size
        self.log_level = log_level
        self.log_messages = log_messages

        self.clients = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def _handle_error(self, error: BaseError) -> None:
        return handle_error(
            log_level=self.log_level,
            error=error,
            logger=self.logger,
            exit_if_fatal=True,
        )

    def _send_response(self, client_address: str, message: Response) -> None:
        if client_address not in self.clients:
            return

        self.logger.debug(f"{client_address}: {message}")

        try:
            self.clients[client_address].socket.send(message.dump()+MESSAGE_SEPARATOR)
        except BrokenPipeError:
            self.logger.warning(f"{client_address}: Broken pipe")
            return

    def _send_error(self, client_address: str, error: ExternalError) -> None:
        return self._send_response(
            client_address,
            message=response_from_error(error)
        )

    async def _handle_data(self, client_address: str) -> None:
        client = self.clients[client_address]
        loop = asyncio.get_event_loop()

        message_size = 0
        message = bytes()

        while True:
            try:
                data, _ = await loop.so(client.client_socket, self.chunk_size)
            except ConnectionResetError:
                self._disconnect_client(client_address)
                break

            if not data:
                print(111)
                continue

            message_size += len(data)

            if message_size > self.max_message_size:
                self._send_error(
                    client_address=client_address,
                    error=MaxMessageSizeReceivedError(
                        max_message_size=self.max_message_size,
                    ),
                )
                message, message_size = bytes(), 0
                continue

            message += data

            if message[-1] == ord(MESSAGE_SEPARATOR):
                await self.message_handler.handle(
                    message=message[0:-1],
                    user=client,
                )
                message, message_size = bytes(), 0
                continue

            continue

    async def _handle_client(
        self,
        client: socket.socket,
    ) -> None:
        peer_name = client.getpeername()
        address = f'{peer_name[0]}:{peer_name[1]}'

        if address not in self.clients:
            self.clients[address] = self.user_class(client)

        self.logger.debug(f'Client {address} connected')

        await asyncio.create_task(self._handle_data(address))

    async def _serve(self) -> None:
        loop = asyncio.get_event_loop()

        while True:
            client, _ = await loop.sock_accept(self.socket)
            await loop.create_task(self._handle_client(client))

    async def _connect(self) -> None:
        self.logger.info(f'Starting server on {self.host}:{self.port}')
        self.logger.info(f'Methods: {list(self.message_handler.methods.keys())}')

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind((self.host, self.port))
            self.socket.listen(8)
            self.socket.setblocking(False)

        except OSError as error:
            raise ServerFatalError.from_base_exception(error)

        self.logger.info('Server started')

    def _disconnect_client(self, address: str) -> None:
        if address not in self.clients:
            return

        self.clients[address].client_socket.close()

        self.clients.pop(address)
        self.logger.debug(f'Client {address} disconnected')

    def _exit(self) -> None:
        self.logger.info('Exiting')

        for client in self.clients.values():
            client.client_socket.close()

        self.socket.close()

    async def _check_clients(self) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_s)

            for address in list(self.clients):
                if self.clients[address].client_socket.fileno() == -1:
                    self._disconnect_client(address)

                try:
                    self.clients[address].client_socket.send(CLIENT_CHECK_MESSAGE)
                except BrokenPipeError:
                    self._disconnect_client(address)

    async def _run(self) -> None:
        await self._connect()

        await asyncio.gather(
            self._serve(),
            self._check_clients(),
        )

    async def run(self) -> None:
        try:
            await self._run()
        except (KeyboardInterrupt, asyncio.CancelledError) as error:
            self.logger.error(error)
            self._exit()
        except ServerFatalError as error:
            self.logger.error(error)
            self.logger.info('Try to use another host and port.')
            self._exit()


if __name__ == '__main__':
    from rich.logging import RichHandler
    from rich import print

    logging.basicConfig(
        level="DEBUG",
        datefmt="[%X]",
        format="%(message)s",
        handlers=[
            RichHandler(
                omit_repeated_times=False,
                show_level=True,
                rich_tracebacks=True,
            ),
        ],
    )

    handler = MessageHandler()

    @handler.method("first_method")
    async def first_method(
        request: ExampleRequest,
        user: User,
    ) -> ExampleResponse:
        response = ExampleResponse(
            method_name=request.method_name,
            success=True,
            trace_id=request.trace_id,
            payload={
                "some_param": "json",
                **request.payload.model_dump(),
            },
            headers={
                'trace_id': request.trace_id,
            },
        )

        return response

    srv = Server(
        host='127.0.0.1',
        port=7777,
        log_level=logging.DEBUG,
        log_messages=True,
        message_handler=handler,
    )

    run(srv.run())

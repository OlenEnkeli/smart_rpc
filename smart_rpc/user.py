from socket import socket

from smart_rpc.ifaces import UserIface


class User(UserIface):
    client_socket: socket

    def __init__(self, client_socket: socket) -> None: # typing:ignore[valid-type]
        self.client_socket = client_socket

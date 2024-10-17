from abc import ABC, abstractmethod
from socket import socket


class UserIface(ABC):
    @abstractmethod
    def __init__(self, client: socket) -> None:
        ...

from uuid import UUID

MESSAGE_SEPARATOR = b'\x1a'
ZERO_TRACE_ID = str(UUID(int=0))
CLIENT_HEARTBEAT_MESSAGE = b'heartbeat'

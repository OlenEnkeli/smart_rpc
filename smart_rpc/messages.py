import logging
from typing import (
    Any,
    Self,
    Type,
)
from uuid import uuid4

import orjson
from pydantic import ValidationError as PydanticValidationError

from smart_rpc.constants import ZERO_TRACE_ID
from smart_rpc.errors import ExternalError, ValidationError
from smart_rpc.schema import BaseHeadersSchema, BasePayloadSchema
from smart_rpc.utils import compute_average_time


class Request:
    method_name: str
    trace_id: str
    payload: BasePayloadSchema
    headers: BaseHeadersSchema

    class PayloadSchema(BasePayloadSchema):
        ...

    class HeadersSchema(BaseHeadersSchema):
        ...

    @property
    def headers_schema(self) -> Type[BaseHeadersSchema]:
        return BaseHeadersSchema

    def __init__(
        self,
        method_name: str,
        trace_id: str | None = None,
        payload: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> None:
        payload = payload or {}
        headers = headers or {}

        self.method_name = method_name

        self.trace_id = trace_id or str(uuid4())
        headers['trace_id'] = self.trace_id

        try:
            self.payload = self.PayloadSchema.model_validate(payload)
            self.headers = self.HeadersSchema.model_validate(headers)
        except PydanticValidationError as error:
            raise ValidationError.from_base_exception(error) from error

    @classmethod
    def load(cls, data: bytes | str) -> Self:
        message = data if isinstance(data, str) else data.decode('utf-8')

        payload_start_at = message.find('{')
        headers_start_at = message.find('{', payload_start_at + 1)

        if (
            payload_start_at in (-1, 0)
            or headers_start_at in (-1, 0)
            or payload_start_at >= headers_start_at
        ):
            raise ValidationError(
                details={
                    'invalid_message_format': 'please check smart_rpc request/response format documentation',
                },
            )

        method_name = message[0:payload_start_at]

        try:
            payload = orjson.loads(message[payload_start_at:headers_start_at])
            headers = orjson.loads(message[headers_start_at:])
        except orjson.JSONDecodeError as error:
            raise ValidationError.from_base_exception(error) from error

        trace_id = headers.get('trace_id', None)

        return cls(
            method_name=method_name,
            payload=payload,
            headers=headers,
            trace_id=trace_id,
        )

    def dump(self) -> bytes:
        payload = orjson.dumps(self.PayloadSchema.model_dump(self.payload))
        headers = orjson.dumps(self.HeadersSchema.model_dump(self.headers))

        return b''.join([
            self.method_name.encode('utf-8'),
            payload,
            headers,
        ])

    @classmethod
    def find_method_name(cls, data: bytes | str) -> str:
        message = data if isinstance(data, str) else data.decode('utf-8')

        payload_start_at = message.find('{')
        if (
            payload_start_at in (-1, 0)
        ):
            raise ValidationError(
                details={
                    'invalid_message_format': 'please check smart_rpc request/response format documentation',
                },
            )

        return message[0:payload_start_at]

    def __str__(self) -> str:
        return f'Request <{self.method_name}: {self.trace_id}>'


class Response:
    method_name: str
    trace_id: str
    payload: BasePayloadSchema
    headers: BaseHeadersSchema
    success: bool

    class PayloadSchema(BasePayloadSchema):
        ...

    class HeadersSchema(BaseHeadersSchema):
        ...

    def __init__(
        self,
        method_name: str,
        trace_id: str,
        *,
        success: bool,
        payload: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> None:
        self.method_name = method_name
        self.trace_id = trace_id
        self.success = success

        payload = payload or {}
        headers = headers or {}

        try:
            self.payload = self.PayloadSchema.model_validate(payload)
            self.headers = self.HeadersSchema.model_validate(headers)
        except PydanticValidationError as error:
            raise ValidationError.from_base_exception(error) from error

    @classmethod
    def load(cls, data: bytes | str) -> Self:
        message = data if isinstance(data, str) else data.decode('utf-8')

        success_start_at = message.find(':')
        payload_start_at = message.find('{', success_start_at + 1)
        headers_start_at = message.find('{', payload_start_at + 1)

        if (
            payload_start_at in (-1, 0)
            or success_start_at in (-1, 0)
            or headers_start_at in (-1, 0)
            or success_start_at >= headers_start_at
            or payload_start_at >= headers_start_at
        ):
            raise ValidationError(
                details={
                    'invalid_message_format': 'please check smart_rpc request/response format documentation',
                },
            )

        method_name = message[0:success_start_at]
        success = (message[success_start_at+1:payload_start_at] == 'ok')
        payload = orjson.loads(message[payload_start_at:headers_start_at])
        headers = orjson.loads(message[headers_start_at:])

        if not (trace_id := headers.get('trace_id')):
            raise ValidationError(
                details={
                    'trace_id': 'must be set',
                },
            )

        return cls(
            method_name=method_name,
            trace_id=trace_id,
            success=success,
            payload=payload,
            headers=headers,
        )

    def dump(self) -> bytes:
        payload = orjson.dumps(self.PayloadSchema.model_dump(self.payload))
        headers = orjson.dumps(self.HeadersSchema.model_dump(self.headers))
        success = b'ok' if self.success else b'err'

        return b''.join([
            self.method_name.encode('utf-8'),
            b':',
            success,
            payload,
            headers,
        ])

    def __str__(self) -> str:
        return f'Response[{'ok' if self.success else 'err'}] <{self.method_name}: {self.trace_id}>'


def response_from_error(
    error: ExternalError,
    request: Request | None = None,
) -> Response:
    return Response(
        method_name=(
            request.method_name
            if request
            else (
                '__error'
                if error.log_level in (logging.CRITICAL, logging.ERROR)
                else '__warning'
            )
        ),
        trace_id=request.trace_id if request else ZERO_TRACE_ID,
        success=False,
        payload={
            'error_code': error.error_code,
            'details': error.details,
        },
    )


if __name__ == '__main__':
    from rich import print

    from smart_rpc.examples import ExampleRequest, ExampleResponse

    EXAMPLE_REQUEST = (
        b'function_name'
        b'{"send_this": "back"}'
        b'{"trace_id": "d948790a-5e67-471f-8bd0-ec212c4b8acc", "another_param": "param_value"}'
    )

    EXAMPLE_RESPONSE = (
        b'function_name:ok'
        b'{"some_param": "example", "send_this": "back"}'
        b'{"trace_id": "d948790a-5e67-471f-8bd0-ec212c4b8acc", "another_param": "param_value"}'
    )

    @compute_average_time
    def compute_load_time() -> tuple[Request, Response]:
        return (
            ExampleRequest.load(EXAMPLE_REQUEST),
            ExampleResponse.load(EXAMPLE_RESPONSE),
        )

    req, resp = compute_load_time()
    print(req)
    print(resp, '\n')

    @compute_average_time
    def compute_dump_time(request: ExampleRequest, response: ExampleResponse) -> tuple[bytes, bytes]:
        return (
            request.dump(),
            response.dump(),
        )

    dumped_req, dumped_resp = compute_dump_time(req, resp)

    print(dumped_req, dumped_resp, sep='\n')

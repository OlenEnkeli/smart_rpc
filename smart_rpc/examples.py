from smart_rpc.messages import Request, Response
from smart_rpc.schema import BasePayloadSchema


class ExampleRequest(Request):
    class PayloadSchema(BasePayloadSchema):
        send_this: str


class ExampleResponse(Response):
    class PayloadSchema(BasePayloadSchema):
        some_param: str
        send_this: str

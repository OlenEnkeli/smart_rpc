from datetime import UTC, datetime
from enum import Enum

from smart_rpc.messages import Request, Response
from smart_rpc.schema import BasePayloadSchema, BaseSchema


class SomeEnum(str, Enum):
    FIRST = 'first'
    SECOND = 'second'
    THIRD = 'third'


class SomeObjectSchema(BaseSchema):
    string_field: str
    enum_field: SomeEnum
    datetime_field: datetime
    float_field: float
    int_field: int
    bool_field: bool


class ExampleRequest(Request):
    class PayloadSchema(BasePayloadSchema):
        send_this: str
        object_field: SomeObjectSchema


class ExampleResponse(Response):
    class PayloadSchema(BasePayloadSchema):
        some_param: str
        send_this: str
        object_field: SomeObjectSchema


example_request_values = {
    'send_this': 'back',
    'object_field': {
        'string_field': 'hello world',
        'enum_field': SomeEnum.SECOND,
        'datetime_field': datetime.now(tz=UTC),
        'float_field': 4.17,
        'int_field': 42229,
        'bool_field': True,
    },
}

example_response_values = {
    'some_param': 'test',
    **example_request_values,
}

example_rpc_annotation = {
  'enums': {
    'TypeEnum': {
      'SIMPLE': 'simple',
      'EXTENDED': 'extended',
    },
  },

  'objects': {
    'Child': {
      'id': ['int', 'string'],
      'uuid': 'uuid',
    },
  },

  'methods': {
    'sample_method': {
      'request': {
        'name': 'string',
        'type': 'TypeEnum',
        'children': ['Child'],
        'main_day': ['date', 'null'],
        'selected_days': [['date', 'datetime'], 'null'],
        'updated_at': ['datetime', 'null'],
        'is_active': 'boolean',
      },

      'response': {
        'id': ['int', 'string'],
        'uuid': 'uuid',
        'created_at': 'datetime',
      },
    },
  },
}

# SmartRPC Annotation

## About

...

## Types

### Primitive Types

 - `integer`
 - `float`
 - `boolean`
 - `string`
 - `uuid`
 - `date`
 - `datetime`

### Nested Objects

...

### Enums

...

## Main structures

### Example annotation

```json
{
  "enums": {
    "TypeEnum": {
      "SIMPLE": "simple",
      "EXTENDED": "extended"
    }
  },

  "objects": {
    "Child": {
      "id": ["int", "string"],
      "uuid": "uuid"
    }
  },

  "methods": {
    "sample_method": {
      "request": {
        "name": "string",
        "type": "TypeEnum",
        "children": ["Child"],
        "main_day": ["date", "null"],
        "selected_days": [["date", "datetime"], "null"],
        "days_custom_names": {
          "days": "string"
        },
        "updated_at": ["datetime", "null"],
        "is_active": "boolean"
      },
      "response": {
        "id": ["int", "string"],
        "uuid": "uuid",
        "created_at": "datetime"
      }
    }
  }
}
```


RECORD_SCHEMA = {
    "type": "object",
    "properties": {
        "id":    {"type": "integer"},
        "name":  {"type": "string",  "minLength": 1},
        "age":   {"type": "integer", "minimum": 0, "maximum": 150},
        "email": {"type": "string",  "minLength": 1},
        "city":  {"type": "string",  "minLength": 1},
    },
    "required": ["id", "name", "age", "email", "city"],
    "additionalProperties": False,
}

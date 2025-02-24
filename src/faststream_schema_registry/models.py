from dataclasses import dataclass
from enum import Enum

from dataclasses_avroschema.pydantic import AvroBaseModel


class SchemaType(Enum):
    Avro = "AVRO"
    Json = "JSON"


class AvroMessage(AvroBaseModel):
    class Meta:
        namespace = ""
        major_version = 1


@dataclass
class SchemaInfo:
    subject: str
    schema_str: str
    schema_obj: dict

    @classmethod
    def from_message(cls, msg: AvroMessage, schema_type: SchemaType):
        schema_get = {
            SchemaType.Json: ("model_json_schema", {"mode": "validation"}),
            SchemaType.Avro: ("avro_schema_to_python", {}),
        }
        func, kwargs = schema_get[schema_type]
        schema = msg.__getattr__(func)(**kwargs)
        subject = schema["name"]

        if "namespace" in schema:
            subject = f"{schema['namespace']}.{['name']}"

        return cls(subject=subject, schema_str=str(schema), schema_obj=schema)

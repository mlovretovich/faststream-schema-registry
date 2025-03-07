import json
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from dataclasses_avroschema import AvroModel
from faststream.broker.message import StreamMessage
from schema_registry.client import (
    AsyncSchemaRegistryClient,
    schema as client_schema,
)
from schema_registry.client.schema import AvroSchema, BaseSchema, JsonSchema
from schema_registry.serializers import (
    AsyncAvroMessageSerializer,
    AsyncMessageSerializer,
)
from schema_registry.serializers import (
    AsyncJsonMessageSerializer,
)


class SchemaType(Enum):
    Avro = "AVRO"
    Json = "JSON"


@dataclass
class SchemaInfo:
    subject: str
    schema_str: str
    schema_obj: BaseSchema

    @classmethod
    def from_message(cls, msg: AvroModel, schema_type: SchemaType):
        schema_get = {
            SchemaType.Json: (
                "model_json_schema",
                {"mode": "validation"},
                JsonSchema,
            ),
            SchemaType.Avro: ("avro_schema_to_python", {}, AvroSchema),
        }

        func, kwargs, schema_transformer = schema_get[schema_type]
        schema = msg.__getattribute__(func)(**kwargs)
        subject = msg.get_fullname()

        return cls(
            subject=subject,
            schema_str=json.dumps(schema),
            schema_obj=schema_transformer(schema),
        )


class BaseSchemaRegistry(ABC):
    "A base Schema Registry classs"

    schema_type: SchemaType

    def __init__(self, url: str):
        self.schema_registry_client = AsyncSchemaRegistryClient(url)

    @property
    @abstractmethod
    def serializer(self) -> AsyncMessageSerializer: ...

    def _get_schema_from_message(
        self, msg: AvroModel
    ) -> typing.Tuple[str, str, client_schema.BaseSchema]:
        schema_get = {
            SchemaType.Json: (
                "model_json_schema",
                {"mode": "validation"},
                client_schema.JsonSchema,
            ),
            SchemaType.Avro: (
                "avro_schema_to_python",
                {},
                client_schema.AvroSchema,
            ),
        }

        func, kwargs, schema_transformer = schema_get[self.schema_type]
        schema = msg.__getattribute__(func)(**kwargs)
        subject = msg.get_fullname()
        schema_str = json.dumps(schema)
        schema_obj = schema_transformer(schema)

        return subject, schema_str, schema_obj

    async def serialize(self, msg: AvroModel, **options):
        schema_info = SchemaInfo.from_message(msg, self.schema_type)

        message_encoded = await self.serializer.encode_record_with_schema(
            schema_info.subject, schema_info.schema_obj, msg.to_dict()
        )
        schema_id = int.from_bytes(
            message_encoded[1:5], byteorder="big", signed=False
        )
        new_headers = {
            "schema-id": str(schema_id),
            "subject": schema_info.subject,
        }
        headers = options.get("headers", {})
        if headers:
            headers.update(new_headers)
        else:
            headers = new_headers

        return message_encoded, headers

    async def deserialize(
        self, msg: StreamMessage[typing.Any]
    ) -> StreamMessage[typing.Any]:
        decoded_message = await self.serializer.decode_message(msg.body)
        msg._decoded_body = decoded_message
        return msg


class AvroSchemaRegistry(BaseSchemaRegistry):
    "Schema Registry for Avro schemas"

    schema_type = SchemaType.Avro

    @property
    def serializer(self) -> AsyncAvroMessageSerializer:
        return AsyncAvroMessageSerializer(
            schemaregistry_client=self.schema_registry_client
        )


class JsonSchemaRegistry(BaseSchemaRegistry):
    "Schema Registry for Json schemas"

    schema_type = SchemaType.Json

    @property
    def serializer(self) -> AsyncJsonMessageSerializer:
        return AsyncJsonMessageSerializer(
            schemaregistry_client=self.schema_registry_client
        )

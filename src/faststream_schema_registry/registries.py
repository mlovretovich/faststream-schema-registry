import json
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from dataclasses_avroschema.pydantic import AvroBaseModel
from faststream.broker.message import StreamMessage
from schema_registry.client import AsyncSchemaRegistryClient
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
    def from_message(cls, msg: AvroBaseModel, schema_type: SchemaType):
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
        self, msg: AvroBaseModel
    ) -> typing.Tuple[str, str, BaseSchema]:
        subject = msg.get_fullname()

        match self.schema_type:
            case SchemaType.Json:
                schema = msg.model_json_schema(mode="validation")
                return subject, json.dumps(schema), JsonSchema(schema)

            case SchemaType.Avro:
                schema = msg.avro_schema_to_python()
                return subject, json.dumps(schema), AvroSchema(schema)
            case _:
                print("got here")

    async def serialize(
        self, msg: AvroBaseModel, **options
    ) -> typing.Tuple[bytes, dict[str, str]]:
        subject, schema_str, schema_obj = self._get_schema_from_message(msg)

        message_encoded = await self.serializer.encode_record_with_schema(
            subject, schema_obj, msg.to_dict()
        )
        schema_id = int.from_bytes(
            message_encoded[1:5], byteorder="big", signed=False
        )

        headers = options.get("headers") or {}
        headers["schema-id"] = str(schema_id)
        headers["subject"] = subject

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

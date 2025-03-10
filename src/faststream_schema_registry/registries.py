import json
import typing
from abc import ABC, abstractmethod
from enum import Enum

from dataclasses_avroschema.pydantic import AvroBaseModel
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


class BaseSchemaRegistry(ABC):
    _schema_type: SchemaType

    def __init__(self, url: str):
        """
        Args:
            url (str): URL of the Confluent Schema Registry API.
        """
        self._schema_registry_client = AsyncSchemaRegistryClient(url)

    @property
    @abstractmethod
    def _serializer(self) -> AsyncMessageSerializer: ...

    def _get_schema_from_message(
        self, msg: AvroBaseModel
    ) -> typing.Tuple[str, str, BaseSchema]:
        subject = msg.get_fullname()

        match self._schema_type:
            case SchemaType.Json:
                schema = msg.model_json_schema(mode="validation")
                return subject, json.dumps(schema), JsonSchema(schema)

            case SchemaType.Avro:
                schema = msg.avro_schema_to_python()
                return subject, json.dumps(schema), AvroSchema(schema)
            case _:
                raise ("got here")

    async def serialize(
        self, msg: AvroBaseModel, **options
    ) -> typing.Tuple[bytes, dict[str, str]]:
        """
        Serialize Method

        Args:
            msg (AvroBaseModel): Avrobase

        Returns:
            bytes: encoded_message
            dict: dictionary of headers with schema-id, subject keys injected

        """
        subject, schema_str, schema_obj = self._get_schema_from_message(msg)

        message_encoded = await self._serializer.encode_record_with_schema(
            subject, schema_obj, msg.to_dict()
        )
        schema_id = int.from_bytes(
            message_encoded[1:5], byteorder="big", signed=False
        )

        headers = options.get("headers") or {}
        headers["schema-id"] = str(schema_id)
        headers["schema-subject"] = subject

        return message_encoded, headers

    async def deserialize(
        self, msg: typing.Union[bytes, typing.Any]
    ) -> dict[str, typing.Any]:
        """
        Decode the serialized message into a object using it's schema

        Args:
            msg (StreamMessage[typing.Any]): StreamMessage object with
            encoded payload #ignore E501

        Returns:
            dict: The StreamMessage with the payload decoded
        """

        decoded_message = await self._serializer.decode_message(msg)
        return decoded_message


class AvroSchemaRegistry(BaseSchemaRegistry):
    """
    Schema Registry for Avro schemas

    !!! Example
        ```python
        from faststream_schema_registry.registries import AvroSchemaRegistry
        from dataclasses_avroschema.pydantic import AvroBaseModel

        registry = AvroSchemaRegistry(url="http://127.0.0.1:8081")

        class User(AvroBaseModel):
            id: int
            first_name: str
            last_name: str
            age: int

            class Meta:
                namespace = "com.example.avro"

        user = User(id=1, first_name="John", last_name="Doe", age=21)

        msg, headers = await registry.serialize(user)
        msg, headers
        >>> (b'\x00\x00\x00\x00\x02\x02\x08John\x06Doe*',
        {'schema-id': '2', 'schema-subject': 'User'})

        decoded = await registry.deserialize(msg)
        decoded
        >>> {'id': 1, 'first_name': 'John', 'last_name': 'Doe', 'age': 21}
        User(**decoded)
        >>> User(id=1, first_name='John', last_name='Doe', age=21)
        ```
    """

    _schema_type = SchemaType.Avro

    @property
    def _serializer(self) -> AsyncAvroMessageSerializer:
        return AsyncAvroMessageSerializer(
            schemaregistry_client=self._schema_registry_client
        )


class JsonSchemaRegistry(BaseSchemaRegistry):
    """
    Schema Registry for Json schemas

    !!! Example
        ```python
        from faststream_schema_registry.registries import JsonSchemaRegistry
        from dataclasses_avroschema.pydantic import AvroBaseModel

        registry = JsonSchemaRegistry(url="http://127.0.0.1:8081")

        class User(AvroBaseModel):
            id: int
            first_name: str
            last_name: str
            age: int

            class Meta:
                namespace = "com.example.json"

        user = User(id=1, first_name="John", last_name="Doe", age=21)

        msg, headers = await registry.serialize(user)
        msg, headers
        >>> (b'\x00\x00\x00\x00\x03{"id": 1, "first_name": "John", "last_name": "Doe", "age": 21}',
        {'schema-id': '3', 'schema-subject': 'com.example.json.User'})

        decoded = await registry.deserialize(msg)
        decoded
        >>> {'id': 1, 'first_name': 'John', 'last_name': 'Doe', 'age': 21}
        User(**decoded)
        >>> User(id=1, first_name='John', last_name='Doe', age=21)
        ```
    """

    _schema_type = SchemaType.Json

    @property
    def _serializer(self) -> AsyncJsonMessageSerializer:
        return AsyncJsonMessageSerializer(
            schemaregistry_client=self._schema_registry_client
        )

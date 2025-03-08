import json
from unittest.mock import patch

import pytest
from dataclasses_avroschema.pydantic import AvroBaseModel
from schema_registry.client.schema import AvroSchema, JsonSchema
from schema_registry.client import AsyncSchemaRegistryClient
from schema_registry.serializers import (
    AsyncAvroMessageSerializer,
    AsyncJsonMessageSerializer,
)
import io
import typing
from faststream_schema_registry.registries import (
    SchemaType,
    SchemaInfo,
    AvroSchemaRegistry,
    JsonSchemaRegistry,
)

import struct


@pytest.fixture
def message():
    class Message(AvroBaseModel):
        message_id: int
        message_text: str

    return Message(message_id=1, message_text="testing")


@pytest.fixture
def message_with_namespace():
    class MessageWithNamespace(AvroBaseModel):
        message_id: int
        message_text: str

        class Meta:
            namespace = "com.testing"

    return MessageWithNamespace(message_id=1, message_text="testing")


class ContextStringIO(io.BytesIO):
    """Wrapper to allow use of StringIO via 'with' constructs."""

    def __enter__(self) -> "ContextStringIO":
        return self

    def __exit__(self, *args: typing.Any) -> None:
        self.close()


def test_schema_info_from_message(message):
    avro_schema = SchemaInfo.from_message(message, SchemaType.Avro)
    json_schema = SchemaInfo.from_message(message, SchemaType.Json)
    assert avro_schema.subject == "Message"
    assert avro_schema.schema_str == json.dumps(
        message.avro_schema_to_python()
    )
    assert json_schema.subject == "Message"
    assert json_schema.schema_str == json.dumps(
        message.model_json_schema(mode="validation")
    )
    assert json_schema.schema_obj == JsonSchema(
        message.model_json_schema(mode="validation")
    )


def test_schema_info_from_message_with_namespace(message_with_namespace):
    avro_schema = SchemaInfo.from_message(
        message_with_namespace, SchemaType.Avro
    )
    json_schema = SchemaInfo.from_message(
        message_with_namespace, SchemaType.Json
    )
    assert avro_schema.subject == "com.testing.MessageWithNamespace"
    assert avro_schema.schema_str == json.dumps(
        message_with_namespace.avro_schema_to_python()
    )
    assert avro_schema.schema_obj == AvroSchema(
        message_with_namespace.avro_schema_to_python()
    )

    assert json_schema.schema_str == json.dumps(
        message_with_namespace.model_json_schema(mode="validation")
    )
    assert json_schema.subject == "com.testing.MessageWithNamespace"
    assert json_schema.schema_obj == JsonSchema(
        message_with_namespace.model_json_schema(mode="validation")
    )


@patch.object(AsyncAvroMessageSerializer, "encode_record_with_schema")
async def test_avro_schema_registry(
    encode_record_with_schema, message_with_namespace
):
    avro_schema = SchemaInfo.from_message(
        message_with_namespace, SchemaType.Avro
    )

    registry = AvroSchemaRegistry(url="http://localhost:9999")

    with ContextStringIO() as outf:
        # Write the magic byte and schema ID in network byte order (big endian)
        outf.write(struct.pack(">bI", 0, 1))

        encoded_message = outf.getvalue()

    encode_record_with_schema.return_value = encoded_message

    return_value, headers = await registry.serialize(message_with_namespace)

    assert isinstance(
        registry.schema_registry_client, AsyncSchemaRegistryClient
    )
    assert isinstance(registry.serializer, AsyncAvroMessageSerializer)
    encode_record_with_schema.assert_called_once_with(
        avro_schema.subject,
        avro_schema.schema_obj,
        message_with_namespace.to_dict(),
    )
    assert headers["schema-id"] == "1"
    assert headers["subject"] == "com.testing.MessageWithNamespace"


@patch.object(AsyncJsonMessageSerializer, "encode_record_with_schema")
async def test_json_schema_registry(
    encode_record_with_schema, message_with_namespace
):
    json_schema = SchemaInfo.from_message(
        message_with_namespace, SchemaType.Json
    )

    registry = JsonSchemaRegistry(url="http://localhost:9999")

    with ContextStringIO() as outf:
        # Write the magic byte and schema ID in network byte order (big endian)
        outf.write(struct.pack(">bI", 0, 1))

        encoded_message = outf.getvalue()

    encode_record_with_schema.return_value = encoded_message

    return_value, headers = await registry.serialize(message_with_namespace)

    assert isinstance(
        registry.schema_registry_client, AsyncSchemaRegistryClient
    )
    assert isinstance(registry.serializer, AsyncJsonMessageSerializer)
    encode_record_with_schema.assert_called_once_with(
        json_schema.subject,
        json_schema.schema_obj,
        message_with_namespace.to_dict(),
    )
    assert headers["schema-id"] == "1"
    assert headers["subject"] == "com.testing.MessageWithNamespace"

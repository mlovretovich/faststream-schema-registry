from unittest.mock import patch

import pytest
from dataclasses_avroschema.pydantic import AvroBaseModel
from schema_registry.client import AsyncSchemaRegistryClient
from schema_registry.serializers import (
    AsyncAvroMessageSerializer,
    AsyncJsonMessageSerializer,
)
import io
import typing
from faststream_schema_registry.registries import (
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


@patch.object(AsyncAvroMessageSerializer, "encode_record_with_schema")
async def test_avro_schema_registry(
    encode_record_with_schema, message_with_namespace
):
    registry = AvroSchemaRegistry(url="http://localhost:9999")

    subject, schema_str, schema_obj = registry._get_schema_from_message(
        message_with_namespace
    )
    with ContextStringIO() as outf:
        # Write the magic byte and schema ID in network byte order (big endian)
        outf.write(struct.pack(">bI", 0, 1))

        encoded_message = outf.getvalue()

    encode_record_with_schema.return_value = encoded_message

    return_value, headers = await registry.serialize(message_with_namespace)

    assert isinstance(
        registry._schema_registry_client, AsyncSchemaRegistryClient
    )
    assert isinstance(registry._serializer, AsyncAvroMessageSerializer)
    encode_record_with_schema.assert_called_once_with(
        subject,
        schema_obj,
        message_with_namespace.to_dict(),
    )
    assert headers["schema-id"] == "1"
    assert headers["schema-subject"] == "com.testing.MessageWithNamespace"


@patch.object(AsyncJsonMessageSerializer, "encode_record_with_schema")
async def test_json_schema_registry(
    encode_record_with_schema, message_with_namespace
):
    registry = JsonSchemaRegistry(url="http://localhost:9999")

    subject, schema_str, schema_obj = registry._get_schema_from_message(
        message_with_namespace
    )

    with ContextStringIO() as outf:
        # Write the magic byte and schema ID in network byte order (big endian)
        outf.write(struct.pack(">bI", 0, 1))

        encoded_message = outf.getvalue()

    encode_record_with_schema.return_value = encoded_message

    return_value, headers = await registry.serialize(message_with_namespace)

    assert isinstance(
        registry._schema_registry_client, AsyncSchemaRegistryClient
    )
    assert isinstance(registry._serializer, AsyncJsonMessageSerializer)
    encode_record_with_schema.assert_called_once_with(
        subject,
        schema_obj,
        message_with_namespace.to_dict(),
    )
    assert headers["schema-id"] == "1"
    assert headers["schema-subject"] == "com.testing.MessageWithNamespace"

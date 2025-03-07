import json

from dataclasses_avroschema.pydantic import AvroBaseModel
from schema_registry.client.schema import AvroSchema, JsonSchema

from faststream_schema_registry.registries import SchemaType, SchemaInfo, AvroSchemaRegistry, JsonSchemaRegistry


class Message(AvroBaseModel):
    message_id: int
    message_text: str


message = Message(message_id=1, message_text="testing")


class MessageWithNamespace(AvroBaseModel):
    message_id: int
    message_text: str

    class Meta:
        namespace = "com.testing"


message_with_namespace = MessageWithNamespace(
    message_id=1, message_text="testing"
)


def test_schema_info_from_message():
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


def test_schema_info_from_message_with_namespace():
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

def test_avro_schema_registry():
    return True
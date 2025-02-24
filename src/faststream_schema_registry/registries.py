import io
import json
import typing
from typing import Callable, ParamSpec, Type, TypeVar, Union

import fastavro
from confluent_kafka.schema_registry import (
    Schema,
    SchemaRegistryClient,
    record_subject_name_strategy,
)
from confluent_kafka.schema_registry.avro import (
    AvroDeserializer,
    AvroSerializer,
)
from confluent_kafka.schema_registry.json_schema import (
    JSONDeserializer,
    JSONSerializer,
)
from confluent_kafka.serialization import SerializationContext
from dataclasses_avroschema import AvroModel
from dataclasses_avroschema.pydantic import AvroBaseModel

from faststream_schema_registry.models import SchemaInfo, SchemaType
from faststream_schema_registry.utils import TimedLRUCache

P = ParamSpec("P")
T = TypeVar("T")


class BaseSchemaRegistry:
    _default_conf = {"subject.name.strategy": record_subject_name_strategy}
    serializer: Callable[[str], Union[JSONSerializer, AvroSerializer]]
    schema_type: SchemaType

    def __init__(
        self,
        url: str,
        cache_ttl: int,
        conf: typing.Optional[dict] = None,
        **kwargs,
    ):
        self.url = url
        self.cache_ttl = cache_ttl
        self.client = SchemaRegistryClient(
            {
                "url": url,
                "cache.latest.ttl.sec": cache_ttl,
            }
        )

        self._schema_cache = TimedLRUCache(max_size=1000, ttl=cache_ttl)

        conf_copy = self._default_conf.copy()
        if conf is not None:
            conf_copy.update(conf)

        self.conf = conf_copy

    def _extract_schema_info(
        self, msg: Union[AvroModel, AvroBaseModel]
    ) -> typing.Tuple[str, str]:
        schema_get = {
            SchemaType.Json: ("model_json_schema", {"mode": "validation"}),
            SchemaType.Avro: ("avro_schema_to_python", {}),
        }
        func, kwargs = schema_get[self.schema_type]
        schema = msg.__getattr__(func)(**kwargs)
        subject = schema["name"]

        if "namespace" in schema:
            subject = f"{schema['namespace']}.{['name']}"

        return subject, str(schema)

    def _build_serializer(
        self, serializer: Union[JSONSerializer, AvroSerializer], **kwargs
    ):
        conf = self.conf.copy()
        conf["auto.register.schemas"] = bool(False)
        return serializer(
            schema_registry_client=self.client, conf=conf, **kwargs
        )

    def _build_deserializer(
        self,
        deserializer: Union[Type[JSONDeserializer], Type[AvroDeserializer]],
        **kwargs,
    ):
        return deserializer(
            schema_registry_client=self.client, conf=self.conf, **kwargs
        )

    def _lookup_schema(self, subject, schema_str: str):
        registered_schema = self._schema_cache[
            (subject, self.schema_type.value)
        ]
        if not registered_schema:
            registered_schema = self.client.get_latest_version(
                subject_name=subject
            )
            if not registered_schema:
                registered_schema = self.client.register_schema_full_response(
                    subject_name=subject, schema=Schema(schema_str=schema_str)
                )
            self._schema_cache[(subject, self.schema_type.value)] = (
                registered_schema
            )

        return registered_schema

    def serialize(self, msg: AvroModel, ctx: SerializationContext):
        schema = SchemaInfo.from_message(msg, self.schema_type)

        reg_schema = self._lookup_schema(schema.subject, schema.schema_strj)

        bytes_writer = io.BytesIO()
        fastavro.schemaless_writer(
            fo=bytes_writer,
            schema=json.loads(reg_schema.schema.schema_str),
            record=msg.to_dict(),
        )

        new_msg = (
            b"\x00"
            + reg_schema.schema_id.to_bytes(4, byteorder="big")
            + bytes_writer.getvalue()
        )

        headers = {
            "schema-id": str(reg_schema.schema_id),
            "subject": reg_schema.subject,
        }
        return headers, new_msg


class JSONSchemaRegistry(BaseSchemaRegistry):
    schema_type = SchemaType.Json

    def __init__(
        self,
        url: str,
        cache_ttl: int,
        conf: typing.Optional[dict] = None,
        **kwargs,
    ):
        super().__init__(url, cache_ttl, conf, **kwargs)

        self.serializer = self._build_serializer(JSONSerializer, **kwargs)
        self.deserializer = self._build_deserializer(JSONDeserializer)


class AvroSchemaRegistry(BaseSchemaRegistry):
    schema_type = SchemaType.Avro

    def __init__(
        self,
        url: str,
        cache_ttl: int,
        conf: typing.Optional[dict] = None,
        **kwargs,
    ):
        super().__init__(url, cache_ttl, conf, **kwargs)

        self.serializer = self._build_serializer(AvroSerializer, **kwargs)
        self.deserializer = self._build_deserializer(
            AvroDeserializer, **kwargs
        )

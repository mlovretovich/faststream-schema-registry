from functools import partial
from typing import Any, Awaitable, Callable, Optional

from confluent_kafka.serialization import MessageField, SerializationContext
from faststream import BaseMiddleware
from faststream.broker.message import StreamMessage

from faststream_schema_registry.registries import (
    AvroSchemaRegistry,
    JSONSchemaRegistry,
)


class SchemaRegistryMiddleware(BaseMiddleware):
    def __init__(
        self,
        msg: Optional[Any],
        *,
        registry: JSONSchemaRegistry | AvroSchemaRegistry,
    ):
        self.registry = registry

        super().__init__(msg)

    @classmethod
    def make_middleware(
        cls,
        registry: JSONSchemaRegistry | AvroSchemaRegistry,
    ) -> Callable[[Any], "SchemaRegistryMiddleware"]:
        """
        Creates a partial function that can be used to instantiate the
        middleware.
        """
        return partial(cls, registry=registry)

    async def consume_scope(
        self,
        call_next: Callable[[Any], Awaitable[Any]],
        msg: StreamMessage[Any],
    ) -> Any:
        scheme_id = int.from_bytes(
            msg.body[1:5], byteorder="big", signed=False
        )

        self.registry.client.get_schema(scheme_id)

        new_msg = self.registry.deserializer(msg.body)
        msg._decoded_body = new_msg

        return await call_next(msg)

    async def publish_scope(
        self,
        call_next: Callable[..., Awaitable[Any]],
        msg: Any,
        **options: Any,
    ) -> Any:
        ctx = SerializationContext(
            field=MessageField.value,
            topic=options["topic"],
            headers=options["headers"],
        )
        headers, new_msg = self.registry.serialize(msg, ctx)

        return await call_next(new_msg, **options)

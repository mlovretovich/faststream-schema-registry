from functools import partial
from typing import Any, Awaitable, Callable, Optional

from faststream import BaseMiddleware
from faststream.broker.message import StreamMessage

from faststream_schema_registry.registries import (
    BaseSchemaRegistry,
    SchemaType,
)


class SchemaRegistryMiddleware(BaseMiddleware):
    schema_type: SchemaType

    def __init__(
        self,
        msg: Optional[Any],
        *,
        schema_registry: BaseSchemaRegistry,
    ):
        self.schema_registry = schema_registry
        super().__init__(msg)

    @classmethod
    def make_middleware(
        cls, schema_registry: BaseSchemaRegistry
    ) -> Callable[[Any], "SchemaRegistryMiddleware"]:
        """
        Creates a partial function that can be used to instantiate the
        middleware.
        """
        return partial(cls, schema_registry=schema_registry)

    async def consume_scope(
        self,
        call_next: Callable[[Any], Awaitable[Any]],
        msg: StreamMessage[Any],
    ) -> Any:
        decoded_message = await self.schema_registry.deserialize(msg)

        return await call_next(decoded_message)

    async def publish_scope(
        self,
        call_next: Callable[..., Awaitable[Any]],
        msg: Any,
        **options: Any,
    ) -> Any:
        message_encoded, headers = await self.schema_registry.serialize(
            msg, **options
        )

        return await call_next(message_encoded, **options)

    #

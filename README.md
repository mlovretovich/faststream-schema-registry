# faststream-schema-registry

## Example

```python
from faststream.kafka import KafkaBroker
from faststream_schema_registry.middleware import SchemaRegistryMiddleware
from faststream_schema_registry.confluent import AvroSchemaRegistry

registry = AvroSchemaRegistry(url="http://localhost:8081", cache_ttl=60)

broker = KafkaBroker(
    middlewares=[SchemaRegistryMiddleware.make_middleware(registry)],
)


```

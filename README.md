# faststream-schema-registry
Middleware for async avro/json serialization using the confluent schema registry
### Uses:
* [python-schema-registry-client](https://github.com/marcosschroh/python-schema-registry-client)
* [dataclasses-avroschema](https://github.com/marcosschroh/dataclasses-avroschema)

## Requirements
python 3.9+
## Installation
```bash
pip install faststream-schema-registry
```
## Usage
### AvroSchemaRegistry
```python
from faststream.kafka import KafkaBroker
from faststream_schema_registry.middleware import SchemaRegistryMiddleware
from faststream_schema_registry.registries import AvroSchemaRegistry

schema_registry= AvroSchemaRegistry(url="http://localhost:8081")
broker = KafkaBroker(
    middlewares=[
        SchemaRegistryMiddleware.make_middleware(
            schema_registry=schema_registry
        )
    ])
```

### JsonSchemaRegistry
```python
from faststream.kafka import KafkaBroker
from faststream_schema_registry.middleware import SchemaRegistryMiddleware
from faststream_schema_registry.registries import JsonSchemaRegistry

schema_registry= JsonSchemaRegistry(url="http://localhost:8081")
broker = KafkaBroker(
    middlewares=[
        SchemaRegistryMiddleware.make_middleware(
            schema_registry=schema_registry
        )
    ])

```

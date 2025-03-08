# faststream-schema-registry
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/mlovretovich/faststream-schema-registry/python-app.yml)
[![codecov](https://codecov.io/gh/mlovretovich/faststream-schema-registry/graph/badge.svg?token=NJNZZ3D35Y)](https://codecov.io/gh/mlovretovich/faststream-schema-registry)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://img.shields.io/badge/python-3.9+-blue.svg)
![PyPI - Version](https://img.shields.io/pypi/v/faststream-schema-registry)

Middleware to integrate with the confluent schema registry for managing avro/json schemas.

Schemas are generated from
python classes using [dataclasses-avroschema](https://github.com/marcosschroh/dataclasses-avroschema) and
registered using [python-schema-registry-client](https://github.com/marcosschroh/python-schema-registry-client).

## Requirements
python 3.9+
## Installation
```bash
pip install faststream-schema-registry
```
## Examples
Serialize objects using either the AvroSchemaRegistry or the JsonSchemaRegistry
### AvroSchemaRegistry
```python
from datetime import datetime

from dataclasses_avroschema.pydantic import AvroBaseModel
from faststream import FastStream
from faststream.confluent import KafkaBroker
from faststream_schema_registry.middleware import SchemaRegistryMiddleware
from faststream_schema_registry.registries import AvroSchemaRegistry

schema_registry = AvroSchemaRegistry(url="http://localhost:8081")
broker = KafkaBroker(
    "localhost:29092",
    middlewares=[
        SchemaRegistryMiddleware.make_middleware(schema_registry=schema_registry)
    ],
)

app = FastStream(broker)

# class for message object
class Message(AvroBaseModel):
    timestamp: datetime
    message_id: int
    payload: str

    class Meta:
        namespace = "com.test"

@app.after_startup
async def test():
    await broker.publish(Message.fake(), topic="messages")


@broker.subscriber("messages")
async def on_messages(msg: Message):
    print(msg)

```

### JsonSchemaRegistry
```python
from datetime import datetime

from dataclasses_avroschema.pydantic import AvroBaseModel
from faststream import FastStream
from faststream.confluent import KafkaBroker
from faststream_schema_registry.middleware import SchemaRegistryMiddleware
from faststream_schema_registry.registries import JsonSchemaRegistry

schema_registry = JsonSchemaRegistry(url="http://localhost:8081")
broker = KafkaBroker(
    "localhost:29092",
    middlewares=[
        SchemaRegistryMiddleware.make_middleware(schema_registry=schema_registry)
    ],
)
...
```

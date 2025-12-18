# Shared Utilities

This directory contains shared utilities and dependencies for all microservices in TheOne project.

## Structure

- `config.py` - Environment variable loader and configuration management
- `models.py` - Pydantic models for inter-service communication
- `database.py` - Database connection utilities (PostgreSQL, MongoDB, Redis)
- `rabbitmq.py` - RabbitMQ publisher/consumer base classes
- `logging_config.py` - Structured JSON logging configuration
- `requirements.txt` - Shared Python dependencies

## Installation

To use these shared utilities in a service, add the shared directory to your Python path or install it as a package.

### Option 1: Add to PYTHONPATH

```python
import sys
sys.path.append('/path/to/TheOne/shared')
```

### Option 2: Install as editable package

```bash
pip install -e /path/to/TheOne/shared
```

### Option 3: Copy shared directory to each service

Copy the shared directory into each service and import directly.

## Usage Examples

### Configuration

```python
from shared.config import get_settings

settings = get_settings()
database_url = settings.database.url
```

### Database Connections

```python
from shared.database import get_postgres, get_mongo, get_redis

# PostgreSQL
postgres = get_postgres()
with postgres.get_cursor() as cursor:
    cursor.execute("SELECT * FROM users")
    results = cursor.fetchall()

# MongoDB
mongo = get_mongo()
collection = mongo.database.users
users = collection.find({"active": True})

# Redis
redis = get_redis()
redis.client.set("key", "value")
value = redis.client.get("key")
```

### RabbitMQ

```python
from shared.rabbitmq import RabbitMQPublisher, RabbitMQConsumer
from shared.models import OrderMessage, MessageType

# Publisher
publisher = RabbitMQPublisher()
message = OrderMessage(
    message_id="123",
    message_type=MessageType.ORDER_CREATED,
    source_service="order-service",
    order_id="order-123",
    user_id="user-456",
    status="pending",
    total_amount=99.99,
    items=[]
)
publisher.publish(message)

# Consumer
def handle_message(message_data, properties, method):
    print(f"Received: {message_data}")

consumer = RabbitMQConsumer(
    queue_name="notifications",
    routing_keys=["order.created", "order.updated"],
    callback=handle_message
)
consumer.start_consuming()
```

### Logging

```python
from shared.logging_config import setup_logging, get_logger

# Setup logging
setup_logging(
    service_name="order-service",
    log_level="INFO",
    json_output=True
)

# Use logger
logger = get_logger(__name__, "order-service")
logger.info("Order created", extra={"order_id": "123"})
```

### Models

```python
from shared.models import OrderMessage, MessageType, HealthCheckResponse

# Create message
message = OrderMessage(
    message_id="msg-123",
    message_type=MessageType.ORDER_CREATED,
    source_service="order-service",
    order_id="order-123",
    user_id="user-456",
    status="pending",
    total_amount=99.99,
    items=[{"product_id": "prod-1", "quantity": 2}]
)

# Serialize to JSON
json_data = message.model_dump_json()

# Deserialize from JSON
message = OrderMessage.model_validate_json(json_data)
```

## Environment Variables

The configuration system supports the following environment variables:

- `DATABASE_URL` - PostgreSQL connection string
- `MONGODB_URL` - MongoDB connection string
- `REDIS_URL` - Redis connection string
- `RABBITMQ_URL` - RabbitMQ connection string
- `ENVIRONMENT` - Environment name (development, staging, production)
- `DEBUG` - Debug mode (true/false)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Dependencies

See `requirements.txt` for the complete list of shared dependencies.


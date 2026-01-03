from uuid import uuid4
from datetime import datetime
from typing import List, Dict, Any

from shared.rabbitmq import RabbitMQPublisher
from shared.models import OrderMessage, MessageType
from app.models import Order
from shared.logging_config import get_logger

logger = get_logger(__name__, "order-service")


async def publish_order_created_event(order: Order):
    """Publish order.created event to RabbitMQ"""
    try:
        publisher = RabbitMQPublisher()
        
        # Prepare order items
        items = [
            {
                "product_id": str(item.product_id),
                "sku": item.sku,
                "quantity": item.quantity,
                "price": float(item.price)
            }
            for item in order.items
        ]
        
        # Create order message
        message = OrderMessage(
            message_id=str(uuid4()),
            message_type=MessageType.ORDER_CREATED,
            timestamp=datetime.utcnow(),
            source_service="order-service",
            correlation_id=None,
            metadata={},
            order_id=str(order.id),
            user_id=str(order.user_id),
            status=order.status.value,
            total_amount=float(order.total),
            items=items
        )
        
        # Publish message
        await publisher.publish(message, routing_key="order.created")
        logger.info(f"Published order.created event for order {order.id}")
        
    except Exception as e:
        logger.error(f"Error publishing order.created event for order {order.id}: {e}", exc_info=True)
        # Don't raise - event publishing failure shouldn't fail order creation
        # In production, you might want to use an outbox pattern for guaranteed delivery


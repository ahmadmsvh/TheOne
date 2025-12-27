import uuid
import asyncio
from typing import Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import os
from shared.logging_config import get_logger
from shared.config import get_settings
from shared.rabbitmq import RabbitMQPublisher, RabbitMQConnection
from shared.models import MessageType, ProductMessage, InventoryMessage
from app.models import Product

logger = get_logger(__name__, os.getenv("SERVICE_NAME"))

# Thread pool executor for running blocking RabbitMQ operations
_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="rabbitmq")


class ProductEventPublisher:
    """Event publisher for product-service events"""
    
    def __init__(self):
        self.settings = None
        self._publisher: Optional[RabbitMQPublisher] = None
        self._connection: Optional[RabbitMQConnection] = None
        self._service_name = os.getenv("SERVICE_NAME", "product-service")
    
    def _get_publisher(self) -> RabbitMQPublisher:
        """Get or create RabbitMQ publisher instance"""
        if self._publisher is None:
            try:
                self.settings = get_settings()
                
                if self.settings.rabbitmq is None:
                    logger.warning("RabbitMQ settings not configured. Events will not be published.")
                    return None
                
                self._connection = RabbitMQConnection()
                self._publisher = RabbitMQPublisher(self._connection)
                # Connect to ensure exchange is declared
                self._connection.connect()
                logger.info("Product event publisher initialized")
            except Exception as e:
                logger.error(f"Failed to initialize RabbitMQ publisher: {e}")
                return None
        return self._publisher
    
    def _publish_sync(self, message, routing_key: str):
        """Synchronous publish method (to be run in thread pool)"""
        try:
            publisher = self._get_publisher()
            if publisher is None:
                logger.debug("RabbitMQ publisher not available, skipping event publish")
                return
            
            publisher.publish(message, routing_key=routing_key)
        except Exception as e:
            logger.error(f"Failed to publish event: {e}", exc_info=True)
            # Don't raise - event publishing failures shouldn't break the main flow
    
    async def publish_event(self, message, routing_key: str):
        """Publish event asynchronously"""
        try:
            # Run blocking publish in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(_executor, self._publish_sync, message, routing_key)
        except Exception as e:
            logger.error(f"Error scheduling event publish: {e}", exc_info=True)
    
    async def publish_product_created(self, product: Product, correlation_id: Optional[str] = None):
        """Publish product.created event"""
        try:
            message = ProductMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.PRODUCT_CREATED,
                source_service=self._service_name,
                correlation_id=correlation_id,
                product_id=str(product.id),
                name=product.name,
                price=product.price,
                stock=product.stock,
                category=product.category,
                metadata={
                    "sku": product.sku,
                    "status": product.status.value if hasattr(product.status, 'value') else str(product.status),
                    "vendor_id": product.vendor_id,
                    "created_by": product.created_by
                }
            )
            await self.publish_event(message, "product.created")
        except Exception as e:
            logger.error(f"Failed to create product.created event: {e}", exc_info=True)
    
    async def publish_product_updated(self, product: Product, correlation_id: Optional[str] = None):
        """Publish product.updated event"""
        try:
            message = ProductMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.PRODUCT_UPDATED,
                source_service=self._service_name,
                correlation_id=correlation_id,
                product_id=str(product.id),
                name=product.name,
                price=product.price,
                stock=product.stock,
                category=product.category,
                metadata={
                    "sku": product.sku,
                    "status": product.status.value if hasattr(product.status, 'value') else str(product.status),
                    "vendor_id": product.vendor_id,
                    "updated_by": product.updated_by
                }
            )
            await self.publish_event(message, "product.updated")
        except Exception as e:
            logger.error(f"Failed to create product.updated event: {e}", exc_info=True)
    
    async def publish_inventory_updated(
        self,
        product: Product,
        quantity_change: int,
        correlation_id: Optional[str] = None
    ):
        """Publish inventory.updated event"""
        try:
            available_stock = product.stock - product.reserved_stock
            message = InventoryMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.INVENTORY_UPDATED,
                source_service=self._service_name,
                correlation_id=correlation_id,
                product_id=str(product.id),
                sku=product.sku,
                quantity_change=quantity_change,
                total_stock=product.stock,
                reserved_stock=product.reserved_stock,
                available_stock=available_stock,
                metadata={
                    "status": product.status.value if hasattr(product.status, 'value') else str(product.status)
                }
            )
            await self.publish_event(message, "inventory.updated")
        except Exception as e:
            logger.error(f"Failed to create inventory.updated event: {e}", exc_info=True)
    
    async def publish_inventory_reserved(
        self,
        product: Product,
        quantity: int,
        order_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        """Publish inventory.reserved event"""
        try:
            available_stock = product.stock - product.reserved_stock
            message = InventoryMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.INVENTORY_RESERVED,
                source_service=self._service_name,
                correlation_id=correlation_id,
                product_id=str(product.id),
                sku=product.sku,
                quantity=quantity,
                total_stock=product.stock,
                reserved_stock=product.reserved_stock,
                available_stock=available_stock,
                order_id=order_id,
                metadata={
                    "status": product.status.value if hasattr(product.status, 'value') else str(product.status)
                }
            )
            await self.publish_event(message, "inventory.reserved")
        except Exception as e:
            logger.error(f"Failed to create inventory.reserved event: {e}", exc_info=True)
    
    async def publish_inventory_released(
        self,
        product: Product,
        quantity: int,
        order_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        """Publish inventory.released event"""
        try:
            available_stock = product.stock - product.reserved_stock
            message = InventoryMessage(
                message_id=str(uuid.uuid4()),
                message_type=MessageType.INVENTORY_RELEASED,
                source_service=self._service_name,
                correlation_id=correlation_id,
                product_id=str(product.id),
                sku=product.sku,
                quantity=quantity,
                total_stock=product.stock,
                reserved_stock=product.reserved_stock,
                available_stock=available_stock,
                order_id=order_id,
                metadata={
                    "status": product.status.value if hasattr(product.status, 'value') else str(product.status)
                }
            )
            await self.publish_event(message, "inventory.released")
        except Exception as e:
            logger.error(f"Failed to create inventory.released event: {e}", exc_info=True)
    
    def close(self):
        """Close RabbitMQ connection"""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.error(f"Error closing RabbitMQ connection: {e}")


# Global event publisher instance (singleton pattern)
_event_publisher: Optional[ProductEventPublisher] = None


def get_event_publisher() -> ProductEventPublisher:
    """Get global event publisher instance"""
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = ProductEventPublisher()
    return _event_publisher


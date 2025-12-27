import json
import time
import asyncio
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import os
import threading

from pika.exceptions import AMQPConnectionError, AMQPChannelError
from shared.logging_config import get_logger
from shared.config import get_settings
from shared.rabbitmq import RabbitMQConsumer, RabbitMQConnection
from pika.adapters.blocking_connection import BlockingChannel
from shared.models import OrderMessage, MessageType
from app.core.database import get_db_manager
from app.repositories.product_repository import ProductRepository
from app.services.product_service import ProductService
from app.utils import run_async

logger = get_logger(__name__, os.getenv("SERVICE_NAME"))

# Thread pool executor for running blocking RabbitMQ operations
_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="rabbitmq-consumer")

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # Base delay in seconds (exponential backoff)


class OrderEventConsumer:
    """Consumer for order-related events"""
    
    def __init__(self):
        self.settings = get_settings()
        self._consumer: Optional[RabbitMQConsumer] = None
        self._connection: Optional[RabbitMQConnection] = None
        self._service_name = os.getenv("SERVICE_NAME", "product-service")
        self._running = False
        self._consumer_thread: Optional[threading.Thread] = None
        
    def _get_connection(self) -> RabbitMQConnection:
        """Get or create RabbitMQ connection instance"""
        if self._connection is None:
            try:
                self._connection = RabbitMQConnection()
                self._connection.connect()
                logger.info("RabbitMQ connection established for consumer")
            except Exception as e:
                logger.error(f"Failed to initialize RabbitMQ connection: {e}")
                raise
        return self._connection
    
    def _get_db_manager(self):
        """Get database manager instance"""
        return get_db_manager()
    
    async def _handle_order_completed(self, message_data: Dict[str, Any]) -> bool:
        """
        Handle order.completed event
        Deducts reserved quantity from total stock and updates inventory
        """
        try:
            # Parse order message
            order_message = OrderMessage(**message_data)
            order_id = order_message.order_id
            items = order_message.items
            
            logger.info(f"Processing order.completed event for order {order_id}")
            
            # Get database manager
            db_manager = self._get_db_manager()
            await run_async(db_manager.connect())
            database = await run_async(db_manager.get_database())
            repository = ProductRepository(database)
            
            # Process each item in the order
            processed_items = []
            errors = []
            
            for item in items:
                try:
                    product_id = item.get("product_id")
                    quantity = item.get("quantity", 0)
                    
                    if not product_id or quantity <= 0:
                        logger.warning(f"Invalid item in order {order_id}: {item}")
                        continue
                    
                    # Deduct reserved stock from total stock
                    updated_product = await repository.complete_order_deduction(
                        product_id=str(product_id),
                        quantity=int(quantity)
                    )
                    
                    if updated_product:
                        processed_items.append({
                            "product_id": product_id,
                            "quantity": quantity,
                            "new_stock": updated_product.stock,
                            "new_reserved_stock": updated_product.reserved_stock
                        })
                        logger.info(
                            f"Completed order deduction for product {product_id}: "
                            f"deducted {quantity}, new stock: {updated_product.stock}, "
                            f"new reserved: {updated_product.reserved_stock}"
                        )
                    else:
                        errors.append(f"Product {product_id} not found")
                        logger.error(f"Product {product_id} not found for order {order_id}")
                        
                except ValueError as e:
                    error_msg = f"Validation error for product {item.get('product_id')}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                except Exception as e:
                    error_msg = f"Error processing item {item.get('product_id')}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)
            
            if errors:
                logger.warning(
                    f"Order {order_id} completed with {len(errors)} errors: {errors}"
                )
                # Still return True if at least some items were processed
                return len(processed_items) > 0
            
            logger.info(
                f"Successfully processed order.completed for order {order_id}: "
                f"{len(processed_items)} items processed"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error handling order.completed event: {e}", exc_info=True)
            return False
    
    async def _handle_order_cancelled(self, message_data: Dict[str, Any]) -> bool:
        """
        Handle order.cancelled event
        Releases reserved inventory back to available stock
        """
        try:
            # Parse order message
            order_message = OrderMessage(**message_data)
            order_id = order_message.order_id
            items = order_message.items
            
            logger.info(f"Processing order.cancelled event for order {order_id}")
            
            # Get database manager
            db_manager = self._get_db_manager()
            await run_async(db_manager.connect())
            database = await run_async(db_manager.get_database())
            repository = ProductRepository(database)
            
            # Process each item in the order
            processed_items = []
            errors = []
            
            for item in items:
                try:
                    product_id = item.get("product_id")
                    quantity = item.get("quantity", 0)
                    
                    if not product_id or quantity <= 0:
                        logger.warning(f"Invalid item in order {order_id}: {item}")
                        continue
                    
                    # Release reserved stock
                    updated_product = await repository.release_stock(
                        product_id=str(product_id),
                        quantity=int(quantity)
                    )
                    
                    if updated_product:
                        processed_items.append({
                            "product_id": product_id,
                            "quantity": quantity,
                            "new_reserved_stock": updated_product.reserved_stock
                        })
                        logger.info(
                            f"Released inventory for product {product_id}: "
                            f"released {quantity}, new reserved: {updated_product.reserved_stock}"
                        )
                    else:
                        errors.append(f"Product {product_id} not found")
                        logger.error(f"Product {product_id} not found for order {order_id}")
                        
                except ValueError as e:
                    error_msg = f"Validation error for product {item.get('product_id')}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                except Exception as e:
                    error_msg = f"Error processing item {item.get('product_id')}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)
            
            if errors:
                logger.warning(
                    f"Order {order_id} cancelled with {len(errors)} errors: {errors}"
                )
                # Still return True if at least some items were processed
                return len(processed_items) > 0
            
            logger.info(
                f"Successfully processed order.cancelled for order {order_id}: "
                f"{len(processed_items)} items processed"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error handling order.cancelled event: {e}", exc_info=True)
            return False
    
    async def _process_with_retry(
        self,
        message_data: Dict[str, Any],
        handler: Callable,
        max_retries: int = MAX_RETRIES
    ) -> bool:
        """
        Process message with retry logic
        Returns True if processing succeeded, False otherwise
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                result = await handler(message_data)
                if result:
                    return True
                # If handler returns False, it's a non-retryable error
                logger.warning(f"Handler returned False, not retrying")
                return False
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = RETRY_DELAY_BASE ** attempt
                    logger.warning(
                        f"Error processing message (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Failed to process message after {max_retries} attempts: {e}",
                        exc_info=True
                    )
        
        return False
    
    def _process_message_sync(
        self,
        ch,
        method,
        properties,
        body: bytes
    ):
        """
        Synchronous message processing wrapper (runs async handler in event loop)
        This is called by RabbitMQConsumer's callback
        """
        try:
            # Parse message
            message_data = json.loads(body.decode('utf-8'))
            message_type = message_data.get("message_type")
            routing_key = method.routing_key if hasattr(method, 'routing_key') else message_type
            
            logger.info(f"Received message: {message_data.get('message_id', 'unknown')}, type: {message_type}, routing_key: {routing_key}")
            
            # Determine handler based on message type or routing key
            handler = None
            if message_type == MessageType.ORDER_COMPLETED.value or routing_key == "order.completed":
                handler = self._handle_order_completed
            elif message_type == MessageType.ORDER_CANCELLED.value or routing_key == "order.cancelled":
                handler = self._handle_order_cancelled
            elif message_type == MessageType.ORDER_UPDATED.value:
                # Check if status is "completed"
                status = message_data.get("status", "")
                if status.lower() == "completed":
                    handler = self._handle_order_completed
                elif status.lower() == "cancelled":
                    handler = self._handle_order_cancelled
            
            if handler is None:
                logger.warning(f"Unknown message type or routing key: {message_type}/{routing_key}")
                # Ack the message even if we don't handle it
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Run async handler in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(
                    self._process_with_retry(message_data, handler)
                )
                
                if success:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info(f"Successfully processed message {message_data.get('message_id', 'unknown')}")
                else:
                    # After max retries, nack and don't requeue (send to DLQ)
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    logger.error(f"Failed to process message {message_data.get('message_id', 'unknown')} after retries")
            finally:
                loop.close()
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Error in message processing wrapper: {e}", exc_info=True)
            # Try to nack, but if that fails, just log
            try:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            except:
                pass
    
    def _create_consumer(self) -> RabbitMQConsumer:
        """Create and configure RabbitMQ consumer"""
        connection = self._get_connection()
        
        # Subscribe to order.completed and order.cancelled events
        routing_keys = ["order.completed", "order.cancelled"]
        
        # Create consumer with custom processing
        consumer = OrderEventRabbitMQConsumer(
            queue_name="order_events",
            routing_keys=routing_keys,
            connection=connection,
            event_handler=self
        )
        
        return consumer
    
    def start(self):
        """Start consuming messages in a background thread"""
        if self._running:
            logger.warning("Consumer is already running")
            return
        
        def run_consumer():
            """Run consumer in thread"""
            try:
                self._running = True
                logger.info("Starting order event consumer...")
                
                # Create consumer and setup queue
                self._consumer = self._create_consumer()
                self._consumer.setup_queue()
                
                # Start consuming (blocking call)
                channel = self._consumer.connection.channel
                channel.basic_consume(
                    queue=self._consumer.queue_name,
                    on_message_callback=self._consumer.process_message
                )
                
                logger.info(f"Started consuming from queue: {self._consumer.queue_name}")
                channel.start_consuming()
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping consumer...")
                self.stop()
            except Exception as e:
                logger.error(f"Error in consumer thread: {e}", exc_info=True)
                self._running = False
        
        self._consumer_thread = threading.Thread(target=run_consumer, daemon=True)
        self._consumer_thread.start()
        logger.info("Order event consumer thread started")
    
    def stop(self):
        """Stop consuming messages"""
        self._running = False
        if self._consumer:
            try:
                self._consumer.stop_consuming()
                logger.info("Stopped order event consumer")
            except Exception as e:
                logger.error(f"Error stopping consumer: {e}")
        
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")


class OrderEventRabbitMQConsumer(RabbitMQConsumer):
    """Custom RabbitMQ consumer for order events with retry logic"""
    
    def __init__(self, queue_name: str, routing_keys: list, connection, event_handler):
        super().__init__(queue_name, routing_keys, connection, callback=None)
        self.event_handler = event_handler
    
    def process_message(self, ch, method, properties, body: bytes):
        """Override process_message to use our custom handler with retry logic"""
        self.event_handler._process_message_sync(ch, method, properties, body)


# Global consumer instance (singleton pattern)
_event_consumer: Optional[OrderEventConsumer] = None


def get_event_consumer() -> OrderEventConsumer:
    """Get global event consumer instance"""
    global _event_consumer
    if _event_consumer is None:
        _event_consumer = OrderEventConsumer()
    return _event_consumer


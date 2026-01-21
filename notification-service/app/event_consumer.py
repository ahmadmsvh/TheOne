import json
import asyncio
import logging
import os
from typing import Optional, Dict, Any

from shared.rabbitmq import RabbitMQConsumer, RabbitMQConnection
from shared.models import OrderMessage, UserMessage, MessageType
from shared.logging_config import get_logger
from shared.config import get_settings
from app.tasks import send_email

logger = get_logger(__name__, os.getenv("SERVICE_NAME", "notification-service"))


class NotificationEventConsumer:
    
    def __init__(self):
        self.settings = get_settings()
        self._consumer: Optional[RabbitMQConsumer] = None
        self._connection: Optional[RabbitMQConnection] = None
        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None
    
    async def _get_connection(self) -> RabbitMQConnection:
        if self._connection is None:
            try:
                self._connection = RabbitMQConnection()
                await self._connection.connect()
                logger.info("RabbitMQ connection established for notification consumer")
            except Exception as e:
                logger.error(f"Failed to initialize RabbitMQ connection: {e}")
                raise
        return self._connection
    
    async def _handle_user_registered(self, message_data: Dict[str, Any]) -> bool:
        try:
            user_message = UserMessage(**message_data)
            user_id = user_message.user_id
            email = user_message.email
            username = user_message.username or email.split('@')[0]
            
            logger.info(f"Processing user.registered event for user {user_id} ({email})")
            
            send_email.delay(
                recipient=email,
                subject='Welcome to Our Service!',
                body=f'Hello {username},\n\nThank you for registering with us! We are excited to have you on board.\n\nBest regards,\nThe Team'
            )
            
            logger.info(f"Queued welcome email for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling user.registered event: {e}", exc_info=True)
            return False
    
    async def _handle_order_created(self, message_data: Dict[str, Any]) -> bool:
        try:
            order_message = OrderMessage(**message_data)
            order_id = order_message.order_id
            user_id = order_message.user_id
            total_amount = order_message.total_amount
            items = order_message.items
            
            logger.info(f"Processing order.created event for order {order_id}")
            
            user_email = message_data.get('metadata', {}).get('user_email', f'user_{user_id}@example.com')
            
            items_list = '\n'.join([
                f"- {item.get('sku', 'N/A')}: {item.get('quantity', 0)}x ${item.get('price', 0):.2f}"
                for item in items
            ])
            
            send_email.delay(
                recipient=user_email,
                subject=f'Order Confirmation - #{order_id}',
                body=f'Your order #{order_id} has been confirmed and will be processed shortly.\n\nTotal Amount: ${total_amount:.2f}\n\nItems:\n{items_list}\n\nView your order: https://example.com/orders/{order_id}'
            )
            
            logger.info(f"Queued order confirmation email for order {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling order.created event: {e}", exc_info=True)
            return False
    
    async def _handle_order_paid(self, message_data: Dict[str, Any]) -> bool:

        try:
            order_message = OrderMessage(**message_data)
            order_id = order_message.order_id
            user_id = order_message.user_id
            total_amount = order_message.total_amount
            metadata = order_message.metadata
            transaction_id = metadata.get('transaction_id', 'N/A')
            payment_method = metadata.get('payment_method', 'Unknown')
            
            logger.info(f"Processing order.paid event for order {order_id}")
            
            user_email = message_data.get('metadata', {}).get('user_email', f'user_{user_id}@example.com')
            
            send_email.delay(
                recipient=user_email,
                subject=f'Payment Confirmed - Order #{order_id}',
                body=f'Your payment for order #{order_id} has been successfully processed.\n\nTransaction ID: {transaction_id}\nPayment Method: {payment_method}\nAmount: ${total_amount:.2f}\n\nView your order: https://example.com/orders/{order_id}'
            )
            
            logger.info(f"Queued payment confirmation email for order {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling order.paid event: {e}", exc_info=True)
            return False
    
    async def _handle_order_status_changed(self, message_data: Dict[str, Any]) -> bool:
        try:
            order_message = OrderMessage(**message_data)
            order_id = order_message.order_id
            user_id = order_message.user_id
            status = order_message.status
            metadata = order_message.metadata
            old_status = metadata.get('old_status', 'Unknown')
            new_status = metadata.get('new_status', status)
            
            logger.info(f"Processing order.status_changed event for order {order_id} ({old_status} -> {new_status})")
            
            user_email = message_data.get('metadata', {}).get('user_email', f'user_{user_id}@example.com')
            
            send_email.delay(
                recipient=user_email,
                subject=f'Order Status Update - #{order_id}',
                body=f'Your order #{order_id} status has been updated:\n\nPrevious Status: {old_status}\nNew Status: {new_status}\n\nView your order: https://example.com/orders/{order_id}'
            )
            
            logger.info(f"Queued status update email for order {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling order.status_changed event: {e}", exc_info=True)
            return False
    
    async def _handle_order_cancelled(self, message_data: Dict[str, Any]) -> bool:
        try:
            order_message = OrderMessage(**message_data)
            order_id = order_message.order_id
            user_id = order_message.user_id
            total_amount = order_message.total_amount
            
            logger.info(f"Processing order.cancelled event for order {order_id}")
            
            user_email = message_data.get('metadata', {}).get('user_email', f'user_{user_id}@example.com')
            
            send_email.delay(
                recipient=user_email,
                subject=f'Order Cancelled - #{order_id}',
                body=f'Your order #{order_id} has been cancelled.\n\nIf you were charged for this order, a refund of ${total_amount:.2f} will be processed within 5-7 business days to your original payment method.\n\nView your order: https://example.com/orders/{order_id}'
            )
            
            logger.info(f"Queued cancellation notice email for order {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling order.cancelled event: {e}", exc_info=True)
            return False
    
    async def _process_message(
        self,
        message_data: Dict[str, Any],
        message_properties: Any,
        message: Any
    ):
        try:
            message_type = message_data.get('message_type')
            
            if not message_type:
                logger.warning(f"Message missing message_type: {message_data.get('message_id', 'unknown')}")
                return
            
            logger.info(f"Processing message type: {message_type} (ID: {message_data.get('message_id', 'unknown')})")
            
            handler_map = {
                'user.registered': self._handle_user_registered,
                'user.created': self._handle_user_registered,
                'order.created': self._handle_order_created,
                'order.paid': self._handle_order_paid,
                'order.updated': self._handle_order_status_changed,
                'order.status_changed': self._handle_order_status_changed,
                'order.cancelled': self._handle_order_cancelled,
            }
            
            handler = handler_map.get(message_type)
            if handler:
                success = await handler(message_data)
                if success:
                    logger.info(f"Successfully processed {message_type} event")
                else:
                    logger.warning(f"Handler returned False for {message_type} event")
            else:
                logger.warning(f"No handler found for message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise
    
    async def start(self):
        if self._running:
            logger.warning("Consumer is already running")
            return
        
        try:
            connection = await self._get_connection()
            
            routing_keys = [
                'user.registered',
                'user.created',
                'order.created',
                'order.paid',
                'order.updated',
                'order.status_changed',
                'order.cancelled',
            ]
            
            self._consumer = RabbitMQConsumer(
                queue_name='notifications',
                routing_keys=routing_keys,
                connection=connection,
                callback=self._process_message
            )
            
            await self._consumer.setup_queue()
            await self._consumer.start_consuming()
            
            self._running = True
            logger.info("Notification event consumer started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start notification consumer: {e}", exc_info=True)
            self._running = False
            raise
    
    async def stop(self):
        if not self._running:
            return
        
        try:
            if self._consumer:
                await self._consumer.stop_consuming()
            
            if self._connection:
                await self._connection.close()
            
            self._running = False
            logger.info("Notification event consumer stopped")
            
        except Exception as e:
            logger.error(f"Error stopping notification consumer: {e}", exc_info=True)
    
    async def run_forever(self):
        try:
            await self.start()
            
            while self._running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Consumer error: {e}", exc_info=True)
        finally:
            await self.stop()

from uuid import UUID
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models import Order, OrderItem, OrderStatus
from shared.logging_config import get_logger

logger = get_logger(__name__, "order-service")


class OrderRepository:
    """Repository for order database operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_order(
        self,
        user_id: UUID,
        total: float,
        status: OrderStatus = OrderStatus.PENDING
    ) -> Order:
        """Create a new order"""
        try:
            order = Order(
                user_id=user_id,
                total=total,
                status=status
            )
            self.db.add(order)
            self.db.flush()  # Flush to get the order ID
            return order
        except SQLAlchemyError as e:
            logger.error(f"Error creating order: {e}")
            self.db.rollback()
            raise
    
    def create_order_item(
        self,
        order_id: UUID,
        product_id: str,  # MongoDB ObjectId as string
        sku: str,
        quantity: int,
        price: float
    ) -> OrderItem:
        """Create an order item"""
        try:
            order_item = OrderItem(
                order_id=order_id,
                product_id=product_id,
                sku=sku,
                quantity=quantity,
                price=price
            )
            self.db.add(order_item)
            return order_item
        except SQLAlchemyError as e:
            logger.error(f"Error creating order item: {e}")
            self.db.rollback()
            raise
    
    def get_order_by_id(self, order_id: UUID) -> Optional[Order]:
        """Get order by ID"""
        try:
            return self.db.query(Order).filter(Order.id == order_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting order {order_id}: {e}")
            raise
    
    def get_orders_by_user_id(self, user_id: UUID) -> List[Order]:
        """Get all orders for a user"""
        try:
            return self.db.query(Order).filter(Order.user_id == user_id).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting orders for user {user_id}: {e}")
            raise
    
    def commit(self):
        """Commit transaction"""
        try:
            self.db.commit()
        except SQLAlchemyError as e:
            logger.error(f"Error committing transaction: {e}")
            self.db.rollback()
            raise
    
    def rollback(self):
        """Rollback transaction"""
        self.db.rollback()


from uuid import UUID
from typing import List, Dict, Any
from decimal import Decimal

from app.repositories.order_repository import OrderRepository
from app.models import Order, OrderStatus
from app.core.product_client import ProductServiceClient
from shared.logging_config import get_logger

logger = get_logger(__name__, "order-service")


class OrderService:
    """Service for order business logic"""
    
    def __init__(self, repository: OrderRepository, product_client: ProductServiceClient):
        self.repository = repository
        self.product_client = product_client
    
    async def create_order(
        self,
        user_id: UUID,
        cart_items: List[Dict[str, Any]],
        token: str
    ) -> Order:
        """
        Create an order with the following steps:
        1. Validate cart items (call Product service)
        2. Check inventory availability (Product service)
        3. Calculate total price
        4. Reserve inventory via Product service
        5. Create order in database
        """
        try:
            # 1. Validate cart items and check inventory
            validated_items = await self.product_client.validate_cart_items(
                cart_items=[{"product_id": item["product_id"], "quantity": item["quantity"]} for item in cart_items],
                token=token
            )
            
            # 2. Calculate total price
            total = Decimal("0.00")
            for item in validated_items:
                item_total = Decimal(str(item["price"])) * Decimal(str(item["quantity"]))
                total += item_total
            
            # 3. Create order
            order = self.repository.create_order(
                user_id=user_id,
                total=float(total),
                status=OrderStatus.PENDING
            )
            
            # 4. Reserve inventory for each item
            reserved_products = []
            try:
                for item in validated_items:
                    product_id = item["product_id"]
                    quantity = item["quantity"]
                    
                    # Reserve inventory
                    await self.product_client.reserve_inventory(
                        product_id=product_id,
                        quantity=quantity,
                        order_id=str(order.id),
                        token=token
                    )
                    reserved_products.append(product_id)
                    
                    # Create order item
                    self.repository.create_order_item(
                        order_id=order.id,
                        product_id=product_id,  # Keep as string (MongoDB ObjectId)
                        sku=item.get("sku", ""),
                        quantity=quantity,
                        price=float(item["price"])
                    )
                
                # Commit transaction
                self.repository.commit()
                logger.info(f"Order {order.id} created successfully for user {user_id}")
                return order
                
            except Exception as e:
                # If reservation fails, rollback and re-raise
                logger.error(f"Error reserving inventory for order {order.id}: {e}")
                self.repository.rollback()
                # TODO: Release already reserved inventory if any
                raise
            
        except Exception as e:
            logger.error(f"Error creating order for user {user_id}: {e}")
            self.repository.rollback()
            raise
    
    def get_order_by_id(self, order_id: UUID) -> Order:
        """Get order by ID"""
        order = self.repository.get_order_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        return order
    
    def get_orders_by_user_id(self, user_id: UUID) -> List[Order]:
        """Get all orders for a user"""
        return self.repository.get_orders_by_user_id(user_id)


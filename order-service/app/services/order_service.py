from uuid import UUID
from typing import List, Dict, Any
from decimal import Decimal

from app.repositories.order_repository import OrderRepository
from app.models import Order, OrderStatus
from app.core.product_client import ProductServiceClient
from shared.logging_config import get_logger

logger = get_logger(__name__, "order-service")


class OrderService:
    
    def __init__(self, repository: OrderRepository, product_client: ProductServiceClient):
        self.repository = repository
        self.product_client = product_client
    
    async def create_order(
        self,
        user_id: UUID,
        cart_items: List[Dict[str, Any]],
        token: str
    ) -> Order:

        try:
            validated_items = await self.product_client.validate_cart_items(
                cart_items=[{"product_id": item["product_id"], "quantity": item["quantity"]} for item in cart_items],
                token=token
            )
            
            total = Decimal("0.00")
            for item in validated_items:
                item_total = Decimal(str(item["price"])) * Decimal(str(item["quantity"]))
                total += item_total
            
            order = self.repository.create_order(
                user_id=user_id,
                total=float(total),
                status=OrderStatus.PENDING
            )
            
            reserved_products = []
            try:
                for item in validated_items:
                    product_id = item["product_id"]
                    quantity = item["quantity"]
                    
                    await self.product_client.reserve_inventory(
                        product_id=product_id,
                        quantity=quantity,
                        order_id=str(order.id),
                        token=token
                    )
                    reserved_products.append(product_id)
                    
                    self.repository.create_order_item(
                        order_id=order.id,
                        product_id=product_id,
                        sku=item.get("sku", ""),
                        quantity=quantity,
                        price=float(item["price"])
                    )
                
                self.repository.commit()
                logger.info(f"Order {order.id} created successfully for user {user_id}")
                return order
                
            except Exception as e:
                logger.error(f"Error reserving inventory for order {order.id}: {e}")
                self.repository.rollback()
                raise
            
        except Exception as e:
            logger.error(f"Error creating order for user {user_id}: {e}")
            self.repository.rollback()
            raise
    
    def get_order_by_id(self, order_id: UUID) -> Order:
        order = self.repository.get_order_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        return order
    
    def get_orders_by_user_id(self, user_id: UUID) -> List[Order]:
        return self.repository.get_orders_by_user_id(user_id)


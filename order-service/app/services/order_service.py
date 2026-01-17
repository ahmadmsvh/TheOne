from uuid import UUID
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal

from app.repositories.order_repository import OrderRepository
from app.repositories.payment_repository import PaymentRepository
from app.models import Order, OrderStatus
from app.core.product_client import ProductServiceClient
from app.services.payment_service import PaymentService
from shared.logging_config import get_logger

logger = get_logger(__name__, "order-service")

STATUS_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.PAID, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED: [OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.CANCELLED],
    OrderStatus.PAID: [OrderStatus.PROCESSING, OrderStatus.SHIPPED],
    OrderStatus.PROCESSING: [OrderStatus.SHIPPED],
    OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: [],
}


class OrderService:
    
    def __init__(
        self,
        repository: OrderRepository,
        product_client: ProductServiceClient,
        payment_repository: Optional[PaymentRepository] = None,
        payment_service: Optional[PaymentService] = None
    ):
        self.repository = repository
        self.product_client = product_client
        self.payment_repository = payment_repository
        self.payment_service = payment_service or PaymentService()
    
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
                    reserved_products.append((product_id, quantity))
                    
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
                
                if reserved_products:
                    logger.info(f"Releasing {len(reserved_products)} reserved products for order {order.id}")
                    release_errors = []
                    for product_id, quantity in reserved_products:
                        try:
                            await self.product_client.release_inventory(
                                product_id=product_id,
                                quantity=quantity,
                                order_id=str(order.id),
                                token=token
                            )
                            logger.info(
                                f"Released inventory for order {order.id}, "
                                f"product {product_id}, quantity {quantity}"
                            )
                        except Exception as release_error:
                            release_errors.append({
                                "product_id": product_id,
                                "quantity": quantity,
                                "error": str(release_error)
                            })
                            logger.error(
                                f"Failed to release inventory for order {order.id}, "
                                f"product {product_id}: {release_error}",
                                exc_info=True
                            )
                    
                    if release_errors:
                        logger.error(
                            f"ORDER CREATION FAILED - INVENTORY RELEASE FAILED - Manual review required. "
                            f"Order ID: {order.id}, Original error: {e}, "
                            f"Inventory release errors: {release_errors}"
                        )
                
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
    
    def list_orders(
        self,
        user_id: Optional[UUID] = None,
        page: int = 1,
        limit: int = 10
    ) -> Dict[str, Any]:
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 10
        
        skip = (page - 1) * limit
        orders, total = self.repository.list_orders(user_id=user_id, skip=skip, limit=limit)
        
        return {
            "orders": orders,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 0
        }
    
    def validate_status_transition(self, current_status: OrderStatus, new_status: OrderStatus) -> bool:     
        allowed_transitions = STATUS_TRANSITIONS.get(current_status, [])
        return new_status in allowed_transitions
    
    def update_order_status(
        self,
        order_id: UUID,
        new_status: OrderStatus
    ) -> Order:
        order = self.get_order_by_id(order_id)
        
        if order.status == new_status:
            return order
        
        if not self.validate_status_transition(order.status, new_status):
            raise ValueError(
                f"Invalid status transition from {order.status.value} to {new_status.value}. "
                f"Allowed transitions: {[s.value for s in STATUS_TRANSITIONS.get(order.status, [])]}"
            )
        
        updated_order = self.repository.update_order_status(order_id, new_status)
        if not updated_order:
            raise ValueError(f"Failed to update order {order_id}")
        
        self.repository.commit()
        logger.info(f"Order {order_id} status updated from {order.status.value} to {new_status.value}")
        return updated_order
    
    def cancel_order(self, order_id: UUID) -> Order:
        order = self.get_order_by_id(order_id)
        
        if order.status == OrderStatus.CANCELLED:
            return order
        
        cancelled_order = self.repository.cancel_order(order_id)
        if not cancelled_order:
            raise ValueError(f"Failed to cancel order {order_id}")
        
        self.repository.commit()
        logger.info(f"Order {order_id} cancelled")
        return cancelled_order
    
    async def process_payment(
        self,
        order_id: UUID,
        idempotency_key: str,
        payment_amount: Optional[float] = None,
        payment_method: Optional[str] = None,
        token: Optional[str] = None
    ) -> Dict[str, Any]:

        if not self.payment_repository:
            raise ValueError("Payment repository is required for payment processing")
        
        existing_payment = self.payment_repository.get_payment_by_idempotency_key(idempotency_key)
        if existing_payment:
            logger.info(f"Payment with idempotency key {idempotency_key} already exists. Returning existing payment.")
            order = self.repository.get_order_by_id(existing_payment.order_id)
            return {
                "payment_id": existing_payment.id,
                "order_id": existing_payment.order_id,
                "transaction_id": existing_payment.transaction_id or "pending",
                "status": existing_payment.status,
                "amount": float(existing_payment.amount),
                "payment_method": existing_payment.payment_method,
                "order_status": order.status.value
            }
        
        order = self.get_order_by_id(order_id)
        
        if order.status == OrderStatus.PAID:
            raise ValueError(f"Order {order_id} is already paid")
        
        if order.status == OrderStatus.CANCELLED:
            raise ValueError(f"Cannot pay for cancelled order {order_id}")
        
        amount = Decimal(str(payment_amount)) if payment_amount else Decimal(str(order.total))
        
        if abs(float(amount) - float(order.total)) > 0.01:
            raise ValueError(
                f"Payment amount {float(amount)} does not match order total {float(order.total)}"
            )
        
        payment = self.payment_repository.create_payment(
            order_id=order_id,
            idempotency_key=idempotency_key,
            amount=float(amount),
            payment_method=payment_method,
            status="pending"
        )
        
        try:
            payment_result = await self.payment_service.process_payment(
                order_id=order_id,
                amount=amount,
                payment_method=payment_method
            )
            
            payment = self.payment_repository.update_payment_status(
                payment_id=payment.id,
                status=payment_result["status"],
                transaction_id=payment_result["transaction_id"]
            )
            
            if payment_result["status"] == "succeeded":
                updated_order = self.repository.update_order_status(order_id, OrderStatus.PAID)
                self.repository.commit()
                self.payment_repository.commit()
                logger.info(f"Payment successful for order {order_id}, transaction_id: {payment_result['transaction_id']}")
                
                return {
                    "payment_id": payment.id,
                    "order_id": order_id,
                    "transaction_id": payment_result["transaction_id"],
                    "status": "succeeded",
                    "amount": float(amount),
                    "payment_method": payment_result.get("payment_method"),
                    "order_status": updated_order.status.value
                }
            else:
                self.payment_repository.commit()
                payment_error = ValueError(f"Payment processing failed with status: {payment_result['status']}")
                
                await self._rollback_order_inventory(order_id, token, payment_error)
                raise payment_error
                
        except Exception as e:
            self.payment_repository.rollback()
            self.repository.rollback()
            logger.error(f"Error processing payment for order {order_id}: {e}")
            
            await self._rollback_order_inventory(order_id, token, e)
            raise
    
    async def _rollback_order_inventory(
        self,
        order_id: UUID,
        token: Optional[str],
        original_error: Exception
    ):
        try:
            order = self.repository.get_order_by_id(order_id)
            if not order:
                logger.warning(f"Order {order_id} not found for inventory rollback")
                return
            
            if not order.items or order.status in [OrderStatus.CANCELLED, OrderStatus.DELIVERED]:
                logger.info(f"Order {order_id} has no items or is already {order.status.value}, skipping inventory release")
                return
            
            if not token:
                logger.warning(
                    f"Payment failed for order {order_id}, but no token available for inventory release. "
                    f"Manual review required. Original error: {original_error}"
                )
                return
            
            release_errors = []
            for item in order.items:
                try:
                    await self.product_client.release_inventory(
                        product_id=item.product_id,
                        quantity=item.quantity,
                        order_id=str(order_id),
                        token=token
                    )
                    logger.info(
                        f"Released inventory for order {order_id}, "
                        f"product {item.product_id}, quantity {item.quantity}"
                    )
                except Exception as release_error:
                    release_errors.append({
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "error": str(release_error)
                    })
                    logger.error(
                        f"Failed to release inventory for order {order_id}, "
                        f"product {item.product_id}: {release_error}",
                        exc_info=True
                    )
            
            if release_errors:
                logger.error(
                    f"PAYMENT FAILURE - INVENTORY RELEASE FAILED - Manual review required. "
                    f"Order ID: {order_id}, Payment error: {original_error}, "
                    f"Inventory release errors: {release_errors}"
                )
            
        except Exception as rollback_error:
            logger.error(
                f"PAYMENT FAILURE - INVENTORY ROLLBACK FAILED - Manual review required. "
                f"Order ID: {order_id}, Payment error: {original_error}, "
                f"Rollback error: {rollback_error}",
                exc_info=True
            )


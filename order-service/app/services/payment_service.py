from uuid import UUID
from typing import Optional, Dict, Any
from decimal import Decimal
import os

from shared.logging_config import get_logger

logger = get_logger(__name__, "order-service")


class PaymentService:
    """
    Payment service that supports both mock payment gateway (for portfolio)
    and Stripe test mode.
    """
    
    def __init__(self):
        self.use_stripe = os.getenv("USE_STRIPE", "false").lower() == "true"
        self.stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
        
        if self.use_stripe and not self.stripe_secret_key:
            logger.warning("USE_STRIPE is true but STRIPE_SECRET_KEY is not set. Falling back to mock payment.")
            self.use_stripe = False
    
    async def process_payment(
        self,
        order_id: UUID,
        amount: Decimal,
        payment_method: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:

        if self.use_stripe:
            return await self._process_stripe_payment(order_id, amount, payment_method, **kwargs)
        else:
            return await self._process_mock_payment(order_id, amount, payment_method, **kwargs)
    
    async def _process_mock_payment(
        self,
        order_id: UUID,
        amount: Decimal,
        payment_method: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        logger.info(f"Processing mock payment for order {order_id}, amount: {amount}")
        
        import asyncio
        await asyncio.sleep(0.1)
        
        transaction_id = f"mock_txn_{order_id}_{int(asyncio.get_event_loop().time() * 1000)}"
        
        logger.info(f"Mock payment successful for order {order_id}, transaction_id: {transaction_id}")
        
        return {
            "transaction_id": transaction_id,
            "status": "succeeded",
            "payment_method": payment_method or "mock",
            "amount": float(amount),
            "gateway": "mock"
        }
    
    async def _process_stripe_payment(
        self,
        order_id: UUID,
        amount: Decimal,
        payment_method: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:

        try:
            import stripe
            
            stripe.api_key = self.stripe_secret_key
            
            amount_cents = int(float(amount) * 100)
            
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                metadata={
                    "order_id": str(order_id),
                    "payment_method": payment_method or "card"
                }
            )
            
            if payment_intent.status == "succeeded":
                transaction_id = payment_intent.id
                status = "succeeded"
            else:
                payment_intent = stripe.PaymentIntent.confirm(payment_intent.id)
                transaction_id = payment_intent.id
                status = payment_intent.status
            
            logger.info(f"Stripe payment processed for order {order_id}, transaction_id: {transaction_id}")
            
            return {
                "transaction_id": transaction_id,
                "status": status,
                "payment_method": payment_method or "card",
                "amount": float(amount),
                "gateway": "stripe"
            }
            
        except ImportError:
            logger.error("Stripe library not installed. Install with: pip install stripe")
            raise ValueError("Stripe payment processing is not available")
        except Exception as e:
            logger.error(f"Stripe payment processing failed for order {order_id}: {e}")
            raise ValueError(f"Payment processing failed: {str(e)}")
    
    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        **kwargs
    ) -> Dict[str, Any]:

        if self.use_stripe:
            return await self._refund_stripe_payment(transaction_id, amount, **kwargs)
        else:
            return await self._refund_mock_payment(transaction_id, amount, **kwargs)
    
    async def _refund_mock_payment(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        **kwargs
    ) -> Dict[str, Any]:

        logger.info(f"Processing mock refund for transaction {transaction_id}, amount: {amount}")
        
        import asyncio
        await asyncio.sleep(0.1)
        
        refund_id = f"mock_refund_{transaction_id}_{int(asyncio.get_event_loop().time() * 1000)}"
        
        logger.info(f"Mock refund successful for transaction {transaction_id}, refund_id: {refund_id}")
        
        return {
            "refund_id": refund_id,
            "transaction_id": transaction_id,
            "status": "succeeded",
            "amount": float(amount) if amount else None,
            "gateway": "mock"
        }
    
    async def _refund_stripe_payment(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        **kwargs
    ) -> Dict[str, Any]:

        try:
            import stripe
            
            stripe.api_key = self.stripe_secret_key
            
            amount_cents = int(float(amount) * 100) if amount else None
            
            refund_params = {"payment_intent": transaction_id}
            if amount_cents:
                refund_params["amount"] = amount_cents
            
            refund = stripe.Refund.create(**refund_params)
            
            logger.info(f"Stripe refund processed for transaction {transaction_id}, refund_id: {refund.id}")
            
            return {
                "refund_id": refund.id,
                "transaction_id": transaction_id,
                "status": refund.status,
                "amount": float(amount) if amount else None,
                "gateway": "stripe"
            }
            
        except ImportError:
            logger.error("Stripe library not installed. Install with: pip install stripe")
            raise ValueError("Stripe payment processing is not available")
        except Exception as e:
            logger.error(f"Stripe refund processing failed for transaction {transaction_id}: {e}")
            raise ValueError(f"Refund processing failed: {str(e)}")


from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from app.core.dependencies import require_auth, require_role
from app.core.product_client import get_product_client, ProductServiceClient
from app.repositories.order_repository import OrderRepository
from app.services.order_service import OrderService
from app.schemas import OrderCreateRequest, OrderResponse, OrderItemResponse
from shared.logging_config import get_logger

logger = get_logger(__name__, "order-service")

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])
security = HTTPBearer()


def get_order_repository(db: Session = Depends(get_db)) -> OrderRepository:
    return OrderRepository(db)


def get_order_service(
    repository: OrderRepository = Depends(get_order_repository),
    product_client: ProductServiceClient = Depends(get_product_client)
) -> OrderService: 
    return OrderService(repository, product_client)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
    description="Create a new order for the authenticated customer. Validates cart items, checks inventory, reserves inventory, and creates the order."
)
async def create_order(
    order_data: OrderCreateRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: Dict[str, Any] = Depends(require_auth),
    _: None = Depends(require_role("Customer")),
    order_service: OrderService = Depends(get_order_service),
    db: Session = Depends(get_db)
):

    try:
        user_id = current_user["user_id"]
        token = credentials.credentials
        
        cart_items = [
            {"product_id": item.product_id, "quantity": item.quantity}
            for item in order_data.items
        ]
        
        order = await order_service.create_order(
            user_id=user_id,
            cart_items=cart_items,
            token=token
        )
        
        db.refresh(order)
        
        from app.core.events import publish_order_created_event
        await publish_order_created_event(order)
        
        return OrderResponse(
            id=order.id,
            user_id=order.user_id,
            status=order.status,
            total=float(order.total),
            created_at=order.created_at,
            updated_at=order.updated_at,
            items=[
                OrderItemResponse(
                    id=item.id,
                    product_id=item.product_id,
                    sku=item.sku,
                    quantity=item.quantity,
                    price=float(item.price)
                )
                for item in order.items
            ]
        )
        
    except ValueError as e:
        logger.warning(f"Validation error creating order: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating order: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the order"
        )


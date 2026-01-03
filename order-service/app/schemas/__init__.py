from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime
from app.models import OrderStatus


class CartItem(BaseModel):
    product_id: str = Field(..., description="Product ID")
    quantity: int = Field(..., gt=0, description="Quantity")


class OrderCreateRequest(BaseModel):
    items: List[CartItem] = Field(..., min_items=1, description="Cart items")


class OrderItemResponse(BaseModel):
    id: UUID
    product_id: str
    sku: str
    quantity: int
    price: float
    
    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: UUID
    user_id: UUID
    status: OrderStatus
    total: float
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse]
    
    class Config:
        from_attributes = True


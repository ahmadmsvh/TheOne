from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime
from app.models import OrderStatus


class CartItem(BaseModel):
    """Cart item for order creation"""
    product_id: str = Field(..., description="Product ID")
    quantity: int = Field(..., gt=0, description="Quantity")


class OrderCreateRequest(BaseModel):
    """Request schema for creating an order"""
    items: List[CartItem] = Field(..., min_items=1, description="Cart items")


class OrderItemResponse(BaseModel):
    """Order item response"""
    id: UUID
    product_id: str  # MongoDB ObjectId as string
    sku: str
    quantity: int
    price: float
    
    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Order response"""
    id: UUID
    user_id: UUID
    status: OrderStatus
    total: float
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse]
    
    class Config:
        from_attributes = True


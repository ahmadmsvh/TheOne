import uuid
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
import os
from shared.logging_config import get_logger
from app.models import Product, ProductStatus
from app.schemas import ProductCreateRequest, ProductUpdateRequest
from app.repositories.product_repository import ProductRepository
from app.services.event_publisher import get_event_publisher

logger = get_logger(__name__, os.getenv("SERVICE_NAME"))


class ProductService:

    def __init__(self, database: AsyncIOMotorDatabase):
        self.repository = ProductRepository(database)
        self.event_publisher = get_event_publisher()
    
    def generate_sku(self) -> str:
        return f"PRD-{uuid.uuid4().hex[:8].upper()}"
    
    async def create_product(
        self,
        product_data: ProductCreateRequest,
        user_id: str,
        vendor_id: Optional[str] = None
    ) -> Product:
        if not product_data.sku:
            sku = self.generate_sku()
            while await self.repository.sku_exists(sku):
                sku = self.generate_sku()
            product_data.sku = sku
        else:
            if await self.repository.sku_exists(product_data.sku):
                raise ValueError(f"Product with SKU '{product_data.sku}' already exists")
        
        if vendor_id:
            product_data.vendor_id = vendor_id
        
        product = await self.repository.create(product_data, user_id)
        logger.info(f"Product created: {product.id} (SKU: {product.sku})")
        
        try:
            await self.event_publisher.publish_product_created(product)
        except Exception as e:
            logger.error(f"Failed to publish product.created event: {e}", exc_info=True)
        
        return product
    
    async def get_product(self, product_id: str) -> Optional[Product]:
        return await self.repository.get_by_id(product_id)
    
    async def list_products(
        self,
        page: int = 1,
        limit: int = 10,
        category: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None
    ) -> dict:
        skip = (page - 1) * limit
        
        products, total = await self.repository.list(
            skip=skip,
            limit=limit,
            category=category,
            search=search,
            status=status
        )
        
        return {
            "products": products,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 0
        }
    
    async def update_product(
        self,
        product_id: str,
        product_data: ProductUpdateRequest,
        user_id: str,
        user_roles: list[str]
    ) -> Optional[Product]:
        product = await self.repository.get_by_id(product_id)
        if not product:
            return None
        
        if "Vendor" in user_roles and "Admin" not in user_roles:
            if product.vendor_id and product.vendor_id != user_id:
                raise PermissionError("You can only update your own products")
        
        if product_data.sku and product_data.sku != product.sku:
            if await self.repository.sku_exists(product_data.sku, exclude_id=product_id):
                raise ValueError(f"Product with SKU '{product_data.sku}' already exists")
        
        updated_product = await self.repository.update(product_id, product_data, user_id)
        
        if updated_product:
            try:
                await self.event_publisher.publish_product_updated(updated_product)
            except Exception as e:
                logger.error(f"Failed to publish product.updated event: {e}", exc_info=True)
        
        return updated_product
    
    async def delete_product(self, product_id: str) -> bool:
        return await self.repository.delete(product_id)
    
    async def adjust_inventory(
        self,
        product_id: str,
        quantity: int,
        user_id: str,
        user_roles: list[str]
    ) -> Optional[Product]:
        product = await self.repository.get_by_id(product_id)
        if not product:
            return None
        
        if "Vendor" in user_roles and "Admin" not in user_roles:
            if product.vendor_id and product.vendor_id != user_id:
                raise PermissionError("You can only adjust inventory for your own products")
        
        old_stock = product.stock
        
        updated_product = await self.repository.adjust_stock(product_id, quantity)
        
        if updated_product:
            try:
                quantity_change = updated_product.stock - old_stock
                await self.event_publisher.publish_inventory_updated(updated_product, quantity_change)
            except Exception as e:
                logger.error(f"Failed to publish inventory.updated event: {e}", exc_info=True)
        
        return updated_product
    
    async def get_inventory(self, product_id: str) -> Optional[dict]:
        product = await self.repository.get_by_id(product_id)
        if not product:
            return None
        
        available_stock = product.stock - product.reserved_stock
        
        return {
            "product_id": str(product.id),
            "total_stock": product.stock,
            "reserved_stock": product.reserved_stock,
            "available_stock": available_stock,
            "status": product.status
        }
    
    async def reserve_inventory(
        self,
        product_id: str,
        quantity: int,
        order_id: Optional[str] = None
    ) -> Optional[Product]:
        product = await self.repository.get_by_id(product_id)
        if not product:
            return None
        
        if product.status != ProductStatus.ACTIVE:
            raise ValueError(f"Cannot reserve inventory for product with status: {product.status}")
        
        updated_product = await self.repository.reserve_stock(product_id, quantity)
        
        if updated_product:
            try:
                await self.event_publisher.publish_inventory_reserved(
                    updated_product, 
                    quantity, 
                    order_id=order_id
                )
            except Exception as e:
                logger.error(f"Failed to publish inventory.reserved event: {e}", exc_info=True)
        
        return updated_product
    
    async def release_inventory(
        self,
        product_id: str,
        quantity: int,
        order_id: Optional[str] = None
    ) -> Optional[Product]:
        product = await self.repository.get_by_id(product_id)
        if not product:
            return None
        
        updated_product = await self.repository.release_stock(product_id, quantity)
        
        if updated_product:
            try:
                await self.event_publisher.publish_inventory_released(
                    updated_product, 
                    quantity, 
                    order_id=order_id
                )
            except Exception as e:
                logger.error(f"Failed to publish inventory.released event: {e}", exc_info=True)
        
        return updated_product


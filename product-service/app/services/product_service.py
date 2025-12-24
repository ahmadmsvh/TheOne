"""
Product service with business logic
"""
import uuid
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
import sys
from pathlib import Path

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from shared.logging_config import get_logger
from app.models import Product, ProductCreate, ProductUpdate
from app.repositories.product_repository import ProductRepository

logger = get_logger(__name__, "product-service")


class ProductService:
    """Service for product business logic"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.repository = ProductRepository(database)
    
    def generate_sku(self) -> str:
        """Generate a unique SKU"""
        # Generate a unique SKU using UUID (first 8 characters)
        return f"PRD-{uuid.uuid4().hex[:8].upper()}"
    
    async def create_product(
        self,
        product_data: ProductCreate,
        user_id: str,
        vendor_id: Optional[str] = None
    ) -> Product:
        """Create a new product with business logic"""
        # Generate SKU if not provided
        if not product_data.sku:
            sku = self.generate_sku()
            # Ensure SKU is unique
            while await self.repository.sku_exists(sku):
                sku = self.generate_sku()
            product_data.sku = sku
        else:
            # Check if SKU already exists
            if await self.repository.sku_exists(product_data.sku):
                raise ValueError(f"Product with SKU '{product_data.sku}' already exists")
        
        # Set vendor_id if provided
        if vendor_id:
            # Update the product data to include vendor_id
            product_dict = product_data.model_dump(exclude_none=True)
            product_dict["vendor_id"] = vendor_id
            product_data = ProductCreate(**product_dict)
        
        # Create product
        product = await self.repository.create(product_data, user_id)
        logger.info(f"Product created: {product.id} (SKU: {product.sku})")
        return product
    
    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get a product by ID"""
        return await self.repository.get_by_id(product_id)
    
    async def list_products(
        self,
        page: int = 1,
        limit: int = 10,
        category: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None
    ) -> dict:
        """List products with pagination"""
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
        product_data: ProductUpdate,
        user_id: str,
        user_roles: list[str]
    ) -> Optional[Product]:
        """Update a product with authorization checks"""
        # Check if product exists
        product = await self.repository.get_by_id(product_id)
        if not product:
            return None
        
        # If user is vendor, ensure they own the product
        if "Vendor" in user_roles and "Admin" not in user_roles:
            if product.vendor_id and product.vendor_id != user_id:
                raise PermissionError("You can only update your own products")
        
        # If SKU is being updated, check uniqueness
        if product_data.sku and product_data.sku != product.sku:
            if await self.repository.sku_exists(product_data.sku, exclude_id=product_id):
                raise ValueError(f"Product with SKU '{product_data.sku}' already exists")
        
        return await self.repository.update(product_id, product_data, user_id)
    
    async def delete_product(self, product_id: str) -> bool:
        """Delete a product"""
        return await self.repository.delete(product_id)


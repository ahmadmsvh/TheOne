"""
Product repository for MongoDB operations
"""
from typing import Optional, List, Dict, Any
from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
import sys
from pathlib import Path

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from shared.logging_config import get_logger
from app.models import Product, ProductCreate, ProductUpdate

logger = get_logger(__name__, "product-service")


class ProductRepository:
    """Repository for product database operations"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.collection = database.products
    
    async def create(self, product_data: ProductCreate, user_id: str) -> Product:
        """Create a new product"""
        try:
            product_dict = product_data.model_dump(exclude_none=True)
            product_dict["created_at"] = datetime.utcnow()
            product_dict["updated_at"] = datetime.utcnow()
            product_dict["created_by"] = user_id
            
            result = await self.collection.insert_one(product_dict)
            created = await self.collection.find_one({"_id": result.inserted_id})
            
            return Product(**created, _id=created["_id"])
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            raise
    
    async def get_by_id(self, product_id: str) -> Optional[Product]:
        """Get product by ID"""
        try:
            if not ObjectId.is_valid(product_id):
                return None
            
            product = await self.collection.find_one({"_id": ObjectId(product_id)})
            if not product:
                return None
            
            return Product(**product, _id=product["_id"])
        except (InvalidId, Exception) as e:
            logger.error(f"Error getting product by ID {product_id}: {e}")
            return None
    
    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU"""
        try:
            product = await self.collection.find_one({"sku": sku})
            if not product:
                return None
            
            return Product(**product, _id=product["_id"])
        except Exception as e:
            logger.error(f"Error getting product by SKU {sku}: {e}")
            return None
    
    async def list(
        self,
        skip: int = 0,
        limit: int = 10,
        category: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None
    ) -> tuple[List[Product], int]:
        """List products with pagination and filters"""
        try:
            query: Dict[str, Any] = {}
            
            # Apply filters
            if category:
                query["category"] = category
            if status:
                query["status"] = status
            if search:
                query["$text"] = {"$search": search}
            
            # Get total count
            total = await self.collection.count_documents(query)
            
            # Get products
            cursor = self.collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
            products = await cursor.to_list(length=limit)
            
            product_list = [Product(**p, _id=p["_id"]) for p in products]
            return product_list, total
        except Exception as e:
            logger.error(f"Error listing products: {e}")
            raise
    
    async def update(self, product_id: str, product_data: ProductUpdate, user_id: str) -> Optional[Product]:
        """Update a product"""
        try:
            if not ObjectId.is_valid(product_id):
                return None
            
            update_dict = product_data.model_dump(exclude_none=True)
            update_dict["updated_at"] = datetime.utcnow()
            update_dict["updated_by"] = user_id
            
            result = await self.collection.update_one(
                {"_id": ObjectId(product_id)},
                {"$set": update_dict}
            )
            
            if result.matched_count == 0:
                return None
            
            updated = await self.collection.find_one({"_id": ObjectId(product_id)})
            return Product(**updated, _id=updated["_id"])
        except (InvalidId, Exception) as e:
            logger.error(f"Error updating product {product_id}: {e}")
            return None
    
    async def delete(self, product_id: str) -> bool:
        """Delete a product"""
        try:
            if not ObjectId.is_valid(product_id):
                return False
            
            result = await self.collection.delete_one({"_id": ObjectId(product_id)})
            return result.deleted_count > 0
        except (InvalidId, Exception) as e:
            logger.error(f"Error deleting product {product_id}: {e}")
            return False
    
    async def sku_exists(self, sku: str, exclude_id: Optional[str] = None) -> bool:
        """Check if SKU already exists"""
        try:
            query: Dict[str, Any] = {"sku": sku}
            if exclude_id and ObjectId.is_valid(exclude_id):
                query["_id"] = {"$ne": ObjectId(exclude_id)}
            
            count = await self.collection.count_documents(query)
            return count > 0
        except Exception as e:
            logger.error(f"Error checking SKU existence: {e}")
            return False


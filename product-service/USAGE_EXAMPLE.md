# MongoDB Connection Usage Examples

This document provides examples of how to use the MongoDB connection and product models in the product-service.

## Setup

### Environment Variables

Create a `.env` file in the `shared/` directory or set environment variables:

```bash
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=product_db
```

### Initialize Database Connection

```python
from app.core.database import get_db_manager

# Get database manager instance
db_manager = get_db_manager()

# Connect to MongoDB (async)
await db_manager.connect()

# Create indexes (one-time setup)
await db_manager.create_indexes()
```

## Using with Flask (Async Routes)

Since Flask doesn't natively support async, you can use Flask with async support or convert to sync:

### Option 1: Using Flask with async support (Flask 2.0+)

```python
from flask import Flask
from app.core.database import get_database
from app.models import Product, ProductCreate, ProductStatus

app = Flask(__name__)

@app.route('/products', methods=['POST'])
async def create_product():
    db = await get_database()
    
    product_data = ProductCreate(
        name="Example Product",
        description="This is an example product",
        price=29.99,
        stock=100,
        status=ProductStatus.ACTIVE,
        category="electronics"
    )
    
    # Convert to dict for MongoDB
    product_dict = product_data.model_dump(exclude_none=True)
    product_dict["created_at"] = datetime.utcnow()
    product_dict["updated_at"] = datetime.utcnow()
    
    # Insert into MongoDB
    result = await db.products.insert_one(product_dict)
    
    # Fetch the created product
    created_product = await db.products.find_one({"_id": result.inserted_id})
    
    return {"id": str(created_product["_id"]), "name": created_product["name"]}
```

### Option 2: Using sync wrapper (for Flask compatibility)

```python
import asyncio
from flask import Flask
from app.core.database import get_database
from app.models import Product, ProductCreate

app = Flask(__name__)

def run_async(coro):
    """Helper to run async functions in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@app.route('/products/<product_id>')
def get_product(product_id):
    async def _get_product():
        db = await get_database()
        from bson import ObjectId
        
        product = await db.products.find_one({"_id": ObjectId(product_id)})
        if product:
            return Product(**product).model_dump()
        return None
    
    product = run_async(_get_product())
    if product:
        return product
    return {"error": "Product not found"}, 404
```

## Using with FastAPI (Recommended)

If you migrate to FastAPI, async support is native:

```python
from fastapi import FastAPI, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.models import Product, ProductCreate, ProductUpdate, ProductResponse
from bson import ObjectId
from datetime import datetime

app = FastAPI()

@app.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(
    product_data: ProductCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new product"""
    product_dict = product_data.model_dump(exclude_none=True)
    product_dict["created_at"] = datetime.utcnow()
    product_dict["updated_at"] = datetime.utcnow()
    
    result = await db.products.insert_one(product_dict)
    created = await db.products.find_one({"_id": result.inserted_id})
    
    return ProductResponse(**created, _id=str(created["_id"]))

@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get a product by ID"""
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID")
    
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return ProductResponse(**product, _id=str(product["_id"]))

@app.get("/products", response_model=list[ProductResponse])
async def list_products(
    skip: int = 0,
    limit: int = 10,
    category: str = None,
    status: str = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List products with filtering"""
    query = {}
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    
    cursor = db.products.find(query).skip(skip).limit(limit)
    products = await cursor.to_list(length=limit)
    
    return [ProductResponse(**p, _id=str(p["_id"])) for p in products]

@app.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update a product"""
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID")
    
    update_dict = product_data.model_dump(exclude_none=True)
    update_dict["updated_at"] = datetime.utcnow()
    
    result = await db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    updated = await db.products.find_one({"_id": ObjectId(product_id)})
    return ProductResponse(**updated, _id=str(updated["_id"]))

@app.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete a product"""
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID")
    
    result = await db.products.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return None
```

## Common Operations

### Search Products

```python
async def search_products(search_term: str, db: AsyncIOMotorDatabase):
    """Search products by name or description"""
    query = {"$text": {"$search": search_term}}
    cursor = db.products.find(query)
    products = await cursor.to_list(length=100)
    return [Product(**p) for p in products]
```

### Update Stock

```python
async def update_stock(product_id: str, quantity: int, db: AsyncIOMotorDatabase):
    """Update product stock"""
    from bson import ObjectId
    
    result = await db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$inc": {"stock": quantity}, "$set": {"updated_at": datetime.utcnow()}}
    )
    return result.modified_count > 0
```

### Get Products by Category

```python
async def get_products_by_category(category: str, db: AsyncIOMotorDatabase):
    """Get all products in a category"""
    cursor = db.products.find({"category": category})
    products = await cursor.to_list(length=1000)
    return [Product(**p) for p in products]
```

### Health Check

```python
async def health_check():
    """Check MongoDB connection health"""
    db_manager = get_db_manager()
    is_healthy = await db_manager.health_check()
    return {"mongodb": "healthy" if is_healthy else "unhealthy"}
```

## Error Handling

```python
from pymongo.errors import DuplicateKeyError, ConnectionFailure

async def create_product_safe(product_data: ProductCreate, db: AsyncIOMotorDatabase):
    """Create product with error handling"""
    try:
        product_dict = product_data.model_dump(exclude_none=True)
        result = await db.products.insert_one(product_dict)
        return {"success": True, "id": str(result.inserted_id)}
    except DuplicateKeyError:
        return {"success": False, "error": "Product with this SKU already exists"}
    except ConnectionFailure:
        return {"success": False, "error": "Database connection failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## Closing Connections

```python
# At application shutdown
async def shutdown():
    db_manager = get_db_manager()
    await db_manager.close()
```


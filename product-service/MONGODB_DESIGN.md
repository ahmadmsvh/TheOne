# MongoDB Collections Design for Product Service

## Overview
This document describes the MongoDB collections design for the product-service, following best practices for document-based databases.

## Collections

### 1. Products Collection

**Collection Name:** `products`

**Purpose:** Store product information including details, pricing, inventory, and metadata.

**Schema:**
```json
{
  "_id": ObjectId,
  "name": String (required, indexed, text search),
  "description": String (optional),
  "sku": String (optional, unique, sparse index),
  "price": Number (required, > 0, indexed),
  "compare_at_price": Number (optional, > price),
  "cost_price": Number (optional, internal),
  "stock": Integer (default: 0, >= 0),
  "status": String (enum: active, inactive, out_of_stock, discontinued, draft),
  "category": String (optional, indexed),
  "categories": Array[String] (optional, for multiple categories),
  "tags": Array[String] (optional),
  "images": Array[{
    "url": String,
    "alt_text": String,
    "is_primary": Boolean,
    "order": Integer
  }],
  "variants": Array[{
    "name": String,
    "value": String,
    "sku": String,
    "price_modifier": Number,
    "stock": Integer
  }],
  "weight": Number (optional, kg),
  "dimensions": {
    "length": Number,
    "width": Number,
    "height": Number
  },
  "brand": String (optional),
  "vendor": String (optional),
  "barcode": String (optional),
  "metadata": Object (flexible, for additional fields),
  "created_at": ISODate (indexed),
  "updated_at": ISODate (indexed),
  "created_by": String (optional, user ID),
  "updated_by": String (optional, user ID)
}
```

**Indexes:**
- `_id`: Primary key (automatic)
- `sku`: Unique, sparse index (allows nulls)
- `name`: Single field index
- `category`: Single field index
- `status`: Single field index
- `price`: Single field index (for range queries)
- `name + description`: Text search index (compound)
- `created_at`: Single field index (for sorting)
- `updated_at`: Single field index (for sorting)

**Query Patterns:**
- Find by SKU (unique lookup)
- Search by name/description (text search)
- Filter by category
- Filter by status
- Filter by price range
- Sort by created_at/updated_at
- Filter by tags
- Filter by stock level

### 2. Categories Collection (Future)

**Collection Name:** `categories`

**Purpose:** Store product categories with hierarchical structure.

**Schema:**
```json
{
  "_id": ObjectId,
  "name": String (required, unique),
  "slug": String (required, unique, URL-friendly),
  "description": String (optional),
  "parent_id": ObjectId (optional, for nested categories),
  "image": String (optional, category image URL),
  "metadata": Object,
  "created_at": ISODate,
  "updated_at": ISODate
}
```

**Indexes:**
- `_id`: Primary key
- `name`: Unique index
- `slug`: Unique index
- `parent_id`: Single field index (for hierarchy queries)

### 3. Inventory History Collection (Future)

**Collection Name:** `inventory_history`

**Purpose:** Track inventory changes for audit and analytics.

**Schema:**
```json
{
  "_id": ObjectId,
  "product_id": ObjectId (required, indexed),
  "change_type": String (enum: sale, restock, adjustment, return),
  "quantity_change": Integer (positive or negative),
  "previous_stock": Integer,
  "new_stock": Integer,
  "reason": String (optional),
  "order_id": String (optional),
  "created_by": String (optional),
  "created_at": ISODate (indexed)
}
```

**Indexes:**
- `product_id`: Single field index
- `created_at`: Single field index
- `product_id + created_at`: Compound index

## Design Decisions

### 1. Embedded vs Referenced Documents

**Products Collection:**
- **Embedded:** Images, Variants, Dimensions (small, frequently accessed together)
- **Referenced:** Categories (can be large, shared across products)

### 2. Indexing Strategy

- **Unique Indexes:** SKU (sparse to allow nulls)
- **Single Field Indexes:** Frequently queried fields (name, category, status, price)
- **Text Search Index:** For full-text search on name and description
- **Compound Indexes:** For complex queries (e.g., category + status + price range)

### 3. Data Types

- **Prices:** Stored as Number (Float) - consider Decimal128 for precision in production
- **Timestamps:** ISODate for proper date handling
- **IDs:** ObjectId for MongoDB native IDs, String for external IDs (user_id, order_id)

### 4. Status Enumeration

Product status values:
- `draft`: Product is being created/edited
- `active`: Product is available for purchase
- `inactive`: Product is temporarily unavailable
- `out_of_stock`: Product has no stock
- `discontinued`: Product is no longer sold

### 5. Variants Structure

Products can have multiple variants (size, color, etc.):
- Each variant can have its own SKU, price modifier, and stock level
- Variants are embedded in the product document for fast access
- For complex variant systems, consider a separate collection

## Connection Configuration

The MongoDB connection uses Motor (async driver) with the following settings:
- **Connection Pool:** minPoolSize=10, maxPoolSize=50
- **Timeout:** serverSelectionTimeoutMS=5000
- **Database:** Configurable via `MONGODB_DATABASE` environment variable
- **URL:** Configurable via `MONGODB_URL` environment variable

## Environment Variables

```bash
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=product_db
```

## Best Practices

1. **Use Transactions:** For multi-document operations (when needed)
2. **Validate Data:** Use Pydantic models for validation before saving
3. **Handle Errors:** Proper error handling for connection failures
4. **Monitor Performance:** Use MongoDB explain() for query optimization
5. **Backup Strategy:** Regular backups of product data
6. **Index Management:** Monitor index usage and remove unused indexes
7. **Document Size:** Keep documents under 16MB (MongoDB limit)

## Future Enhancements

1. **Categories Collection:** Implement hierarchical category structure
2. **Inventory History:** Track all stock changes
3. **Product Reviews:** Separate collection for reviews
4. **Product Analytics:** Track views, purchases, etc.
5. **Search Optimization:** Implement Elasticsearch for advanced search
6. **Caching:** Use Redis for frequently accessed products


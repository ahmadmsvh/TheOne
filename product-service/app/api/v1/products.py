from flask import Blueprint, request, jsonify
from pydantic import ValidationError
import sys
from pathlib import Path

# Add shared to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "shared"))

from shared.logging_config import get_logger
from app.core.database import get_database
from app.core.auth import require_auth, require_role, require_any_role
from app.utils import async_route
from app.services.product_service import ProductService
from app.schemas import (
    ProductCreateRequest,
    ProductUpdateRequest,
    ProductResponse,
    ProductListResponse
)

logger = get_logger(__name__, "product-service")

bp = Blueprint("products", __name__, url_prefix="/api/v1/products")


@bp.route("", methods=["POST"])
@require_role("Vendor")
@async_route
async def create_product(current_user):
    """Create a new product (Vendor only)"""
    try:
        # Get database
        db = await get_database()
        service = ProductService(db)
        
        # Validate request data
        try:
            product_data = ProductCreateRequest(**request.json)
        except ValidationError as e:
            return jsonify({"error": "Validation error", "details": e.errors()}), 400
        
        # Convert to ProductCreate model
        from app.models import ProductCreate
        product_create = ProductCreate(**product_data.model_dump())
        
        # Get user ID and vendor ID from token
        user_id = current_user.get("sub")
        vendor_id = current_user.get("sub")  # Use user_id as vendor_id for now
        
        # Create product
        product = await service.create_product(
            product_data=product_create,
            user_id=user_id,
            vendor_id=vendor_id
        )
        
        # Return response
        response = ProductResponse.from_model(product)
        return jsonify(response.model_dump()), 201
        
    except ValueError as e:
        logger.warning(f"Validation error creating product: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("", methods=["GET"])
@async_route
async def list_products():
    """List products with pagination (Public access)"""
    try:
        # Get query parameters
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
        category = request.args.get("category")
        search = request.args.get("search")
        status = request.args.get("status")
        
        # Validate pagination
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 10
        
        # Get database
        db = await get_database()
        service = ProductService(db)
        
        # Get products
        result = await service.list_products(
            page=page,
            limit=limit,
            category=category,
            search=search,
            status=status
        )
        
        # Convert to response
        products_response = [ProductResponse.from_model(p).model_dump() for p in result["products"]]
        response = ProductListResponse(
            products=products_response,
            total=result["total"],
            page=result["page"],
            limit=result["limit"],
            pages=result["pages"]
        )
        
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        logger.error(f"Error listing products: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/<product_id>", methods=["GET"])
@async_route
async def get_product(product_id):
    """Get a single product"""
    try:
        # Get database
        db = await get_database()
        service = ProductService(db)
        
        # Get product
        product = await service.get_product(product_id)
        
        if not product:
            return jsonify({"error": "Product not found"}), 404
        
        # Return response
        response = ProductResponse.from_model(product)
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        logger.error(f"Error getting product: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/<product_id>", methods=["PUT"])
@require_any_role("Vendor", "Admin")
@async_route
async def update_product(product_id, current_user):
    """Update a product (Vendor/Admin)"""
    try:
        # Get database
        db = await get_database()
        service = ProductService(db)
        
        # Validate request data
        try:
            product_data = ProductUpdateRequest(**request.json)
        except ValidationError as e:
            return jsonify({"error": "Validation error", "details": e.errors()}), 400
        
        # Convert to ProductUpdate model
        from app.models import ProductUpdate
        product_update = ProductUpdate(**product_data.model_dump())
        
        # Get user ID and roles
        user_id = current_user.get("sub")
        user_roles = current_user.get("roles", [])
        
        # Update product
        try:
            product = await service.update_product(
                product_id=product_id,
                product_data=product_update,
                user_id=user_id,
                user_roles=user_roles
            )
        except PermissionError as e:
            return jsonify({"error": str(e)}), 403
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        
        if not product:
            return jsonify({"error": "Product not found"}), 404
        
        # Return response
        response = ProductResponse.from_model(product)
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        logger.error(f"Error updating product: {e}")
        return jsonify({"error": "Internal server error"}), 500


@bp.route("/<product_id>", methods=["DELETE"])
@require_role("Admin")
@async_route
async def delete_product(product_id, current_user):
    """Delete a product (Admin only)"""
    try:
        # Get database
        db = await get_database()
        service = ProductService(db)
        
        # Delete product
        deleted = await service.delete_product(product_id)
        
        if not deleted:
            return jsonify({"error": "Product not found"}), 404
        
        return jsonify({"message": "Product deleted successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error deleting product: {e}")
        return jsonify({"error": "Internal server error"}), 500


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database.connection import get_db
from app.database.models import Product, User, Tenant
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse,
    ProductSearchRequest, ProductSearchResult
)
from app.auth.dependencies import get_current_user, get_current_tenant
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["product-management"])


@router.post("/", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new product"""
    # Check tenant product limits
    product_count = db.query(Product).filter(
        Product.tenant_id == current_tenant.id
    ).count()
    if product_count >= current_tenant.max_products:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant has reached maximum product limit"
        )
    
    # Check if SKU already exists in tenant
    if product_data.sku:
        existing_product = db.query(Product).filter(
            Product.tenant_id == current_tenant.id,
            Product.sku == product_data.sku,
            Product.is_active == True
        ).first()
        if existing_product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product with this SKU already exists"
            )
    
    # Create product
    product = Product(
        tenant_id=current_tenant.id,
        name=product_data.name,
        description=product_data.description,
        category=product_data.category,
        price=product_data.price,
        currency=product_data.currency,
        sku=product_data.sku,
        stock_quantity=product_data.stock_quantity,
        specifications=product_data.specifications,
        meta_data=product_data.meta_data
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    # Add to vector store
    try:
        # Create searchable content from product info
        searchable_content = f"{product.name}"
        if product.description:
            searchable_content += f" {product.description}"
        if product.category:
            searchable_content += f" Category: {product.category}"
        if product.specifications:
            spec_text = " ".join([f"{k}: {v}" for k, v in product.specifications.items()])
            searchable_content += f" {spec_text}"
        
        vector_id = await vector_store.add_product(
            product.id,
            product.name,
            searchable_content,
            current_tenant.id,
            metadata={
                "category": product.category,
                "price": product.price,
                "currency": product.currency,
                "sku": product.sku,
                "stock_quantity": product.stock_quantity,
                **(product.meta_data or {})
            }
        )
        
        # Update with vector ID
        product.vector_id = vector_id
        db.commit()
        
    except Exception as e:
        logger.error(f"Error adding product to vector store: {e}")
        # Don't fail the creation, just log the error
    
    logger.info(f"Product created: {product.name} by {current_user.email}")
    return product


@router.get("/", response_model=List[ProductResponse])
async def list_products(
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    category: str = None,
    min_price: float = None,
    max_price: float = None,
    in_stock_only: bool = False,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """List products for tenant"""
    query = db.query(Product).filter(
        Product.tenant_id == current_tenant.id,
        Product.is_active == True
    )
    
    if search:
        query = query.filter(
            Product.name.contains(search) | 
            Product.description.contains(search)
        )
    
    if category:
        query = query.filter(Product.category == category)
    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    if in_stock_only:
        query = query.filter(Product.stock_quantity > 0)
    
    products = query.offset(skip).limit(limit).all()
    return products


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get specific product"""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == current_tenant.id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update product"""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == current_tenant.id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check SKU uniqueness if changing SKU
    if product_data.sku and product_data.sku != product.sku:
        existing_product = db.query(Product).filter(
            Product.tenant_id == current_tenant.id,
            Product.sku == product_data.sku,
            Product.is_active == True,
            Product.id != product_id
        ).first()
        if existing_product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product with this SKU already exists"
            )
    
    # Update fields
    update_data = product_data.dict(exclude_unset=True)
    content_changed = False
    
    for field, value in update_data.items():
        if field in ["name", "description", "category", "specifications"] and getattr(product, field) != value:
            content_changed = True
        setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    
    # Update vector store if content changed
    if content_changed and product.vector_id:
        try:
            searchable_content = f"{product.name}"
            if product.description:
                searchable_content += f" {product.description}"
            if product.category:
                searchable_content += f" Category: {product.category}"
            if product.specifications:
                spec_text = " ".join([f"{k}: {v}" for k, v in product.specifications.items()])
                searchable_content += f" {spec_text}"
            
            await vector_store.update_product(
                product.vector_id,
                product.name,
                searchable_content,
                current_tenant.id,
                metadata={
                    "category": product.category,
                    "price": product.price,
                    "currency": product.currency,
                    "sku": product.sku,
                    "stock_quantity": product.stock_quantity,
                    **(product.meta_data or {})
                }
            )
        except Exception as e:
            logger.error(f"Error updating product in vector store: {e}")
    
    logger.info(f"Product updated: {product.name} by {current_user.email}")
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete product"""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == current_tenant.id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Remove from vector store
    if product.vector_id:
        try:
            await vector_store.delete_product(product.vector_id, current_tenant.id)
        except Exception as e:
            logger.error(f"Error removing product from vector store: {e}")
    
    # Soft delete
    product.is_active = False
    db.commit()
    
    logger.info(f"Product deleted: {product.name} by {current_user.email}")
    return {"message": "Product deleted successfully"}


@router.post("/search", response_model=List[ProductSearchResult])
async def search_products(
    search_request: ProductSearchRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Search products using vector similarity"""
    try:
        # Search in vector store
        results = await vector_store.search_products(
            query=search_request.query,
            tenant_id=current_tenant.id,
            limit=search_request.limit,
            min_score=search_request.min_score,
            filters={
                "category": search_request.category,
                "min_price": search_request.min_price,
                "max_price": search_request.max_price
            }
        )
        
        # Get products from database
        search_results = []
        for result in results:
            product = db.query(Product).filter(
                Product.id == result["id"],
                Product.tenant_id == current_tenant.id,
                Product.is_active == True
            ).first()
            
            if product:
                # Additional filtering if needed
                if search_request.min_price and product.price and product.price < search_request.min_price:
                    continue
                if search_request.max_price and product.price and product.price > search_request.max_price:
                    continue
                if search_request.category and product.category != search_request.category:
                    continue
                
                search_results.append(ProductSearchResult(
                    product=product,
                    score=result["score"]
                ))
        
        return search_results
        
    except Exception as e:
        logger.error(f"Error searching products: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/categories/list")
async def list_product_categories(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """List all product categories in tenant"""
    categories = db.query(Product.category).filter(
        Product.tenant_id == current_tenant.id,
        Product.is_active == True,
        Product.category.isnot(None)
    ).distinct().all()
    
    return [c[0] for c in categories if c[0]]


@router.put("/{product_id}/stock", response_model=ProductResponse)
async def update_stock(
    product_id: str,
    stock_quantity: int,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update product stock quantity"""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == current_tenant.id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.stock_quantity = stock_quantity
    db.commit()
    db.refresh(product)
    
    logger.info(f"Stock updated for {product.name}: {stock_quantity} by {current_user.email}")
    return product 
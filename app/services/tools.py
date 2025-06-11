import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from app.database.models import Product, KnowledgeItem
from app.services.vector_store import vector_store
from app.services.openai_service import openai_service
import logging

logger = logging.getLogger(__name__)


class ToolsService:
    def __init__(self):
        self.available_tools = {
            "search_knowledge": self.search_knowledge,
            "search_products": self.search_products,
            "get_product_details": self.get_product_details,
            "search_products_by_category": self.search_products_by_category,
            "check_product_availability": self.check_product_availability
        }
    
    def get_tool_definitions(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get OpenAI function definitions for tools"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge",
                    "description": "Search through the knowledge base for relevant information and documentation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query for finding relevant knowledge"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 5)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_products",
                    "description": "Search for products by name, description, or specifications",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query for finding products"
                            },
                            "category": {
                                "type": "string",
                                "description": "Optional category filter"
                            },
                            "min_price": {
                                "type": "number",
                                "description": "Minimum price filter"
                            },
                            "max_price": {
                                "type": "number",
                                "description": "Maximum price filter"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 10)",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_product_details",
                    "description": "Get detailed information about a specific product",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_id": {
                                "type": "string",
                                "description": "The unique ID of the product"
                            }
                        },
                        "required": ["product_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_products_by_category",
                    "description": "Find products in a specific category",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "The product category to search in"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 10)",
                                "default": 10
                            }
                        },
                        "required": ["category"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_product_availability",
                    "description": "Check stock availability for a product",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_id": {
                                "type": "string",
                                "description": "The unique ID of the product"
                            }
                        },
                        "required": ["product_id"]
                    }
                }
            }
        ]
    
    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tenant_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Execute a tool function"""
        try:
            if tool_name not in self.available_tools:
                return {"error": f"Tool '{tool_name}' not found"}
            
            # Add tenant_id and db to arguments
            arguments["tenant_id"] = tenant_id
            arguments["db"] = db
            
            result = await self.available_tools[tool_name](**arguments)
            return {"success": True, "data": result}
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e)}
    
    async def search_knowledge(
        self,
        query: str,
        tenant_id: str,
        db: Session,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search knowledge base using vector similarity"""
        try:
            # Create embedding for query
            query_embedding = await openai_service.create_embedding(query)
            
            # Search in vector store
            results = await vector_store.search_documents(
                tenant_id=tenant_id,
                collection_type="knowledge",
                query_embedding=query_embedding,
                n_results=limit
            )
            
            # Get additional metadata from database
            knowledge_items = []
            for i, doc_id in enumerate(results["ids"]):
                knowledge_item = db.query(KnowledgeItem).filter(
                    KnowledgeItem.vector_id == doc_id,
                    KnowledgeItem.tenant_id == tenant_id,
                    KnowledgeItem.is_active == True
                ).first()
                
                if knowledge_item:
                    knowledge_items.append({
                        "id": knowledge_item.id,
                        "title": knowledge_item.title,
                        "content": results["documents"][i],
                        "source": knowledge_item.source,
                        "similarity_score": 1 - results["distances"][i],  # Convert distance to similarity
                        "metadata": knowledge_item.metadata
                    })
            
            return knowledge_items
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}")
            return []
    
    async def search_products(
        self,
        query: str,
        tenant_id: str,
        db: Session,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search products using hybrid approach (vector + database)"""
        try:
            # Vector search
            query_embedding = await openai_service.create_embedding(query)
            vector_results = await vector_store.search_documents(
                tenant_id=tenant_id,
                collection_type="products",
                query_embedding=query_embedding,
                n_results=limit * 2  # Get more for filtering
            )
            
            # Get product IDs from vector search
            vector_product_ids = []
            for doc_id in vector_results["ids"]:
                product = db.query(Product).filter(
                    Product.vector_id == doc_id,
                    Product.tenant_id == tenant_id,
                    Product.is_active == True
                ).first()
                if product:
                    vector_product_ids.append(product.id)
            
            # Database search with filters
            db_query = db.query(Product).filter(
                Product.tenant_id == tenant_id,
                Product.is_active == True
            )
            
            # Apply text search
            if query:
                db_query = db_query.filter(
                    or_(
                        Product.name.ilike(f"%{query}%"),
                        Product.description.ilike(f"%{query}%"),
                        Product.category.ilike(f"%{query}%")
                    )
                )
            
            # Apply filters
            if category:
                db_query = db_query.filter(Product.category.ilike(f"%{category}%"))
            if min_price is not None:
                db_query = db_query.filter(Product.price >= min_price)
            if max_price is not None:
                db_query = db_query.filter(Product.price <= max_price)
            
            db_products = db_query.limit(limit).all()
            
            # Combine and rank results
            products = []
            seen_ids = set()
            
            # First add vector search results (higher relevance)
            for product_id in vector_product_ids:
                if product_id not in seen_ids:
                    product = db.query(Product).filter(Product.id == product_id).first()
                    if product and self._matches_filters(product, category, min_price, max_price):
                        products.append(self._format_product(product, high_relevance=True))
                        seen_ids.add(product_id)
                        if len(products) >= limit:
                            break
            
            # Then add database search results
            for product in db_products:
                if product.id not in seen_ids:
                    products.append(self._format_product(product, high_relevance=False))
                    seen_ids.add(product.id)
                    if len(products) >= limit:
                        break
            
            return products
            
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return []
    
    async def get_product_details(
        self,
        product_id: str,
        tenant_id: str,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """Get detailed product information"""
        try:
            product = db.query(Product).filter(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
                Product.is_active == True
            ).first()
            
            if not product:
                return None
            
            return {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "category": product.category,
                "price": product.price,
                "currency": product.currency,
                "sku": product.sku,
                "stock_quantity": product.stock_quantity,
                "specifications": product.specifications,
                "metadata": product.metadata,
                "created_at": product.created_at.isoformat(),
                "updated_at": product.updated_at.isoformat() if product.updated_at else None
            }
            
        except Exception as e:
            logger.error(f"Error getting product details: {e}")
            return None
    
    async def search_products_by_category(
        self,
        category: str,
        tenant_id: str,
        db: Session,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search products by category"""
        try:
            products = db.query(Product).filter(
                Product.tenant_id == tenant_id,
                Product.category.ilike(f"%{category}%"),
                Product.is_active == True
            ).limit(limit).all()
            
            return [self._format_product(product) for product in products]
            
        except Exception as e:
            logger.error(f"Error searching products by category: {e}")
            return []
    
    async def check_product_availability(
        self,
        product_id: str,
        tenant_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Check product stock availability"""
        try:
            product = db.query(Product).filter(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
                Product.is_active == True
            ).first()
            
            if not product:
                return {"available": False, "message": "Product not found"}
            
            return {
                "available": product.stock_quantity > 0,
                "stock_quantity": product.stock_quantity,
                "product_name": product.name,
                "sku": product.sku
            }
            
        except Exception as e:
            logger.error(f"Error checking product availability: {e}")
            return {"available": False, "message": "Error checking availability"}
    
    def _matches_filters(
        self,
        product: Product,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> bool:
        """Check if product matches the given filters"""
        if category and category.lower() not in (product.category or "").lower():
            return False
        if min_price is not None and (product.price is None or product.price < min_price):
            return False
        if max_price is not None and (product.price is None or product.price > max_price):
            return False
        return True
    
    def _format_product(self, product: Product, high_relevance: bool = False) -> Dict[str, Any]:
        """Format product for response"""
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "category": product.category,
            "price": product.price,
            "currency": product.currency,
            "sku": product.sku,
            "stock_quantity": product.stock_quantity,
            "high_relevance": high_relevance
        }


# Global tools service instance
tools_service = ToolsService() 
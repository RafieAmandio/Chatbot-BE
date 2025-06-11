#!/usr/bin/env python3
"""
Script to add sample knowledge and products for testing
"""
import asyncio
import sys
import os

# Add the parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import SessionLocal, engine
from app.database.models import Tenant, KnowledgeItem, Product
from app.services.openai_service import openai_service
from app.services.vector_store import vector_store


async def add_sample_knowledge(tenant_id: str):
    """Add sample knowledge items"""
    sample_knowledge = [
        {
            "title": "How to Reset Your Password",
            "content": "To reset your password: 1. Go to the login page 2. Click 'Forgot Password' 3. Enter your email address 4. Check your email for reset instructions 5. Follow the link and create a new password",
            "source": "help_docs",
            "document_type": "faq"
        },
        {
            "title": "Shipping Policy",
            "content": "We offer free shipping on orders over $50. Standard shipping takes 3-5 business days. Express shipping takes 1-2 business days and costs $15. International shipping is available for $25 and takes 7-14 business days.",
            "source": "policy_docs",
            "document_type": "policy"
        },
        {
            "title": "Return Policy",
            "content": "Items can be returned within 30 days of purchase. Items must be in original condition. Return shipping is free for defective items. Customer pays return shipping for other returns. Refunds are processed within 5-7 business days.",
            "source": "policy_docs",
            "document_type": "policy"
        },
        {
            "title": "Technical Support",
            "content": "For technical support: 1. Check our FAQ section 2. Try restarting the application 3. Clear browser cache and cookies 4. Contact support at support@company.com 5. Include error messages and screenshots",
            "source": "support_docs",
            "document_type": "faq"
        }
    ]
    
    db = SessionLocal()
    try:
        for item in sample_knowledge:
            # Create embedding
            content_for_embedding = f"{item['title']} {item['content']}"
            embedding = await openai_service.create_embedding(content_for_embedding)
            
            # Create knowledge item
            knowledge_item = KnowledgeItem(
                tenant_id=tenant_id,
                title=item['title'],
                content=item['content'],
                source=item['source'],
                document_type=item['document_type'],
                vector_id=f"knowledge_{tenant_id}_{len(db.query(KnowledgeItem).filter(KnowledgeItem.tenant_id == tenant_id).all())}"
            )
            
            db.add(knowledge_item)
            db.commit()
            db.refresh(knowledge_item)
            
            # Add to vector store
            await vector_store.add_documents(
                tenant_id=tenant_id,
                collection_type="knowledge",
                documents=[item['content']],
                embeddings=[embedding],
                metadatas=[{
                    "title": item['title'],
                    "source": item['source'],
                    "document_type": item['document_type'],
                    "knowledge_id": knowledge_item.id
                }],
                ids=[knowledge_item.vector_id]
            )
            
            print(f"Added knowledge item: {item['title']}")
    
    finally:
        db.close()


async def add_sample_products(tenant_id: str):
    """Add sample products"""
    sample_products = [
        {
            "name": "Wireless Bluetooth Headphones",
            "description": "High-quality wireless Bluetooth headphones with noise cancellation, 30-hour battery life, and premium sound quality. Perfect for music, calls, and gaming.",
            "category": "Electronics",
            "price": 199.99,
            "sku": "WBH-001",
            "stock_quantity": 25,
            "specifications": {
                "battery_life": "30 hours",
                "connectivity": "Bluetooth 5.0",
                "features": ["noise cancellation", "fast charging", "foldable design"],
                "color_options": ["Black", "White", "Blue"]
            }
        },
        {
            "name": "Smart Fitness Watch",
            "description": "Advanced fitness tracker with heart rate monitoring, GPS, sleep tracking, and smartphone notifications. Water-resistant up to 50 meters.",
            "category": "Wearables",
            "price": 299.99,
            "sku": "SFW-002",
            "stock_quantity": 15,
            "specifications": {
                "display": "1.4 inch AMOLED",
                "battery_life": "7 days",
                "water_resistance": "50 meters",
                "sensors": ["heart rate", "GPS", "accelerometer", "gyroscope"]
            }
        },
        {
            "name": "Portable Power Bank",
            "description": "20,000mAh portable charger with fast charging technology. Compatible with all smartphones and tablets. LED display shows remaining battery.",
            "category": "Accessories",
            "price": 49.99,
            "sku": "PPB-003",
            "stock_quantity": 50,
            "specifications": {
                "capacity": "20,000mAh",
                "input": "USB-C, Micro USB",
                "output": "2x USB-A, 1x USB-C",
                "features": ["LED display", "fast charging", "pass-through charging"]
            }
        },
        {
            "name": "4K Webcam",
            "description": "Ultra HD 4K webcam with auto-focus, built-in microphone, and wide-angle lens. Perfect for video conferencing, streaming, and content creation.",
            "category": "Electronics",
            "price": 129.99,
            "sku": "4KW-004",
            "stock_quantity": 30,
            "specifications": {
                "resolution": "4K at 30fps",
                "field_of_view": "90 degrees",
                "microphone": "Built-in stereo",
                "compatibility": ["Windows", "Mac", "Linux"]
            }
        }
    ]
    
    db = SessionLocal()
    try:
        for item in sample_products:
            # Create embedding
            content_for_embedding = f"{item['name']} {item['description']} {item['category']}"
            if item.get('specifications'):
                content_for_embedding += f" {' '.join([f'{k}: {v}' for k, v in item['specifications'].items()])}"
            
            embedding = await openai_service.create_embedding(content_for_embedding)
            
            # Create product
            product = Product(
                tenant_id=tenant_id,
                name=item['name'],
                description=item['description'],
                category=item['category'],
                price=item['price'],
                sku=item['sku'],
                stock_quantity=item['stock_quantity'],
                specifications=item.get('specifications'),
                vector_id=f"product_{tenant_id}_{len(db.query(Product).filter(Product.tenant_id == tenant_id).all())}"
            )
            
            db.add(product)
            db.commit()
            db.refresh(product)
            
            # Add to vector store
            await vector_store.add_documents(
                tenant_id=tenant_id,
                collection_type="products",
                documents=[content_for_embedding],
                embeddings=[embedding],
                metadatas=[{
                    "name": item['name'],
                    "category": item['category'],
                    "price": item['price'],
                    "sku": item['sku'],
                    "stock_quantity": item['stock_quantity'],
                    "product_id": product.id
                }],
                ids=[product.vector_id]
            )
            
            print(f"Added product: {item['name']}")
    
    finally:
        db.close()


async def main():
    """Main function"""
    print("Adding sample data...")
    
    # Get default tenant
    db = SessionLocal()
    tenant = db.query(Tenant).filter(Tenant.domain == "default").first()
    db.close()
    
    if not tenant:
        print("Default tenant not found. Please run the application first to create default data.")
        return
    
    print(f"Adding data for tenant: {tenant.name}")
    
    # Add sample knowledge
    print("\nAdding sample knowledge...")
    await add_sample_knowledge(tenant.id)
    
    # Add sample products
    print("\nAdding sample products...")
    await add_sample_products(tenant.id)
    
    print("\nSample data added successfully!")


if __name__ == "__main__":
    asyncio.run(main()) 
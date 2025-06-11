import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database.connection import init_db
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.tenants import router as tenants_router
from app.api.users import router as users_router
from app.api.knowledge import router as knowledge_router
from app.api.products import router as products_router
from app.api.prompts import router as prompts_router
from app.api.files import router as files_router
from app.api.admin import router as admin_router
from app.services.vector_store import vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting up Multi-Tenant RAG Chatbot Backend...")
    
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized successfully")
        
        # Initialize vector store (already done in vector_store.py)
        logger.info("Vector store initialized successfully")
        
        # Create default tenant and admin user if needed
        await create_default_data()
        
        logger.info("Application startup completed")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


async def create_default_data():
    """Create default tenant and user if they don't exist"""
    try:
        from app.database.connection import SessionLocal
        from app.database.models import Tenant, User, Prompt, Product, KnowledgeItem, Conversation, Message
        from app.services.auth_service import auth_service
        from app.services.vector_store import vector_store
        import json
        from datetime import datetime, timedelta
        
        db = SessionLocal()
        
        # Check if default tenant exists
        default_tenant = db.query(Tenant).filter(Tenant.domain == "default").first()
        
        if not default_tenant:
            # Create default tenant
            default_tenant = Tenant(
                name="TechCorp Solutions",
                domain="default",
                description="Technology solutions company - Default tenant for testing and development",
                max_users=500,
                max_documents=5000,
                max_products=1000
            )
            db.add(default_tenant)
            db.commit()
            db.refresh(default_tenant)
            
            # Create default prompt
            default_prompt = Prompt(
                tenant_id=default_tenant.id,
                name="TechCorp Customer Service Assistant",
                system_prompt="""You are a helpful customer service assistant for TechCorp Solutions, a technology company specializing in laptops, smartphones, headphones, and tech accessories.

Use the available tools to search for relevant information when needed:
- search_knowledge: For general information, policies, and documentation
- search_products: For finding products in our catalog
- get_product_details: For specific product information and specifications
- check_product_availability: For stock information

Company Information:
- We offer free shipping on orders over $100
- 30-day return policy on all products
- 2-year warranty on laptops and smartphones
- 1-year warranty on accessories
- Customer support available 9 AM - 6 PM EST

Always be helpful, accurate, and professional in your responses. If you cannot find specific information, guide customers to contact our support team.""",
                description="Main customer service prompt for TechCorp Solutions",
                variables={
                    "company_name": "TechCorp Solutions",
                    "support_hours": "9 AM - 6 PM EST",
                    "free_shipping_threshold": "$100",
                    "return_policy_days": "30"
                },
                is_default=True
            )
            db.add(default_prompt)
            
            # Create additional prompts
            sales_prompt = Prompt(
                tenant_id=default_tenant.id,
                name="Sales Assistant",
                system_prompt="""You are an enthusiastic sales assistant for TechCorp Solutions. Your goal is to help customers find the perfect technology products while being informative and helpful.

Focus on:
- Understanding customer needs and use cases
- Recommending suitable products from our catalog
- Highlighting key features and benefits
- Providing competitive pricing information
- Upselling complementary products when appropriate

Always maintain a friendly, professional tone and use the available tools to provide accurate product information.""",
                description="Sales-focused prompt for product recommendations",
                variables={
                    "company_name": "TechCorp Solutions",
                    "sales_focus": "technology products"
                },
                is_active=True
            )
            db.add(sales_prompt)
            
            technical_prompt = Prompt(
                tenant_id=default_tenant.id,
                name="Technical Support Assistant",
                system_prompt="""You are a technical support specialist for TechCorp Solutions. You provide detailed technical assistance and troubleshooting guidance.

Your expertise covers:
- Laptop and computer troubleshooting
- Smartphone setup and issues
- Audio equipment configuration
- Software installation and updates
- Hardware compatibility

Always provide step-by-step solutions and ask clarifying questions when needed. Use knowledge base for specific technical documentation.""",
                description="Technical support specialist prompt",
                variables={
                    "company_name": "TechCorp Solutions",
                    "specialization": "technology support"
                },
                is_active=True
            )
            db.add(technical_prompt)
            
            # Create admin user
            admin_user = auth_service.create_user(
                db=db,
                email="admin@techcorp.com",
                password="admin123",
                full_name="Sarah Administrator",
                tenant_id=default_tenant.id,
                is_admin=True
            )
            
            # Create additional sample users
            sales_user = auth_service.create_user(
                db=db,
                email="sales@techcorp.com",
                password="sales123",
                full_name="Mike Sales",
                tenant_id=default_tenant.id,
                is_admin=False
            )
            
            support_user = auth_service.create_user(
                db=db,
                email="support@techcorp.com",
                password="support123",
                full_name="Lisa Support",
                tenant_id=default_tenant.id,
                is_admin=False
            )
            
            customer_user = auth_service.create_user(
                db=db,
                email="customer@example.com",
                password="customer123",
                full_name="John Customer",
                tenant_id=default_tenant.id,
                is_admin=False
            )
            
            db.commit()
            
            # Create sample products
            sample_products = [
                {
                    "name": "TechBook Pro 15",
                    "description": "High-performance laptop with Intel i7 processor, 16GB RAM, and 512GB SSD. Perfect for professionals and creators.",
                    "category": "Laptops",
                    "price": 1299.99,
                    "sku": "TBP-15-001",
                    "stock_quantity": 25,
                    "specifications": {
                        "processor": "Intel Core i7-12700H",
                        "memory": "16GB DDR4",
                        "storage": "512GB NVMe SSD",
                        "display": "15.6\" 4K IPS",
                        "graphics": "Intel Iris Xe",
                        "battery": "Up to 10 hours",
                        "weight": "3.5 lbs",
                        "warranty": "2 years"
                    }
                },
                {
                    "name": "TechBook Air 13",
                    "description": "Ultra-lightweight laptop with exceptional battery life. Ideal for students and travelers.",
                    "category": "Laptops",
                    "price": 899.99,
                    "sku": "TBA-13-001",
                    "stock_quantity": 40,
                    "specifications": {
                        "processor": "Intel Core i5-1235U",
                        "memory": "8GB DDR4",
                        "storage": "256GB SSD",
                        "display": "13.3\" Full HD",
                        "graphics": "Intel Iris Xe",
                        "battery": "Up to 15 hours",
                        "weight": "2.1 lbs",
                        "warranty": "2 years"
                    }
                },
                {
                    "name": "SmartPhone X Pro",
                    "description": "Flagship smartphone with advanced camera system and 5G connectivity.",
                    "category": "Smartphones",
                    "price": 999.99,
                    "sku": "SPX-PRO-001",
                    "stock_quantity": 60,
                    "specifications": {
                        "display": "6.7\" OLED Super Retina",
                        "camera": "Triple 48MP system",
                        "processor": "A16 Bionic chip",
                        "storage": "256GB",
                        "connectivity": "5G, Wi-Fi 6E, Bluetooth 5.3",
                        "battery": "All-day battery life",
                        "colors": "Space Black, Silver, Gold, Deep Purple",
                        "warranty": "2 years"
                    }
                },
                {
                    "name": "SmartPhone Lite",
                    "description": "Affordable smartphone with essential features and reliable performance.",
                    "category": "Smartphones",
                    "price": 399.99,
                    "sku": "SPL-001",
                    "stock_quantity": 80,
                    "specifications": {
                        "display": "6.1\" LCD",
                        "camera": "Dual 12MP system",
                        "processor": "A14 Bionic chip",
                        "storage": "128GB",
                        "connectivity": "4G LTE, Wi-Fi, Bluetooth 5.0",
                        "battery": "Up to 17 hours video",
                        "colors": "Blue, Red, White, Black",
                        "warranty": "2 years"
                    }
                },
                {
                    "name": "AudioMax Pro Headphones",
                    "description": "Premium noise-canceling headphones with studio-quality sound.",
                    "category": "Audio",
                    "price": 349.99,
                    "sku": "AMP-001",
                    "stock_quantity": 35,
                    "specifications": {
                        "type": "Over-ear, Closed-back",
                        "noise_cancellation": "Active Noise Cancellation",
                        "drivers": "40mm dynamic drivers",
                        "frequency_response": "20Hz - 20kHz",
                        "battery": "30 hours with ANC",
                        "connectivity": "Bluetooth 5.0, 3.5mm jack",
                        "weight": "250g",
                        "warranty": "1 year"
                    }
                },
                {
                    "name": "AudioMax Wireless Earbuds",
                    "description": "True wireless earbuds with premium sound quality and long battery life.",
                    "category": "Audio",
                    "price": 149.99,
                    "sku": "AWE-001",
                    "stock_quantity": 75,
                    "specifications": {
                        "type": "True Wireless",
                        "drivers": "11mm dynamic drivers",
                        "battery": "6 hours + 24 hours with case",
                        "connectivity": "Bluetooth 5.2",
                        "water_resistance": "IPX4",
                        "features": "Touch controls, Voice assistant",
                        "weight": "5g per earbud",
                        "warranty": "1 year"
                    }
                },
                {
                    "name": "TechMouse Pro",
                    "description": "Ergonomic wireless mouse with precision tracking for productivity and gaming.",
                    "category": "Accessories",
                    "price": 79.99,
                    "sku": "TMP-001",
                    "stock_quantity": 120,
                    "specifications": {
                        "sensor": "Optical, 4000 DPI",
                        "connectivity": "2.4GHz wireless, USB-C",
                        "battery": "Up to 70 hours",
                        "buttons": "6 programmable buttons",
                        "compatibility": "Windows, Mac, Linux",
                        "weight": "95g",
                        "warranty": "1 year"
                    }
                },
                {
                    "name": "TechKeyboard Mechanical",
                    "description": "Premium mechanical keyboard with customizable RGB lighting.",
                    "category": "Accessories",
                    "price": 159.99,
                    "sku": "TKM-001",
                    "stock_quantity": 45,
                    "specifications": {
                        "switches": "Cherry MX Blue",
                        "layout": "Full-size, 104 keys",
                        "backlighting": "RGB per-key",
                        "connectivity": "USB-C, detachable cable",
                        "features": "Programmable keys, Media controls",
                        "material": "Aluminum frame",
                        "warranty": "1 year"
                    }
                },
                {
                    "name": "TechCharger Ultra",
                    "description": "Fast wireless charging pad compatible with all Qi-enabled devices.",
                    "category": "Accessories",
                    "price": 49.99,
                    "sku": "TCU-001",
                    "stock_quantity": 200,
                    "specifications": {
                        "power": "15W fast charging",
                        "compatibility": "Qi-enabled devices",
                        "features": "LED indicator, Foreign object detection",
                        "material": "Premium glass surface",
                        "dimensions": "4.3\" x 4.3\" x 0.4\"",
                        "cable": "USB-C cable included",
                        "warranty": "1 year"
                    }
                },
                {
                    "name": "TechCare Protection Plan",
                    "description": "Extended warranty and accidental damage protection for your devices.",
                    "category": "Services",
                    "price": 99.99,
                    "sku": "TCP-001",
                    "stock_quantity": 999,
                    "specifications": {
                        "coverage": "Accidental damage, Hardware failures",
                        "duration": "Additional 1 year",
                        "devices": "Laptops, Smartphones, Tablets",
                        "claims": "Up to 2 claims per year",
                        "deductible": "$50 per claim",
                        "support": "24/7 technical support",
                        "warranty": "Service plan"
                    }
                }
            ]
            
            # Add products to database and vector store
            for product_data in sample_products:
                product = Product(
                    tenant_id=default_tenant.id,
                    name=product_data["name"],
                    description=product_data["description"],
                    category=product_data["category"],
                    price=product_data["price"],
                    sku=product_data["sku"],
                    stock_quantity=product_data["stock_quantity"],
                    specifications=product_data["specifications"],
                    meta_data={"featured": product_data["category"] in ["Laptops", "Smartphones"]}
                )
                db.add(product)
                db.commit()
                db.refresh(product)
                
                # Add to vector store
                try:
                    vector_id = await vector_store.add_product(
                        tenant_id=default_tenant.id,
                        product_id=product.id,
                        name=product.name,
                        description=product.description,
                        category=product.category,
                        specifications=product.specifications
                    )
                    product.vector_id = vector_id
                    db.commit()
                except Exception as e:
                    logger.warning(f"Failed to add product to vector store: {e}")
            
            # Create sample knowledge items
            knowledge_items = [
                {
                    "title": "Shipping and Delivery Policy",
                    "content": """TechCorp Solutions Shipping Policy:

• Free standard shipping on orders over $100
• Standard shipping: 3-5 business days ($9.99)
• Express shipping: 1-2 business days ($19.99)
• Next-day delivery available in select areas ($29.99)
• International shipping available to 50+ countries

Delivery Information:
- Signature may be required for high-value items
- We ship Monday through Friday
- Orders placed before 2 PM EST ship same day
- Tracking information provided via email
- Package insurance included on all orders

Contact our shipping department for special delivery requirements.""",
                    "document_type": "policy",
                    "source": "company_policies",
                    "meta_data": {"category": "shipping", "priority": "high"}
                },
                {
                    "title": "Return and Refund Policy",
                    "content": """TechCorp Solutions Return Policy:

Return Window:
• 30 days from delivery date for most items
• 14 days for opened software and digital products
• 90 days for defective items under warranty

Return Conditions:
• Items must be in original condition and packaging
• All accessories and documentation must be included
• Original receipt or order number required
• Restocking fee may apply to some categories

Refund Process:
• Refunds processed within 3-5 business days
• Original payment method will be credited
• Shipping costs are non-refundable (except defective items)
• Return shipping paid by customer unless item is defective

How to Return:
1. Contact customer service for return authorization
2. Pack item securely with all original contents
3. Use provided return label or ship to our returns center
4. Tracking number recommended for your protection""",
                    "document_type": "policy",
                    "source": "company_policies",
                    "meta_data": {"category": "returns", "priority": "high"}
                },
                {
                    "title": "Warranty Information",
                    "content": """TechCorp Solutions Warranty Coverage:

Standard Warranty:
• Laptops and Smartphones: 2-year limited warranty
• Audio equipment: 1-year limited warranty
• Accessories: 1-year limited warranty
• Services: As specified in service agreement

Warranty Coverage Includes:
• Manufacturing defects
• Hardware component failures
• Software issues (for pre-installed software)
• Battery performance (minimum 80% capacity for 1 year)

Not Covered:
• Physical damage from drops, spills, or abuse
• Damage from unauthorized repairs
• Normal wear and tear
• Lost or stolen items
• Damage from misuse or neglect

Extended Protection:
TechCare Protection Plan available for additional coverage including accidental damage protection.

To File a Warranty Claim:
1. Contact our technical support team
2. Provide proof of purchase and device serial number
3. Describe the issue and troubleshooting steps tried
4. Follow provided instructions for repair or replacement""",
                    "document_type": "policy",
                    "source": "company_policies",
                    "meta_data": {"category": "warranty", "priority": "high"}
                },
                {
                    "title": "TechBook Pro 15 Troubleshooting Guide",
                    "content": """TechBook Pro 15 Common Issues and Solutions:

Performance Issues:
• Slow startup: Check for software updates, restart in safe mode
• Overheating: Clean vents, check running processes, ensure proper ventilation
• Battery drain: Calibrate battery, check power settings, update drivers

Display Problems:
• Flickering screen: Update graphics drivers, check display cable connection
• No display: Try external monitor, check brightness settings, hold power button for hard reset
• Color issues: Calibrate display, check graphics driver settings

Connectivity Issues:
• Wi-Fi problems: Restart network adapter, forget and reconnect to network, update drivers
• Bluetooth issues: Reset Bluetooth module, check device compatibility
• USB ports not working: Check device manager, try different ports, restart computer

Audio Problems:
• No sound: Check volume levels, update audio drivers, check default playback device
• Microphone not working: Check privacy settings, update drivers, test with different apps

If issues persist, contact our technical support team at support@techcorp.com or call 1-800-TECHCORP.""",
                    "document_type": "technical",
                    "source": "product_support",
                    "meta_data": {"category": "troubleshooting", "product": "TechBook Pro 15"}
                },
                {
                    "title": "Customer Support Hours and Contact Information",
                    "content": """TechCorp Solutions Customer Support:

Business Hours:
• Monday - Friday: 9:00 AM - 6:00 PM EST
• Saturday: 10:00 AM - 4:00 PM EST
• Sunday: Closed
• Holiday hours may vary

Contact Methods:
• Phone: 1-800-TECHCORP (1-800-832-4267)
• Email: support@techcorp.com
• Live Chat: Available on website during business hours
• Support Portal: support.techcorp.com

Response Times:
• Phone: Immediate during business hours
• Live Chat: Average 2-3 minutes
• Email: Within 24 hours on business days
• Support tickets: Within 4-6 hours priority based

Emergency Support:
For critical business issues, premium support plans include 24/7 emergency assistance.

Self-Service Options:
• Online knowledge base
• Video tutorials
• Community forums
• Downloadable user manuals""",
                    "document_type": "contact",
                    "source": "company_info",
                    "meta_data": {"category": "support", "priority": "high"}
                },
                {
                    "title": "Payment Methods and Financing Options",
                    "content": """TechCorp Solutions Payment Information:

Accepted Payment Methods:
• Credit Cards: Visa, MasterCard, American Express, Discover
• PayPal and PayPal Credit
• Apple Pay and Google Pay
• Bank wire transfers (for large orders)
• Corporate purchase orders (approved accounts)

Financing Options:
• 0% APR for 12 months on purchases over $500*
• 0% APR for 24 months on purchases over $1,500*
• Monthly payment plans available
• Student discounts: 10% off with valid student ID
• Military discounts: 15% off with military ID

*Subject to credit approval. Standard APR rates apply after promotional period.

Security:
• SSL encryption for all transactions
• PCI DSS compliant payment processing
• Fraud protection and monitoring
• Secure account management

Business Accounts:
• Net 30 payment terms available
• Volume discounts for bulk orders
• Dedicated account managers
• Custom pricing for enterprise customers

For payment questions, contact our billing department at billing@techcorp.com""",
                    "document_type": "policy",
                    "source": "company_policies",
                    "meta_data": {"category": "payment", "priority": "medium"}
                }
            ]
            
            # Add knowledge items to database and vector store
            for item_data in knowledge_items:
                knowledge_item = KnowledgeItem(
                    tenant_id=default_tenant.id,
                    title=item_data["title"],
                    content=item_data["content"],
                    document_type=item_data["document_type"],
                    source=item_data["source"],
                    meta_data=item_data["meta_data"]
                )
                db.add(knowledge_item)
                db.commit()
                db.refresh(knowledge_item)
                
                # Add to vector store
                try:
                    vector_id = await vector_store.add_knowledge_item(
                        tenant_id=default_tenant.id,
                        item_id=knowledge_item.id,
                        title=knowledge_item.title,
                        content=knowledge_item.content,
                        metadata=knowledge_item.meta_data
                    )
                    knowledge_item.vector_id = vector_id
                    db.commit()
                except Exception as e:
                    logger.warning(f"Failed to add knowledge item to vector store: {e}")
            
            # Create sample conversations and messages
            sample_conversation = Conversation(
                tenant_id=default_tenant.id,
                user_id=customer_user.id,
                title="Product Inquiry - TechBook Pro 15"
            )
            db.add(sample_conversation)
            db.commit()
            db.refresh(sample_conversation)
            
            # Add sample messages
            messages = [
                {
                    "role": "user",
                    "content": "Hi, I'm interested in the TechBook Pro 15. Can you tell me more about its specifications and battery life?"
                },
                {
                    "role": "assistant",
                    "content": "Hello! I'd be happy to help you with information about the TechBook Pro 15. It's one of our most popular laptops!\n\nKey specifications:\n- Intel Core i7-12700H processor\n- 16GB DDR4 RAM\n- 512GB NVMe SSD storage\n- 15.6\" 4K IPS display\n- Intel Iris Xe graphics\n- Up to 10 hours battery life\n- Weighs only 3.5 lbs\n\nThe TechBook Pro 15 is perfect for professionals and creators who need high performance in a portable package. The 4K display is excellent for photo/video editing, and the powerful processor handles demanding applications smoothly.\n\nWould you like to know about pricing or any specific features?",
                    "meta_data": {"tool_calls": [], "response_time": 2.3}
                },
                {
                    "role": "user",
                    "content": "What's the price and do you have any current promotions?"
                },
                {
                    "role": "assistant",
                    "content": "The TechBook Pro 15 is currently priced at $1,299.99. We have several great offers right now:\n\n💰 **Current Promotions:**\n- Free shipping (since it's over $100)\n- 0% APR financing for 12 months (with approved credit)\n- Student discount: 10% off with valid student ID\n- Military discount: 15% off with military ID\n\n📦 **What's Included:**\n- TechBook Pro 15 laptop\n- Power adapter and cable\n- Quick start guide\n- 2-year limited warranty\n\n🛡️ **Optional Add-ons:**\n- TechCare Protection Plan for $99.99 (extends warranty + accidental damage coverage)\n- Premium carrying case and accessories\n\nWould you like me to help you configure an order or do you have any other questions about the laptop?",
                    "meta_data": {"tool_calls": [], "response_time": 1.8}
                }
            ]
            
            for msg_data in messages:
                message = Message(
                    conversation_id=sample_conversation.id,
                    role=msg_data["role"],
                    content=msg_data["content"],
                    meta_data=msg_data.get("meta_data")
                )
                db.add(message)
            
            db.commit()
            logger.info("Created comprehensive sample data: tenant, users, products, knowledge items, prompts, and conversations")
        
        else:
            logger.info("Default tenant already exists, skipping sample data creation")
        
        db.close()
        
    except Exception as e:
        logger.error(f"Error creating default data: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()
        raise


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-Tenant RAG + Tooling Chatbot Backend with OpenAI integration",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for production
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure this properly for production
    )


# Exception handlers
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc):
    logger.error(f"Database error: {exc}")
    return HTTPException(
        status_code=500,
        detail="Database error occurred"
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}")
    return HTTPException(
        status_code=500,
        detail="Internal server error"
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version
    }


# Include routers
app.include_router(chat_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(prompts_router, prefix="/api/v1")
app.include_router(files_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    ) 
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging

from app.database.connection import get_db
from app.database.models import Tenant, User, Conversation, Message, Prompt
from app.schemas.chat import ChatRequest, ChatResponse, ConversationCreate, ConversationResponse
from app.services.openai_service import openai_service
from app.services.tools import tools_service
from app.services.vector_store import vector_store
from app.auth.dependencies import get_current_tenant, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatService:
    def __init__(self):
        pass
    
    async def get_system_prompt(self, tenant_id: str, db: Session) -> str:
        """Get active system prompt for tenant"""
        prompt = db.query(Prompt).filter(
            Prompt.tenant_id == tenant_id,
            Prompt.is_active == True,
            Prompt.is_default == True
        ).first()
        
        if not prompt:
            # Default system prompt
            return """You are a helpful customer service assistant. You have access to knowledge base and product information to help customers with their questions.

Use the available tools to search for relevant information when needed:
- search_knowledge: For general information and documentation
- search_products: For finding products
- get_product_details: For specific product information
- check_product_availability: For stock information

Always be helpful, accurate, and professional in your responses."""
        
        return prompt.system_prompt
    
    async def get_conversation_messages(self, conversation_id: str, tenant_id: str, db: Session) -> List[Dict[str, str]]:
        """Get conversation messages for context"""
        messages = db.query(Message).join(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id
        ).order_by(Message.created_at).all()
        
        return [
            {
                "role": message.role,
                "content": message.content
            }
            for message in messages
        ]
    
    async def create_or_get_conversation(
        self,
        conversation_id: Optional[str],
        tenant_id: str,
        user_id: str,
        db: Session
    ) -> str:
        """Create new conversation or get existing one"""
        if conversation_id:
            # Verify conversation belongs to tenant
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id
            ).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return conversation_id
        
        # Create new conversation
        conversation = Conversation(
            tenant_id=tenant_id,
            user_id=user_id
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation.id
    
    async def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]],
        db: Session
    ):
        """Save message to database"""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata=metadata
        )
        db.add(message)
        db.commit()
    
    async def process_tool_calls(
        self,
        tool_calls: List[Any],
        tenant_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Process OpenAI tool calls"""
        tool_messages = []
        
        for tool_call in tool_calls:
            try:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Execute tool
                result = await tools_service.execute_tool(
                    tool_name=function_name,
                    arguments=function_args,
                    tenant_id=tenant_id,
                    db=db
                )
                
                tool_messages.append({
                    "role": "tool",
                    "content": json.dumps(result),
                    "tool_call_id": tool_call.id
                })
                
            except Exception as e:
                logger.error(f"Error processing tool call: {e}")
                tool_messages.append({
                    "role": "tool",
                    "content": json.dumps({"error": str(e)}),
                    "tool_call_id": tool_call.id
                })
        
        return tool_messages


chat_service = ChatService()


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stream chat response"""
    
    async def generate_response():
        try:
            # Create or get conversation
            conversation_id = await chat_service.create_or_get_conversation(
                request.conversation_id,
                current_tenant.id,
                current_user.id,
                db
            )
            
            # Save user message
            await chat_service.save_message(
                conversation_id,
                "user",
                request.message,
                None,
                db
            )
            
            # Get system prompt
            system_prompt = await chat_service.get_system_prompt(current_tenant.id, db)
            
            # Build messages for OpenAI
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            if request.conversation_id:
                history_messages = await chat_service.get_conversation_messages(
                    request.conversation_id,
                    current_tenant.id,
                    db
                )
                messages.extend(history_messages)
            
            # Add current user message
            messages.append({"role": "user", "content": request.message})
            
            # Truncate messages if too long
            messages = openai_service.truncate_messages(messages)
            
            # Get available tools
            tools = tools_service.get_tool_definitions(current_tenant.id)
            
            # Send initial data
            yield f"data: {json.dumps({'type': 'conversation_id', 'data': conversation_id})}\n\n"
            
            assistant_message = ""
            tool_calls_buffer = []
            
            # Stream chat completion
            async for chunk in openai_service.chat_completion_stream(
                messages=messages,
                tools=tools,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            ):
                if chunk["content"]:
                    assistant_message += chunk["content"]
                    yield f"data: {json.dumps({'type': 'content', 'data': chunk['content']})}\n\n"
                
                if chunk["tool_calls"]:
                    tool_calls_buffer.extend(chunk["tool_calls"])
                
                if chunk["finish_reason"] == "tool_calls":
                    # Process tool calls
                    yield f"data: {json.dumps({'type': 'tool_calls', 'data': 'Processing tools...'})}\n\n"
                    
                    tool_messages = await chat_service.process_tool_calls(
                        tool_calls_buffer,
                        current_tenant.id,
                        db
                    )
                    
                    # Add tool results to messages
                    messages.extend([
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": tool_calls_buffer
                        }
                    ])
                    messages.extend(tool_messages)
                    
                    # Continue with tool results
                    async for follow_chunk in openai_service.chat_completion_stream(
                        messages=messages,
                        tools=tools,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens
                    ):
                        if follow_chunk["content"]:
                            assistant_message += follow_chunk["content"]
                            yield f"data: {json.dumps({'type': 'content', 'data': follow_chunk['content']})}\n\n"
                        
                        if follow_chunk["finish_reason"] in ["stop", "length"]:
                            break
                    
                    break
                
                if chunk["finish_reason"] in ["stop", "length"]:
                    break
            
            # Save assistant message
            await chat_service.save_message(
                conversation_id,
                "assistant",
                assistant_message,
                {"tool_calls": tool_calls_buffer} if tool_calls_buffer else None,
                db
            )
            
            yield f"data: {json.dumps({'type': 'done', 'data': 'Stream completed'})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in chat stream: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


@router.post("/", response_model=ChatResponse)
async def chat_non_stream(
    request: ChatRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Non-streaming chat endpoint"""
    try:
        # Create or get conversation
        conversation_id = await chat_service.create_or_get_conversation(
            request.conversation_id,
            current_tenant.id,
            current_user.id,
            db
        )
        
        # Save user message
        await chat_service.save_message(
            conversation_id,
            "user",
            request.message,
            None,
            db
        )
        
        # Get system prompt
        system_prompt = await chat_service.get_system_prompt(current_tenant.id, db)
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        if request.conversation_id:
            history_messages = await chat_service.get_conversation_messages(
                request.conversation_id,
                current_tenant.id,
                db
            )
            messages.extend(history_messages)
        
        messages.append({"role": "user", "content": request.message})
        messages = openai_service.truncate_messages(messages)
        
        # Get tools
        tools = tools_service.get_tool_definitions(current_tenant.id)
        
        # Get completion
        response = await openai_service.chat_completion(
            messages=messages,
            tools=tools,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        assistant_message = response["content"] or ""
        
        # Handle tool calls if present
        if response["tool_calls"]:
            tool_messages = await chat_service.process_tool_calls(
                response["tool_calls"],
                current_tenant.id,
                db
            )
            
            # Get final response with tool results
            messages.extend([
                {
                    "role": "assistant", 
                    "content": None,
                    "tool_calls": response["tool_calls"]
                }
            ])
            messages.extend(tool_messages)
            
            final_response = await openai_service.chat_completion(
                messages=messages,
                tools=tools,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            assistant_message = final_response["content"] or ""
        
        # Save assistant message
        await chat_service.save_message(
            conversation_id,
            "assistant",
            assistant_message,
            {"tool_calls": response["tool_calls"]} if response["tool_calls"] else None,
            db
        )
        
        return ChatResponse(
            conversation_id=conversation_id,
            message={
                "role": "assistant",
                "content": assistant_message,
                "metadata": {"tool_calls": response["tool_calls"]} if response["tool_calls"] else None
            },
            usage=response.get("usage")
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation"""
    conversation = Conversation(
        tenant_id=current_tenant.id,
        user_id=current_user.id,
        title=request.title
    )
    
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    return conversation


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's conversations"""
    conversations = db.query(Conversation).filter(
        Conversation.tenant_id == current_tenant.id,
        Conversation.user_id == current_user.id
    ).order_by(Conversation.updated_at.desc()).all()
    
    return conversations


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific conversation with messages"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.tenant_id == current_tenant.id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation 
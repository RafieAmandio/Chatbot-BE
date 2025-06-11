from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
import re

from app.database.connection import get_db
from app.database.models import Prompt, User, Tenant
from app.schemas.prompt import (
    PromptCreate, PromptUpdate, PromptResponse,
    PromptTestRequest, PromptTestResponse
)
from app.auth.dependencies import get_current_user, get_current_tenant
from app.services.openai_service import openai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prompts", tags=["prompt-management"])


class PromptService:
    """Service for prompt management and variable substitution"""
    
    @staticmethod
    def render_prompt(prompt_template: str, variables: dict = None) -> str:
        """Render prompt template with variables"""
        if not variables:
            return prompt_template
        
        # Replace variables in format {{variable_name}}
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            prompt_template = prompt_template.replace(placeholder, str(value))
        
        return prompt_template
    
    @staticmethod
    def extract_variables(prompt_template: str) -> List[str]:
        """Extract variable names from prompt template"""
        # Find all variables in format {{variable_name}}
        pattern = r'\{\{(\w+)\}\}'
        variables = re.findall(pattern, prompt_template)
        return list(set(variables))


prompt_service = PromptService()


@router.post("/", response_model=PromptResponse)
async def create_prompt(
    prompt_data: PromptCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new prompt"""
    # If setting as default, unset other defaults
    if prompt_data.is_default:
        db.query(Prompt).filter(
            Prompt.tenant_id == current_tenant.id,
            Prompt.is_default == True
        ).update({"is_default": False})
    
    # Extract variables from prompt
    extracted_variables = prompt_service.extract_variables(prompt_data.system_prompt)
    
    prompt = Prompt(
        tenant_id=current_tenant.id,
        name=prompt_data.name,
        system_prompt=prompt_data.system_prompt,
        description=prompt_data.description,
        is_default=prompt_data.is_default,
        variables=prompt_data.variables or {var: "" for var in extracted_variables}
    )
    
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    
    logger.info(f"Prompt created: {prompt.name} by {current_user.email}")
    return prompt


@router.get("/", response_model=List[PromptResponse])
async def list_prompts(
    skip: int = 0,
    limit: int = 100,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """List prompts for tenant"""
    prompts = db.query(Prompt).filter(
        Prompt.tenant_id == current_tenant.id,
        Prompt.is_active == True
    ).offset(skip).limit(limit).all()
    
    return prompts


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get specific prompt"""
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.tenant_id == current_tenant.id
    ).first()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    return prompt


@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: str,
    prompt_data: PromptUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update prompt"""
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.tenant_id == current_tenant.id
    ).first()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # If setting as default, unset other defaults
    if prompt_data.is_default:
        db.query(Prompt).filter(
            Prompt.tenant_id == current_tenant.id,
            Prompt.is_default == True,
            Prompt.id != prompt_id
        ).update({"is_default": False})
    
    # Update fields
    update_data = prompt_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prompt, field, value)
    
    # Update variables if system_prompt changed
    if "system_prompt" in update_data:
        extracted_variables = prompt_service.extract_variables(prompt.system_prompt)
        existing_vars = prompt.variables or {}
        
        # Merge existing and new variables
        new_variables = {var: existing_vars.get(var, "") for var in extracted_variables}
        prompt.variables = new_variables
    
    db.commit()
    db.refresh(prompt)
    
    logger.info(f"Prompt updated: {prompt.name} by {current_user.email}")
    return prompt


@router.delete("/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete prompt"""
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.tenant_id == current_tenant.id
    ).first()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Don't allow deleting default prompt
    if prompt.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete default prompt"
        )
    
    # Soft delete
    prompt.is_active = False
    db.commit()
    
    logger.info(f"Prompt deleted: {prompt.name} by {current_user.email}")
    return {"message": "Prompt deleted successfully"}


@router.post("/{prompt_id}/set-default")
async def set_default_prompt(
    prompt_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set prompt as default for tenant"""
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.tenant_id == current_tenant.id
    ).first()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Unset all other defaults
    db.query(Prompt).filter(
        Prompt.tenant_id == current_tenant.id,
        Prompt.is_default == True
    ).update({"is_default": False})
    
    # Set this as default
    prompt.is_default = True
    db.commit()
    
    logger.info(f"Default prompt set: {prompt.name} by {current_user.email}")
    return {"message": "Default prompt updated successfully"}


@router.get("/default/current", response_model=PromptResponse)
async def get_default_prompt(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get current default prompt for tenant"""
    prompt = db.query(Prompt).filter(
        Prompt.tenant_id == current_tenant.id,
        Prompt.is_default == True,
        Prompt.is_active == True
    ).first()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="No default prompt found")
    
    return prompt


@router.post("/test", response_model=PromptTestResponse)
async def test_prompt(
    test_request: PromptTestRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """Test a prompt with a sample message"""
    try:
        # Render prompt with variables
        rendered_prompt = prompt_service.render_prompt(
            test_request.system_prompt,
            test_request.variables
        )
        
        # Test with OpenAI
        messages = [
            {"role": "system", "content": rendered_prompt},
            {"role": "user", "content": test_request.test_message}
        ]
        
        response = await openai_service.chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        return PromptTestResponse(
            rendered_prompt=rendered_prompt,
            test_response=response["content"] or "",
            usage=response.get("usage")
        )
        
    except Exception as e:
        logger.error(f"Error testing prompt: {e}")
        raise HTTPException(status_code=500, detail="Prompt test failed")


@router.get("/{prompt_id}/variables")
async def get_prompt_variables(
    prompt_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Get variables available in a prompt"""
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.tenant_id == current_tenant.id
    ).first()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    extracted_variables = prompt_service.extract_variables(prompt.system_prompt)
    
    return {
        "variables": extracted_variables,
        "values": prompt.variables or {}
    } 
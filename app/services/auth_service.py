from datetime import datetime, timedelta
from typing import Optional, Union
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import secrets
import logging

from app.config import settings
from app.database.models import User, Tenant
from app.schemas.auth import TokenData

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)
    
    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            token_data = TokenData(user_id=user_id)
            return token_data
        except JWTError:
            return None
    
    def create_user(self, db: Session, email: str, password: str, full_name: str, tenant_id: str, is_admin: bool = False) -> User:
        """Create a new user"""
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email, User.tenant_id == tenant_id).first()
        if existing_user:
            raise ValueError("User with this email already exists in this tenant")
        
        # Hash password
        hashed_password = self.get_password_hash(password)
        
        # Create user
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            tenant_id=tenant_id,
            is_admin=is_admin
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"Created user {email} for tenant {tenant_id}")
        return user
    
    def update_user_password(self, db: Session, user: User, new_password: str) -> User:
        """Update user password"""
        hashed_password = self.get_password_hash(new_password)
        user.hashed_password = hashed_password
        db.commit()
        db.refresh(user)
        return user
    
    def deactivate_user(self, db: Session, user: User) -> User:
        """Deactivate user account"""
        user.is_active = False
        db.commit()
        db.refresh(user)
        return user
    
    def activate_user(self, db: Session, user: User) -> User:
        """Activate user account"""
        user.is_active = True
        db.commit()
        db.refresh(user)
        return user
    
    def generate_reset_token(self) -> str:
        """Generate password reset token"""
        return secrets.token_urlsafe(32)
    
    def create_reset_token(self, user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create password reset token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=1)  # Reset tokens expire in 1 hour
        
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "type": "password_reset"
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_reset_token(self, token: str) -> Optional[str]:
        """Verify password reset token and return user ID"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")
            
            if user_id is None or token_type != "password_reset":
                return None
            
            return user_id
        except JWTError:
            return None
    
    def get_user_by_email(self, db: Session, email: str, tenant_id: Optional[str] = None) -> Optional[User]:
        """Get user by email, optionally filtered by tenant"""
        query = db.query(User).filter(User.email == email)
        if tenant_id:
            query = query.filter(User.tenant_id == tenant_id)
        return query.first()
    
    def get_user_by_id(self, db: Session, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    def check_tenant_domain(self, db: Session, domain: str) -> Optional[Tenant]:
        """Check if tenant domain exists and is active"""
        return db.query(Tenant).filter(
            Tenant.domain == domain,
            Tenant.is_active == True
        ).first()
    
    def is_email_available(self, db: Session, email: str, tenant_id: str) -> bool:
        """Check if email is available for registration in tenant"""
        existing_user = db.query(User).filter(
            User.email == email,
            User.tenant_id == tenant_id
        ).first()
        return existing_user is None


# Global auth service instance
auth_service = AuthService() 
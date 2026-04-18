from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from core import security
from models.user import User, UserRole, UserType
import secrets

security_basic = HTTPBasic()

async def get_swagger_auth(credentials: HTTPBasicCredentials = Depends(security_basic)):
    """
    Dependency to authenticate Swagger/ReDoc endpoints using HTTP Basic Auth.
    Only allows Platform Staff Admins.
    """
    user = await User.find_one(User.username == credentials.username)
    if not user:
        # Check by email as fallback if username not found
        user = await User.find_one(User.email == credentials.username)
        
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Verify password
    if not security.verify_password(credentials.password, user.hashed_password):
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
         
    # Check privileges: Must be platform-staff and admin
    if user.user_type != UserType.PLATFORM_STAFF or user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have enough privileges to access the API documentation",
        )
    
    return user

import pytest
from app.services.user_service import create_user, get_user_by_id, UserNotFoundError
from app.schemas.user import UserCreate

def test_create_user(db):
    user_data = UserCreate(name="Test User", email="test@example.com")
    user = create_user(db, user_data)
    
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.id is not None

def test_get_user_by_id(db):
    user_data = UserCreate(name="Test User", email="test@example.com")
    created_user = create_user(db, user_data)
    
    user = get_user_by_id(db, created_user.id)
    assert user is not None
    assert user.id == created_user.id
    assert user.name == "Test User"

def test_get_user_by_id_not_found(db):
    with pytest.raises(UserNotFoundError):
        get_user_by_id(db, 999)
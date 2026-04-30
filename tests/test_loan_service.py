import pytest
from datetime import datetime, date
from enum import Enum
from app.services.user_service import create_user
from app.services.author_service import create_author
from app.services.book_service import create_book
from app.services.loan_service import create_loan, return_loan, LoanBookIsNotAvailableError, LoanAlreadyReturnedError
from app.schemas.user import UserCreate
from app.schemas.author import AuthorCreate
from app.schemas.book import BookCreate

class LoanStatusMock(str, Enum):
    ACTIVE = "active"
    RETURNED = "returned"

def test_create_loan(db):
    user_data = UserCreate(name="Test User", email="test@example.com")
    user = create_user(db, user_data)
    
    author_data = AuthorCreate(name="Test Author")
    author = create_author(db, author_data)
    
    book_data = BookCreate(isbn="1234567890", author_id=author.id, title="Test Book", published_date=date(2023, 1, 1))
    book = create_book(db, book_data)
    
    loan = create_loan(db, user.id, book.id)
    
    assert loan.user_id == user.id
    assert loan.book_id == book.id
    assert loan.status == LoanStatusMock.ACTIVE
    assert loan.fine_value == 0.0

def test_return_loan(db):
    user_data = UserCreate(name="Test User", email="test@example.com")
    user = create_user(db, user_data)
    
    author_data = AuthorCreate(name="Test Author")
    author = create_author(db, author_data)
    
    book_data = BookCreate(isbn="1234567890", author_id=author.id, title="Test Book", published_date=date(2023, 1, 1))
    book = create_book(db, book_data)
    
    loan = create_loan(db, user.id, book.id)
    
    returned_loan = return_loan(db, loan.id)
    
    assert returned_loan.status == LoanStatusMock.RETURNED
    assert returned_loan.actual_return_date is not None
    assert returned_loan.fine_value == 0.0

def test_return_loan_already_returned(db):
    user_data = UserCreate(name="Test User", email="test@example.com")
    user = create_user(db, user_data)
    
    author_data = AuthorCreate(name="Test Author")
    author = create_author(db, author_data)
    
    book_data = BookCreate(isbn="1234567890", author_id=author.id, title="Test Book", published_date=date(2023, 1, 1))
    book = create_book(db, book_data)
    
    loan = create_loan(db, user.id, book.id)
    return_loan(db, loan.id)
    
    with pytest.raises(LoanAlreadyReturnedError):
        return_loan(db, loan.id)
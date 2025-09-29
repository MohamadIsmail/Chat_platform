import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from faker import Faker

fake = Faker()


class TestUserRegistration:
    """Test user registration functionality."""
    
    def test_register_user_success(self, client: TestClient, test_user_data, helpers):
        """Test successful user registration."""
        response = client.post("/register", json=test_user_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "username" in data
        assert "email" in data
        assert "password" not in data
        
        # Verify data matches input
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert isinstance(data["id"], int)
    
    def test_register_user_duplicate_username(self, client: TestClient, test_user, test_user_data):
        """Test registration with duplicate username."""
        # Try to register with existing username
        duplicate_data = {
            "username": test_user.username,
            "email": "different@test.com",
            "password": "newpassword123"
        }
        
        response = client.post("/register", json=duplicate_data)
        
        assert response.status_code == 400
        assert "Username or email already registered" in response.json()["detail"]
    
    def test_register_user_duplicate_email(self, client: TestClient, test_user, test_user_data):
        """Test registration with duplicate email."""
        # Try to register with existing email
        duplicate_data = {
            "username": "different_user",
            "email": test_user.email,
            "password": "newpassword123"
        }
        
        response = client.post("/register", json=duplicate_data)
        
        assert response.status_code == 400
        assert "Username or email already registered" in response.json()["detail"]
    
    def test_register_user_invalid_email(self, client: TestClient):
        """Test registration with invalid email format."""
        invalid_data = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "password123"
        }
        
        response = client.post("/register", json=invalid_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_register_user_short_password(self, client: TestClient):
        """Test registration with short password."""
        invalid_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "123"  # Too short
        }
        
        response = client.post("/register", json=invalid_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_register_user_missing_fields(self, client: TestClient):
        """Test registration with missing required fields."""
        # Missing password
        response = client.post("/register", json={
            "username": "testuser",
            "email": "test@example.com"
        })
        
        assert response.status_code == 422
        
        # Missing username
        response = client.post("/register", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 422
        
        # Missing email
        response = client.post("/register", json={
            "username": "testuser",
            "password": "password123"
        })
        
        assert response.status_code == 422
    
    def test_register_user_empty_fields(self, client: TestClient):
        """Test registration with empty fields."""
        empty_data = {
            "username": "",
            "email": "",
            "password": ""
        }
        
        response = client.post("/register", json=empty_data)
        
        assert response.status_code == 422
    
    @pytest.mark.parametrize("username", [
        "a" * 51,  # Too long
        "user@name",  # Invalid characters
        "user name",  # Spaces
        "user-name",  # Hyphens (if not allowed)
    ])
    def test_register_user_invalid_username(self, client: TestClient, username):
        """Test registration with invalid username formats."""
        invalid_data = {
            "username": username,
            "email": "test@example.com",
            "password": "password123"
        }
        
        response = client.post("/register", json=invalid_data)
        
        assert response.status_code == 422


class TestUserLogin:
    """Test user login functionality."""
    
    def test_login_success(self, client: TestClient, test_user, test_user_data):
        """Test successful user login."""
        response = client.post("/login", data={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
    
    def test_login_invalid_username(self, client: TestClient, test_user_data):
        """Test login with non-existent username."""
        response = client.post("/login", data={
            "username": "nonexistent_user",
            "password": test_user_data["password"]
        })
        
        assert response.status_code == 400
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_invalid_password(self, client: TestClient, test_user, test_user_data):
        """Test login with incorrect password."""
        response = client.post("/login", data={
            "username": test_user_data["username"],
            "password": "wrongpassword"
        })
        
        assert response.status_code == 400
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_empty_credentials(self, client: TestClient):
        """Test login with empty credentials."""
        response = client.post("/login", data={
            "username": "",
            "password": ""
        })
        
        assert response.status_code == 422
    
    def test_login_missing_credentials(self, client: TestClient):
        """Test login with missing credentials."""
        # Missing password
        response = client.post("/login", data={
            "username": "testuser"
        })
        
        assert response.status_code == 422
        
        # Missing username
        response = client.post("/login", data={
            "password": "password123"
        })
        
        assert response.status_code == 422
    
    def test_login_case_sensitivity(self, client: TestClient, test_user, test_user_data):
        """Test login with different case username."""
        # Try with uppercase username
        response = client.post("/login", data={
            "username": test_user_data["username"].upper(),
            "password": test_user_data["password"]
        })
        
        # Should fail if usernames are case-sensitive
        assert response.status_code == 400
    
    def test_login_with_email(self, client: TestClient, test_user, test_user_data):
        """Test login using email instead of username."""
        response = client.post("/login", data={
            "username": test_user_data["email"],  # Using email as username
            "password": test_user_data["password"]
        })
        
        # Should fail if login only accepts username
        assert response.status_code == 400


class TestAuthenticationFlow:
    """Test complete authentication flow."""
    
    def test_register_and_login_flow(self, client: TestClient, data_factory):
        """Test complete registration and login flow."""
        # Register new user
        user_data = data_factory.create_user_data()
        register_response = client.post("/register", json=user_data)
        
        assert register_response.status_code == 200
        user_id = register_response.json()["id"]
        
        # Login with registered user
        login_response = client.post("/login", data={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Verify token is valid by accessing protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/health", headers=headers)
        
        assert response.status_code == 200
    
    def test_multiple_user_registration(self, client: TestClient, data_factory):
        """Test registering multiple users."""
        users_data = data_factory.create_multiple_users(3)
        
        for i, user_data in enumerate(users_data):
            response = client.post("/register", json=user_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == user_data["username"]
            assert data["email"] == user_data["email"]
            assert data["id"] == i + 1  # Assuming sequential IDs
    
    def test_concurrent_registration(self, client: TestClient, data_factory):
        """Test concurrent user registration."""
        import threading
        import time
        
        results = []
        
        def register_user(user_data):
            response = client.post("/register", json=user_data)
            results.append(response.status_code)
        
        # Create multiple users concurrently
        users_data = data_factory.create_multiple_users(5)
        threads = []
        
        for user_data in users_data:
            thread = threading.Thread(target=register_user, args=(user_data,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All registrations should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5


class TestUserDataValidation:
    """Test user data validation."""
    
    @pytest.mark.parametrize("field,invalid_values", [
        ("username", ["", "a", "a" * 51, "user@name", "user name"]),
        ("email", ["", "invalid", "test@", "@test.com", "test..test@test.com"]),
        ("password", ["", "123", "a" * 5, "a" * 101]),
    ])
    def test_invalid_field_values(self, client: TestClient, field, invalid_values):
        """Test various invalid field values."""
        base_data = {
            "username": "validuser",
            "email": "valid@test.com",
            "password": "validpassword123"
        }
        
        for invalid_value in invalid_values:
            test_data = base_data.copy()
            test_data[field] = invalid_value
            
            response = client.post("/register", json=test_data)
            
            assert response.status_code == 422, f"Expected 422 for {field}={invalid_value}"
    
    def test_sql_injection_attempts(self, client: TestClient):
        """Test SQL injection prevention."""
        malicious_data = {
            "username": "'; DROP TABLE users; --",
            "email": "test@test.com",
            "password": "password123"
        }
        
        response = client.post("/register", json=malicious_data)
        
        # Should either succeed (if properly escaped) or fail with validation error
        # Should not cause server error
        assert response.status_code in [200, 422]
    
    def test_xss_attempts(self, client: TestClient):
        """Test XSS prevention."""
        xss_data = {
            "username": "<script>alert('xss')</script>",
            "email": "test@test.com",
            "password": "password123"
        }
        
        response = client.post("/register", json=xss_data)
        
        # Should succeed but data should be properly escaped
        if response.status_code == 200:
            data = response.json()
            assert "<script>" not in data["username"]
    
    def test_unicode_handling(self, client: TestClient):
        """Test Unicode character handling."""
        unicode_data = {
            "username": "用户123",
            "email": "测试@测试.com",
            "password": "密码123"
        }
        
        response = client.post("/register", json=unicode_data)
        
        # Should handle Unicode properly
        assert response.status_code in [200, 422]  # Depending on validation rules

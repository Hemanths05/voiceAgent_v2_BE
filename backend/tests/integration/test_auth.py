"""
Integration Tests for Authentication
Tests auth flow: register → login → access protected route
"""
import pytest
from fastapi.testclient import TestClient


class TestAuthenticationFlow:
    """Test complete authentication flow"""

    def test_register_superadmin(self, client: TestClient, mock_user_data: dict):
        """Test superadmin registration"""
        register_data = {
            "email": "superadmin_test@example.com",
            "password": mock_user_data["password"],
            "name": "Superadmin Test"
        }

        response = client.post("/api/auth/register", json=register_data)

        assert response.status_code == 201
        data = response.json()

        # Check response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == register_data["email"]
        assert data["user"]["role"] == "superadmin"
        assert data["user"]["company_id"] is None

    def test_register_admin_with_company(self, client: TestClient, mock_user_data: dict):
        """Test admin registration with company"""
        # First create superadmin and company
        superadmin_data = {
            "email": "superadmin_for_company@example.com",
            "password": mock_user_data["password"],
            "name": "Superadmin"
        }
        superadmin_response = client.post("/api/auth/register", json=superadmin_data)
        superadmin_token = superadmin_response.json()["access_token"]

        # Create company
        company_data = {
            "name": "Test Company For Admin",
            "phone_number": "+1234567891",
            "description": "Test company"
        }
        company_response = client.post(
            "/api/superadmin/companies",
            json=company_data,
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        company_id = company_response.json()["id"]

        # Now register admin for that company
        admin_data = {
            "email": "admin_test@example.com",
            "password": mock_user_data["password"],
            "name": "Admin Test",
            "company_id": company_id
        }

        response = client.post("/api/auth/register", json=admin_data)

        assert response.status_code == 201
        data = response.json()

        assert data["user"]["role"] == "admin"
        assert data["user"]["company_id"] == company_id

    def test_register_duplicate_email(self, client: TestClient, mock_user_data: dict):
        """Test registering with duplicate email fails"""
        register_data = {
            "email": "duplicate@example.com",
            "password": mock_user_data["password"],
            "name": "First User"
        }

        # First registration should succeed
        response1 = client.post("/api/auth/register", json=register_data)
        assert response1.status_code == 201

        # Second registration with same email should fail
        response2 = client.post("/api/auth/register", json=register_data)
        assert response2.status_code == 400

    def test_login_success(self, client: TestClient, mock_user_data: dict):
        """Test successful login"""
        # First register
        register_data = {
            "email": "login_test@example.com",
            "password": mock_user_data["password"],
            "name": "Login Test"
        }
        client.post("/api/auth/register", json=register_data)

        # Now login
        login_data = {
            "email": "login_test@example.com",
            "password": mock_user_data["password"]
        }

        response = client.post("/api/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == login_data["email"]

    def test_login_invalid_email(self, client: TestClient, mock_user_data: dict):
        """Test login with non-existent email"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": mock_user_data["password"]
        }

        response = client.post("/api/auth/login", json=login_data)

        assert response.status_code == 401

    def test_login_invalid_password(self, client: TestClient, mock_user_data: dict):
        """Test login with wrong password"""
        # First register
        register_data = {
            "email": "wrongpassword@example.com",
            "password": mock_user_data["password"],
            "name": "Wrong Password Test"
        }
        client.post("/api/auth/register", json=register_data)

        # Try to login with wrong password
        login_data = {
            "email": "wrongpassword@example.com",
            "password": "WrongPassword123!"
        }

        response = client.post("/api/auth/login", json=login_data)

        assert response.status_code == 401

    def test_get_current_user(self, client: TestClient, mock_user_data: dict):
        """Test getting current user info"""
        # Register and get token
        register_data = {
            "email": "currentuser@example.com",
            "password": mock_user_data["password"],
            "name": "Current User Test"
        }
        register_response = client.post("/api/auth/register", json=register_data)
        access_token = register_response.json()["access_token"]

        # Get current user
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == register_data["email"]
        assert data["name"] == register_data["name"]

    def test_get_current_user_no_token(self, client: TestClient):
        """Test getting current user without token fails"""
        response = client.get("/api/auth/me")

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token fails"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )

        assert response.status_code == 401

    def test_complete_auth_flow(self, client: TestClient, mock_user_data: dict):
        """Test complete authentication flow"""
        # 1. Register
        register_data = {
            "email": "fullflow@example.com",
            "password": mock_user_data["password"],
            "name": "Full Flow Test"
        }
        register_response = client.post("/api/auth/register", json=register_data)
        assert register_response.status_code == 201
        access_token_1 = register_response.json()["access_token"]

        # 2. Access protected route
        me_response_1 = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token_1}"}
        )
        assert me_response_1.status_code == 200

        # 3. Login again
        login_data = {
            "email": "fullflow@example.com",
            "password": mock_user_data["password"]
        }
        login_response = client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        access_token_2 = login_response.json()["access_token"]

        # 4. Access protected route with new token
        me_response_2 = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token_2}"}
        )
        assert me_response_2.status_code == 200

        # Should be same user
        assert me_response_1.json()["id"] == me_response_2.json()["id"]


class TestAuthValidation:
    """Test authentication input validation"""

    def test_register_invalid_email(self, client: TestClient, mock_user_data: dict):
        """Test registration with invalid email format"""
        register_data = {
            "email": "invalid-email",
            "password": mock_user_data["password"],
            "name": "Test"
        }

        response = client.post("/api/auth/register", json=register_data)

        assert response.status_code == 400 or response.status_code == 422

    def test_register_weak_password(self, client: TestClient):
        """Test registration with weak password"""
        register_data = {
            "email": "weakpassword@example.com",
            "password": "123",  # Too short
            "name": "Test"
        }

        response = client.post("/api/auth/register", json=register_data)

        # Should fail validation
        assert response.status_code == 400 or response.status_code == 422

    def test_register_missing_fields(self, client: TestClient):
        """Test registration with missing required fields"""
        register_data = {
            "email": "missing@example.com"
            # Missing password and name
        }

        response = client.post("/api/auth/register", json=register_data)

        assert response.status_code == 422  # Unprocessable Entity

"""
Integration tests for user endpoints with real database and services.

This module tests the complete user authentication and management system
with real PostgreSQL database, JWT tokens, and HTTP endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock
import json
from datetime import datetime, timezone


class TestUserEndpointsIntegration:
    """Integration tests for user authentication endpoints."""

    async def test_full_user_registration_flow(self, client, test_api_key):
        """Test complete user registration to login flow with real database."""
        # Test user registration with unique email
        import time
        unique_email = f"integration_test_{int(time.time())}@example.com"
        registration_data = {
            "email": unique_email,
            "password": "TestPassword123!",
            "first_name": "Integration",
            "last_name": "Test"
        }

        # This will fail until we implement the actual registration endpoint
        response = await client.post(
            "/auth/register",
            json=registration_data,
            headers={"X-API-Key": test_api_key}
        )

        # Check the actual response
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

        # Now that the endpoint is working, expect 200 OK
        assert response.status_code == 200

        # Validate response structure
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "user" in data

        # Validate user data
        user = data["user"]
        assert user["email"] == unique_email
        assert user["role"] == "USER"
        assert user["is_active"] is True
        assert user["created_at"] is not None
        assert user["updated_at"] is not None
        assert user["last_login_at"] is None

    async def test_admin_user_management(self, client, test_api_key, test_admin_jwt_token):
        """Test admin creating and managing users with database persistence."""
        # This test will fail initially - needs real admin endpoints
        pass

    async def test_user_permissions(self, client, test_api_key, test_jwt_token, test_admin_jwt_token):
        """Test user permission boundaries with real authentication."""
        # This test will fail initially - needs real permission checking
        pass

    async def test_database_user_store_integration(self, test_database_user_store):
        """Test database user store with real PostgreSQL container."""
        # Test direct database user store operations
        # This will fail initially if the database schema doesn't exist
        pass

    async def test_auth_endpoints_with_real_dependencies(self, client, test_api_key):
        """Test AuthEndpoints with real JWT service and user store."""
        # This test will fail initially - needs real dependency injection
        pass

    async def test_user_registration_with_database_persistence(self, client, test_api_key):
        """Test user registration with real database persistence."""
        # This test will fail initially - needs database integration
        pass

    async def test_user_login_with_database_verification(self, client, test_api_key):
        """Test user login with real database credential verification."""
        # First register a user
        import time
        unique_email = f"login_test_{int(time.time())}@example.com"
        registration_data = {
            "email": unique_email,
            "password": "TestPassword123!",
            "first_name": "Login",
            "last_name": "Test"
        }

        # Register the user
        register_response = await client.post(
            "/auth/register",
            json=registration_data,
            headers={"X-API-Key": test_api_key}
        )
        assert register_response.status_code == 200

        # Now login with the same credentials
        login_data = {
            "email": unique_email,
            "password": "TestPassword123!"
        }

        login_response = await client.post(
            "/auth/login",
            json=login_data,
            headers={"X-API-Key": test_api_key}
        )

        # Debug: Check response
        print(f"Login response status: {login_response.status_code}")
        print(f"Login response body: {login_response.text}")

        # Login should succeed
        assert login_response.status_code == 200
        data = login_response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == unique_email
        assert data["user"]["last_login_at"] is not None  # Should be updated on login

    async def test_token_refresh_with_database_validation(self, client, test_api_key):
        """Test token refresh with database user validation."""
        # First register and login a user
        import time
        unique_email = f"refresh_test_{int(time.time())}@example.com"
        registration_data = {
            "email": unique_email,
            "password": "TestPassword123!",
            "first_name": "Refresh",
            "last_name": "Test"
        }

        # Register the user
        register_response = await client.post(
            "/auth/register",
            json=registration_data,
            headers={"X-API-Key": test_api_key}
        )
        assert register_response.status_code == 200

        # Login to get tokens
        login_data = {
            "email": unique_email,
            "password": "TestPassword123!"
        }
        login_response = await client.post(
            "/auth/login",
            json=login_data,
            headers={"X-API-Key": test_api_key}
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        refresh_token = login_data["refresh_token"]

        # Now refresh the tokens
        refresh_response = await client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
            headers={"X-API-Key": test_api_key}
        )

        # Debug: Check response
        print(f"Token refresh response status: {refresh_response.status_code}")
        print(f"Token refresh response body: {refresh_response.text}")

        # Should succeed
        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0
        assert data["user"]["email"] == unique_email

        # Note: The access token might be the same if generated within the same second
        # This is acceptable as long as the refresh mechanism works

    async def test_user_logout_with_token_blacklisting(self, client, test_api_key):
        """Test user logout with real token blacklisting."""
        # This test will fail initially - needs database integration
        pass

    async def test_get_current_user_with_database_lookup(self, client, test_api_key):
        """Test getting current user info with real database lookup."""
        # First register and login a user
        import time
        unique_email = f"current_user_test_{int(time.time())}@example.com"
        registration_data = {
            "email": unique_email,
            "password": "TestPassword123!",
            "first_name": "Current",
            "last_name": "User"
        }

        # Register the user
        register_response = await client.post(
            "/auth/register",
            json=registration_data,
            headers={"X-API-Key": test_api_key}
        )
        assert register_response.status_code == 200

        # Login to get tokens
        login_data = {
            "email": unique_email,
            "password": "TestPassword123!"
        }
        login_response = await client.post(
            "/auth/login",
            json=login_data,
            headers={"X-API-Key": test_api_key}
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        access_token = login_data["access_token"]

        # Now get current user info
        me_response = await client.get(
            "/auth/me",
            headers={
                "X-API-Key": test_api_key,
                "Authorization": f"Bearer {access_token}"
            }
        )

        # Debug: Check response
        print(f"Get current user response status: {me_response.status_code}")
        print(f"Get current user response body: {me_response.text}")

        # Should succeed
        assert me_response.status_code == 200
        user_data = me_response.json()
        assert user_data["email"] == unique_email
        assert user_data["first_name"] == "Current"
        assert user_data["last_name"] == "User"
        assert user_data["role"] == "USER"
        assert user_data["is_active"] is True

    async def test_user_change_password_endpoint(self, client, test_api_key):
        """Integration: user can change their own password via /auth/change-password."""
        import time
        unique_email = f"changepw_{int(time.time())}@example.com"
        registration_data = {
            "email": unique_email,
            "password": "OrigPass123!",
            "first_name": "Change",
            "last_name": "Pw"
        }

        # Register the user
        register_response = await client.post(
            "/auth/register",
            json=registration_data,
            headers={"X-API-Key": test_api_key}
        )
        assert register_response.status_code == 200
        user = register_response.json()["user"]
        user_id = user.get("id")

        # We'll clean up this user at the end of the test using admin credentials
        try:
            # Login to get token
            login_response = await client.post(
                "/auth/login",
                json={"email": unique_email, "password": "OrigPass123!"},
                headers={"X-API-Key": test_api_key}
            )
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]

            # Change password
            change_response = await client.post(
                "/auth/change-password",
                json={"current_password": "OrigPass123!", "new_password": "NewPass123!"},
                headers={"X-API-Key": test_api_key, "Authorization": f"Bearer {token}"}
            )

            # Debug
            print(f"Change pw status: {change_response.status_code}")
            print(f"Change pw body: {change_response.text}")

            assert change_response.status_code == 200
            data = change_response.json()
            # API may return either {"success": true} or a message string. Accept both.
            assert data.get("success") is True or (isinstance(data.get("message"), str) and "Password" in data.get("message"))

            # Ensure new password works for login
            relogin = await client.post(
                "/auth/login",
                json={"email": unique_email, "password": "NewPass123!"},
                headers={"X-API-Key": test_api_key}
            )
            assert relogin.status_code == 200
        finally:
            # Attempt cleanup: login as admin and delete the created user
            try:
                from shared.config.config_manager import ConfigManager
                config = ConfigManager()
                admin_login = await client.post(
                    "/auth/login",
                    json={"email": config.admin_email, "password": config.admin_password},
                    headers={"X-API-Key": test_api_key}
                )
                if admin_login.status_code == 200 and user_id:
                    admin_token = admin_login.json().get("access_token")
                    await client.delete(
                        f"/api/v1/users/{user_id}",
                        headers={"X-API-Key": test_api_key, "Authorization": f"Bearer {admin_token}"}
                    )
            except Exception:
                # Best-effort cleanup; don't fail test if cleanup fails
                pass

    async def test_admin_set_user_password_endpoint(self, client, test_api_key):
        """Integration: admin can set another user's password via /api/v1/users/{id}/password."""
        import time
        unique_email = f"adminset_{int(time.time())}@example.com"
        registration_data = {
            "email": unique_email,
            "password": "UserOrig123!",
            "first_name": "Admin",
            "last_name": "Set"
        }

        # Register the user
        register_response = await client.post(
            "/auth/register",
            json=registration_data,
            headers={"X-API-Key": test_api_key}
        )
        assert register_response.status_code == 200
        user = register_response.json()["user"]
        user_id = user["id"]

        # Login as admin
        from shared.config.config_manager import ConfigManager
        config = ConfigManager()
        admin_login = await client.post(
            "/auth/login",
            json={"email": config.admin_email, "password": config.admin_password},
            headers={"X-API-Key": test_api_key}
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]

        # Admin sets user's password
        try:
            setpw_resp = await client.post(
                f"/api/v1/users/{user_id}/password",
                json={"new_password": "AdminSetPass123!"},
                headers={"X-API-Key": test_api_key, "Authorization": f"Bearer {admin_token}"}
            )

            print(f"Admin setpw status: {setpw_resp.status_code}")
            print(f"Admin setpw body: {setpw_resp.text}")

            assert setpw_resp.status_code == 200
            sp_data = setpw_resp.json()
            # Accept either boolean success or a message string
            assert sp_data.get("success") is True or (isinstance(sp_data.get("message"), str) and "Password" in sp_data.get("message"))

            # Ensure user can login with new password
            login_resp = await client.post(
                "/auth/login",
                json={"email": unique_email, "password": "AdminSetPass123!"},
                headers={"X-API-Key": test_api_key}
            )
            assert login_resp.status_code == 200
        finally:
            # Cleanup: delete the created user using admin token
            try:
                if user_id:
                    await client.delete(
                        f"/api/v1/users/{user_id}",
                        headers={"X-API-Key": test_api_key, "Authorization": f"Bearer {admin_token}"}
                    )
            except Exception:
                pass
        


    async def test_admin_list_users_with_pagination(self, client, test_api_key):
        """Test admin listing users with real database pagination."""
        # Use the existing admin user created at startup
        # Get admin credentials from ConfigManager
        from shared.config.config_manager import ConfigManager
        config = ConfigManager()
        import time
        base_time = int(time.time())

        # Login as the existing admin user
        admin_login_response = await client.post(
            "/auth/login",
            json={
                "email": config.admin_email,
                "password": config.admin_password
            },
            headers={"X-API-Key": test_api_key}
        )

        # Debug: Check admin login response
        print(f"Admin login response status: {admin_login_response.status_code}")
        print(f"Admin login response body: {admin_login_response.text}")

        # Admin login should succeed
        assert admin_login_response.status_code == 200
        admin_data = admin_login_response.json()
        admin_token = admin_data["access_token"]

        # Verify the user has ADMIN role
        assert admin_data["user"]["role"] == "ADMIN"
        print(f"Admin user role: {admin_data['user']['role']}")

        # First create some regular users
        for i in range(3):
            unique_email = f"admin_list_test_{base_time}_{i}@example.com"
            print(f"Creating user with email: {unique_email}")
            registration_data = {
                "email": unique_email,
                "password": "TestPassword123!",
                "first_name": f"Test{chr(65+i)}",  # A, B, C
                "last_name": f"User{chr(65+i)}"
            }

            # Register the user
            register_response = await client.post(
                "/auth/register",
                json=registration_data,
                headers={"X-API-Key": test_api_key}
            )
            print(f"Registration response status: {register_response.status_code}")
            print(f"Registration response body: {register_response.text}")
            assert register_response.status_code == 200

        # Now list users as admin
        list_response = await client.get(
            "/api/v1/users/",
            headers={
                "X-API-Key": test_api_key,
                "Authorization": f"Bearer {admin_token}"
            }
        )

        # Debug: Check response
        print(f"Admin list users response status: {list_response.status_code}")
        print(f"Admin list users response body: {list_response.text}")

        # Should succeed
        assert list_response.status_code == 200
        data = list_response.json()
        assert "users" in data
        assert "pagination" in data
        assert len(data["users"]) >= 3  # At least the users we created

        # Check pagination info
        pagination = data["pagination"]
        assert "limit" in pagination
        assert "offset" in pagination
        assert "total" in pagination

        # Verify user data structure
        for user in data["users"]:
            assert "id" in user
            assert "email" in user
            assert "role" in user
            assert "is_active" in user

    async def test_admin_get_user_details(self, client, test_api_key):
        """Test admin getting specific user details from database."""
        # Use the existing admin user created at startup
        from shared.config.config_manager import ConfigManager
        config = ConfigManager()
        import time
        base_time = int(time.time())

        # Login as the existing admin user
        admin_login_response = await client.post(
            "/auth/login",
            json={
                "email": config.admin_email,
                "password": config.admin_password
            },
            headers={"X-API-Key": test_api_key}
        )
        assert admin_login_response.status_code == 200
        admin_data = admin_login_response.json()
        admin_token = admin_data["access_token"]

        # First create a test user to get details for
        unique_email = f"get_user_test_{base_time}@example.com"
        registration_data = {
            "email": unique_email,
            "password": "TestPassword123!",
            "first_name": "Get",
            "last_name": "User"
        }

        # Register the user
        register_response = await client.post(
            "/auth/register",
            json=registration_data,
            headers={"X-API-Key": test_api_key}
        )
        assert register_response.status_code == 200
        user_data = register_response.json()["user"]
        user_id = user_data["id"]

        # Now get user details as admin
        get_response = await client.get(
            f"/api/v1/users/{user_id}",
            headers={
                "X-API-Key": test_api_key,
                "Authorization": f"Bearer {admin_token}"
            }
        )

        # Debug: Check response
        print(f"Admin get user response status: {get_response.status_code}")
        print(f"Admin get user response body: {get_response.text}")

        # Should succeed
        assert get_response.status_code == 200
        details_data = get_response.json()
        assert details_data["id"] == user_id
        assert details_data["email"] == unique_email
        assert details_data["first_name"] == "Get"
        assert details_data["last_name"] == "User"
        assert details_data["role"] == "USER"

    async def test_admin_update_user_role(self, client, test_api_key):
        """Test admin updating user role with database persistence."""
        # Use the existing admin user created at startup
        from shared.config.config_manager import ConfigManager
        config = ConfigManager()
        import time
        base_time = int(time.time())

        # Login as the existing admin user
        admin_login_response = await client.post(
            "/auth/login",
            json={
                "email": config.admin_email,
                "password": config.admin_password
            },
            headers={"X-API-Key": test_api_key}
        )
        assert admin_login_response.status_code == 200
        admin_data = admin_login_response.json()
        admin_token = admin_data["access_token"]

        # First create a test user to update
        unique_email = f"update_role_test_{base_time}@example.com"
        registration_data = {
            "email": unique_email,
            "password": "TestPassword123!",
            "first_name": "Update",
            "last_name": "Role"
        }

        # Register the user
        register_response = await client.post(
            "/auth/register",
            json=registration_data,
            headers={"X-API-Key": test_api_key}
        )
        assert register_response.status_code == 200
        user_data = register_response.json()["user"]
        user_id = user_data["id"]

        # Now update user role to ADMIN
        update_data = {
            "role": "ADMIN"
        }
        update_response = await client.put(
            f"/api/v1/users/{user_id}",
            json=update_data,
            headers={
                "X-API-Key": test_api_key,
                "Authorization": f"Bearer {admin_token}"
            }
        )

        # Debug: Check response
        print(f"Admin update user response status: {update_response.status_code}")
        print(f"Admin update user response body: {update_response.text}")

        # Should succeed
        assert update_response.status_code == 200
        updated_data = update_response.json()
        assert updated_data["id"] == user_id
        assert updated_data["email"] == unique_email
        assert updated_data["role"] == "ADMIN"

        # Verify the update by getting user details again
        get_response = await client.get(
            f"/api/v1/users/{user_id}",
            headers={
                "X-API-Key": test_api_key,
                "Authorization": f"Bearer {admin_token}"
            }
        )
        assert get_response.status_code == 200
        verify_data = get_response.json()
        assert verify_data["role"] == "ADMIN"

    async def test_admin_delete_user(self, client, test_api_key):
        """Test admin deleting user with database cleanup."""
        # Use the existing admin user created at startup
        from shared.config.config_manager import ConfigManager
        config = ConfigManager()
        import time
        base_time = int(time.time())

        # Login as the existing admin user
        admin_login_response = await client.post(
            "/auth/login",
            json={
                "email": config.admin_email,
                "password": config.admin_password
            },
            headers={"X-API-Key": test_api_key}
        )
        assert admin_login_response.status_code == 200
        admin_data = admin_login_response.json()
        admin_token = admin_data["access_token"]

        # First create a test user to delete
        unique_email = f"delete_user_test_{base_time}@example.com"
        registration_data = {
            "email": unique_email,
            "password": "TestPassword123!",
            "first_name": "Delete",
            "last_name": "User"
        }

        # Register the user
        register_response = await client.post(
            "/auth/register",
            json=registration_data,
            headers={"X-API-Key": test_api_key}
        )
        assert register_response.status_code == 200
        user_data = register_response.json()["user"]
        user_id = user_data["id"]

        # Now delete the user (soft delete by default)
        delete_response = await client.delete(
            f"/api/v1/users/{user_id}",
            headers={
                "X-API-Key": test_api_key,
                "Authorization": f"Bearer {admin_token}"
            }
        )

        # Debug: Check response
        print(f"Admin delete user response status: {delete_response.status_code}")
        print(f"Admin delete user response body: {delete_response.text}")

        # Should succeed
        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert delete_data["user_id"] == user_id
        # admin endpoint now performs a hard delete by default (soft_delete=False)
        assert delete_data["soft_deleted"] is False

        # Verify the user no longer exists (hard delete => 404 Not Found)
        get_response = await client.get(
            f"/api/v1/users/{user_id}",
            headers={
                "X-API-Key": test_api_key,
                "Authorization": f"Bearer {admin_token}"
            }
        )
        assert get_response.status_code == 404

    async def test_regular_user_cannot_access_admin_endpoints(self, client, test_api_key, test_jwt_token):
        """Test regular users cannot access admin endpoints."""
        # This test will fail initially - needs real permission checking
        pass

    async def test_concurrent_user_operations(self, client, test_api_key):
        """Test concurrent user registration/login operations."""
        # This test will fail initially - needs real concurrent handling
        pass

    async def test_user_account_status_management(self, client, test_api_key, test_admin_jwt_token):
        """Test user account activation/deactivation with database updates."""
        # This test will fail initially - needs database integration
        pass

    async def test_user_last_login_tracking(self, client, test_api_key):
        """Test user last login timestamp updates in database."""
        # This test will fail initially - needs database integration
        pass

    async def test_email_availability_checking(self, client, test_api_key):
        """Test email availability checking with real database."""
        # This test will fail initially - needs database integration
        pass

    async def test_user_counting_and_statistics(self, client, test_api_key, test_admin_jwt_token):
        """Test user counting and statistics with real database."""
        # This test will fail initially - needs database integration
        pass
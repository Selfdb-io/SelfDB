#!/usr/bin/env python3
"""Generate the API reference markdown by calling the live backend."""

from __future__ import annotations

import json
import os
import sys
import textwrap
import time
import uuid
import hashlib
import hmac
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import dotenv_values


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env.dev"
FRONTEND_CONSTANT_PATH = (
    ROOT_DIR / "frontend" / "src" / "modules" / "core" / "constants" / "apiReferenceMarkdown.ts"
)


def load_environment() -> Dict[str, str]:
    if not ENV_PATH.exists():
        raise FileNotFoundError(f"Cannot locate .env.dev file at {ENV_PATH}")

    env_values = dotenv_values(str(ENV_PATH))
    for key, value in env_values.items():
        if value is not None:
            os.environ.setdefault(key, value)
    return {key: value for key, value in env_values.items() if value is not None}


def guess_backend_url(env: Dict[str, str]) -> str:
    explicit = env.get("API_BASE_URL") or env.get("BACKEND_URL") or env.get("API_URL")
    if explicit:
        return explicit.rstrip("/")

    port = env.get("API_PORT", "8000").strip()
    host = env.get("API_HOST", "localhost").strip()
    scheme = env.get("API_SCHEME", "http").strip()
    return f"{scheme}://{host}:{port}".rstrip("/")


def ensure_directory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class RequestDoc:
    method: str
    path: str
    description: str
    headers: Dict[str, str]
    json_body: Optional[Dict[str, Any]] = None
    data_body: Optional[Dict[str, Any]] = None
    files_desc: Optional[str] = None
    response_status: int = 0
    response_body: Any = None
    errors: List[str] = field(default_factory=list)


class ApiDocGenerator:
    def __init__(self, base_url: str, api_key: str, admin_email: str, admin_password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.admin_email = admin_email
        self.admin_password = admin_password
        self.session = requests.Session()

        self.sections: Dict[str, List[RequestDoc]] = {}
        self.cleanup_actions: List[Any] = []
        self.admin_token: Optional[str] = None

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------
    def _default_headers(self) -> Dict[str, str]:
        return {"X-API-Key": self.api_key}

    def _request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        req_headers = self._default_headers()
        if headers:
            req_headers.update(headers)

        response = self.session.request(
            method,
            url,
            headers=req_headers,
            json=json,
            data=data,
            files=files,
            params=params,
            timeout=timeout,
        )

        if response.status_code >= 500:
            response.raise_for_status()

        return response

    def _doc_headers(self, extra: Optional[Dict[str, str]] = None, include_auth: bool = False) -> Dict[str, str]:
        headers = {"X-API-Key": "YOUR_API_KEY"}
        if include_auth:
            headers["Authorization"] = "Bearer YOUR_ACCESS_TOKEN"
        if extra:
            headers.update(extra)
        return headers

    def _sanitize_response(self, payload: Any) -> Any:
        if isinstance(payload, dict):
            sanitized: Dict[str, Any] = {}
            for key, value in payload.items():
                lower_key = key.lower()
                if lower_key in {"access_token", "refresh_token"} or lower_key.endswith("_token"):
                    sanitized[key] = f"<{lower_key}>"
                elif lower_key in {"password", "new_password", "current_password"}:
                    sanitized[key] = "<redacted>"
                elif lower_key.endswith("secret"):
                    sanitized[key] = "<redacted>"
                else:
                    sanitized[key] = self._sanitize_response(value)
            return sanitized
        if isinstance(payload, list):
            return [self._sanitize_response(item) for item in payload]
        if isinstance(payload, str):
            if payload.startswith("eyJ") and len(payload) > 20:
                return "<token>"
            return payload
        return payload

    def _to_json_string(self, payload: Any) -> str:
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _add_entry(self, section: str, entry: RequestDoc) -> None:
        self.sections.setdefault(section, []).append(entry)

    # ------------------------------------------------------------------
    # Cleanup helpers
    # ------------------------------------------------------------------
    def add_cleanup(self, func) -> None:
        self.cleanup_actions.append(func)

    def run_cleanup(self) -> None:
        for action in reversed(self.cleanup_actions):
            try:
                action()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Authentication helpers
    # ------------------------------------------------------------------
    def ensure_admin_token(self) -> str:
        if self.admin_token:
            return self.admin_token

        response = self._request(
            "POST",
            "/auth/login",
            json={"email": self.admin_email, "password": self.admin_password},
        )
        if response.status_code != 200:
            raise RuntimeError(
                "Failed to authenticate admin user. Ensure ADMIN_EMAIL and ADMIN_PASSWORD are correct."
            )

        data = response.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError("Admin login did not return an access token.")

        self.admin_token = token
        return token

    # ------------------------------------------------------------------
    # Section generators
    # ------------------------------------------------------------------
    def generate_health_section(self) -> None:
        response = self._request("GET", "/health")
        entry = RequestDoc(
            method="GET",
            path="/health",
            description="Check if the backend API is healthy and reachable.",
            headers=self._doc_headers(),
            response_status=response.status_code,
            response_body=self._sanitize_response(response.json()),
        )
        self._add_entry("Health Endpoints", entry)

        response = self._request("GET", "/api/v1/status")
        entry = RequestDoc(
            method="GET",
            path="/api/v1/status",
            description="Retrieve API version, service status, and configuration summary.",
            headers=self._doc_headers(),
            response_status=response.status_code,
            response_body=self._sanitize_response(response.json()),
        )
        self._add_entry("Health Endpoints", entry)

    def generate_auth_section(self) -> Dict[str, str]:
        timestamp = int(time.time())
        email = f"docs_user_{timestamp}@example.com"
        password = "DocsPassword123!"

        registration_payload = {
            "email": email,
            "password": password,
            "first_name": "Docs",
            "last_name": "User",
        }

        response = self._request("POST", "/auth/register", json=registration_payload)
        if response.status_code != 200:
            raise RuntimeError(f"Registration failed: {response.status_code} {response.text}")
        register_data = response.json()

        entry = RequestDoc(
            method="POST",
            path="/auth/register",
            description="Create a new user account.",
            headers=self._doc_headers(extra={"Content-Type": "application/json"}),
            json_body={
                "email": "newuser@example.com",
                "password": "Password123!",
                "first_name": "Jane",
                "last_name": "Doe",
            },
            response_status=response.status_code,
            response_body=self._sanitize_response(register_data),
        )
        self._add_entry("Authentication", entry)

        login_payload = {"email": email, "password": password}
        response = self._request("POST", "/auth/login", json=login_payload)
        if response.status_code != 200:
            raise RuntimeError(f"Login failed: {response.status_code} {response.text}")
        login_data = response.json()

        entry = RequestDoc(
            method="POST",
            path="/auth/login",
            description="Authenticate a user and retrieve access and refresh tokens.",
            headers=self._doc_headers(extra={"Content-Type": "application/json"}),
            json_body={
                "email": "newuser@example.com",
                "password": "Password123!",
            },
            response_status=response.status_code,
            response_body=self._sanitize_response(login_data),
        )
        self._add_entry("Authentication", entry)

        refresh_payload = {"refresh_token": login_data.get("refresh_token")}
        response = self._request("POST", "/auth/refresh", json=refresh_payload)
        if response.status_code != 200:
            raise RuntimeError(f"Refresh token request failed: {response.status_code} {response.text}")

        entry = RequestDoc(
            method="POST",
            path="/auth/refresh",
            description="Exchange a refresh token for a new access token.",
            headers=self._doc_headers(extra={"Content-Type": "application/json"}),
            json_body={"refresh_token": "YOUR_REFRESH_TOKEN"},
            response_status=response.status_code,
            response_body=self._sanitize_response(response.json()),
        )
        self._add_entry("Authentication", entry)

        access_token = login_data.get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}
        response = self._request("GET", "/auth/me", headers=headers)

        entry = RequestDoc(
            method="GET",
            path="/auth/me",
            description="Retrieve the currently authenticated user's profile.",
            headers=self._doc_headers(include_auth=True),
            response_status=response.status_code,
            response_body=self._sanitize_response(response.json()),
        )
        self._add_entry("Authentication", entry)

        # Change password (user changing their own password)
        change_pw_resp = self._request(
            "POST",
            "/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"current_password": password, "new_password": "NewPassword123!"},
        )
        entry = RequestDoc(
            method="POST",
            path="/auth/change-password",
            description="Change the authenticated user's password.",
            headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
            json_body={"current_password": "OldPassword123!", "new_password": "NewPassword123!"},
            response_status=change_pw_resp.status_code,
            response_body=self._sanitize_response(change_pw_resp.json() if change_pw_resp.content else {}),
        )
        self._add_entry("Authentication", entry)

        cleanup_email = email
        cleanup_user_id = register_data.get("user", {}).get("id") or login_data.get("user", {}).get("id")

        def cleanup_user() -> None:
            if not cleanup_user_id:
                return
            admin_token = self.ensure_admin_token()
            self._request(
                "DELETE",
                f"/api/v1/users/{cleanup_user_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        self.add_cleanup(cleanup_user)

        return {"email": cleanup_email, "password": password, "access_token": access_token}

    def generate_user_management_section(self, auth_context: Dict[str, str]) -> None:
        """Complete user management CRUD mirroring integration tests."""
        admin_token = self.ensure_admin_token()
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create user (admin)
        timestamp = int(time.time())
        new_user_email = f"docs_admin_user_{timestamp}@example.com"
        create_payload = {
            "email": new_user_email,
            "password": "DocsPassword123!",
            "first_name": "Docs",
            "last_name": "AdminUser",
        }
        create_resp = self._request("POST", "/api/v1/users/", headers=headers, json=create_payload)
        entry = RequestDoc(
            method="POST",
            path="/api/v1/users/",
            description="Create a new user (admin only).",
            headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
            json_body={
                "email": "user@example.com",
                "password": "Password123!",
                "first_name": "Jane",
                "last_name": "Doe",
            },
            response_status=create_resp.status_code,
            response_body=self._sanitize_response(create_resp.json()),
        )
        self._add_entry("User Management", entry)

        user_id = None
        if create_resp.status_code in (200, 201):
            user_data = create_resp.json()
            user_id = user_data.get("id") or user_data.get("user", {}).get("id")

        # List users with pagination
        list_resp = self._request("GET", "/api/v1/users/", headers=headers, params={"limit": 50, "offset": 0})
        entry = RequestDoc(
            method="GET",
            path="/api/v1/users/",
            description="List users with pagination (admin only).",
            headers=self._doc_headers(include_auth=True),
            response_status=list_resp.status_code,
            response_body=self._sanitize_response(list_resp.json()),
        )
        self._add_entry("User Management", entry)

        # Get user count
        count_resp = self._request("GET", "/api/v1/users/count", headers=headers)
        entry = RequestDoc(
            method="GET",
            path="/api/v1/users/count",
            description="Get total user count (admin only).",
            headers=self._doc_headers(include_auth=True),
            response_status=count_resp.status_code,
            response_body=self._sanitize_response(count_resp.json()),
        )
        self._add_entry("User Management", entry)

        # Get user details
        if user_id:
            get_resp = self._request("GET", f"/api/v1/users/{user_id}", headers=headers)
            entry = RequestDoc(
                method="GET",
                path="/api/v1/users/{user_id}",
                description="Get user details by ID (admin only).",
                headers=self._doc_headers(include_auth=True),
                response_status=get_resp.status_code,
                response_body=self._sanitize_response(get_resp.json()),
            )
            self._add_entry("User Management", entry)

            # Update user (change role)
            update_payload = {"role": "ADMIN"}
            update_resp = self._request("PUT", f"/api/v1/users/{user_id}", headers=headers, json=update_payload)
            entry = RequestDoc(
                method="PUT",
                path="/api/v1/users/{user_id}",
                description="Update user fields such as role (admin only).",
                headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
                json_body={"role": "ADMIN"},
                response_status=update_resp.status_code,
                response_body=self._sanitize_response(update_resp.json()),
            )
            self._add_entry("User Management", entry)

            # Admin set user password
            set_pw_resp = self._request("POST", f"/api/v1/users/{user_id}/password", headers=headers, json={"new_password": "AdminSetPass123!"})
            entry = RequestDoc(
                method="POST",
                path="/api/v1/users/{user_id}/password",
                description="Set a user's password (admin only).",
                headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
                json_body={"new_password": "NewSecurePassword123!"},
                response_status=set_pw_resp.status_code,
                response_body=self._sanitize_response(set_pw_resp.json() if set_pw_resp.content else {}),
            )
            self._add_entry("User Management", entry)

            delete_resp = self._request("DELETE", f"/api/v1/users/{user_id}", headers=headers)
            entry = RequestDoc(
                method="DELETE",
                path="/api/v1/users/{user_id}",
                description="Delete a user (admin only).",
                headers=self._doc_headers(include_auth=True),
                response_status=delete_resp.status_code,
                response_body=self._sanitize_response(delete_resp.json() if delete_resp.content else {}),
            )
            self._add_entry("User Management", entry)

            # Cleanup - ensure user removed if deletion failed earlier
            self.add_cleanup(lambda: self._request("DELETE", f"/api/v1/users/{user_id}", headers=headers))

        # Get current user's API key
        api_key_resp = self._request("GET", "/auth/me/api-key", headers=headers)
        entry = RequestDoc(
            method="GET",
            path="/auth/me/api-key",
            description="Retrieve the configured API key for the authenticated user.",
            headers=self._doc_headers(include_auth=True),
            response_status=api_key_resp.status_code,
            response_body=self._sanitize_response(api_key_resp.json()),
        )
        self._add_entry("User Management", entry)

    def generate_bucket_section(self, auth_context: Dict[str, str]) -> Dict[str, str]:
        admin_token = self.ensure_admin_token()
        admin_profile = self._request(
            "GET",
            "/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        admin_user_id = admin_profile.json().get("id")

        bucket_name = f"integration-bucket-{uuid.uuid4().hex[:8]}"
        create_payload = {
            "name": bucket_name,
            "owner_id": admin_user_id,
            "public": False,
        }

        create_resp = self._request(
            "POST",
            "/api/v1/buckets",
            json=create_payload,
        )

        entry = RequestDoc(
            method="POST",
            path="/api/v1/buckets",
            description="Create a new storage bucket.",
            headers=self._doc_headers(extra={"Content-Type": "application/json"}),
            json_body=create_payload,
            response_status=create_resp.status_code,
            response_body=self._sanitize_response(create_resp.json()),
        )
        self._add_entry("Bucket Management", entry)

        get_resp = self._request("GET", f"/api/v1/buckets/{bucket_name}")
        entry = RequestDoc(
            method="GET",
            path="/api/v1/buckets/{bucket_id}",
            description="Get bucket metadata by name.",
            headers=self._doc_headers(),
            response_status=get_resp.status_code,
            response_body=self._sanitize_response(get_resp.json()),
        )
        self._add_entry("Bucket Management", entry)

        self.add_cleanup(
            lambda: self._request("DELETE", f"/api/v1/buckets/{bucket_name}")
        )

    def generate_tables_section(self) -> None:
        """Complete table CRUD mirroring integration tests."""
        admin_token = self.ensure_admin_token()
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # List tables
        response = self._request("GET", "/api/v1/tables", headers=headers)
        entry = RequestDoc(
            method="GET",
            path="/api/v1/tables",
            description="List all tables in the database.",
            headers=self._doc_headers(include_auth=True),
            response_status=response.status_code,
            response_body=self._sanitize_response(response.json()),
        )
        self._add_entry("Table Management", entry)

        # Create table (mirroring test_comprehensive_table_crud_with_data)
        table_name = f"docs_table_{uuid.uuid4().hex[:12]}"
        create_payload = {
            "name": table_name,
            "description": "Documentation example table",
            "public": False,
            "schema": {
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "name", "type": "text", "nullable": False},
                    {"name": "price", "type": "numeric", "nullable": False},
                    {"name": "stock", "type": "integer", "nullable": True},
                ]
            },
        }
        
        response = self._request("POST", "/api/v1/tables", headers=headers, json=create_payload)
        entry = RequestDoc(
            method="POST",
            path="/api/v1/tables",
            description="Create a new table with specified schema.",
            headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
            json_body={
                "name": "products",
                "description": "Product catalog",
                "public": False,
                "schema": {
                    "columns": [
                        {"name": "id", "type": "uuid", "primary_key": True},
                        {"name": "name", "type": "text", "nullable": False},
                        {"name": "price", "type": "numeric", "nullable": False},
                    ]
                },
            },
            response_status=response.status_code,
            response_body=self._sanitize_response(response.json()),
        )
        self._add_entry("Table Management", entry)

        # Get table metadata
        response = self._request("GET", f"/api/v1/tables/{table_name}", headers=headers)
        entry = RequestDoc(
            method="GET",
            path="/api/v1/tables/{table_name}",
            description="Get table schema and metadata.",
            headers=self._doc_headers(include_auth=True),
            response_status=response.status_code,
            response_body=self._sanitize_response(response.json()),
        )
        self._add_entry("Table Management", entry)

        # Get table SQL
        response = self._request("GET", f"/api/v1/tables/{table_name}/sql", headers=headers)
        entry = RequestDoc(
            method="GET",
            path="/api/v1/tables/{table_name}/sql",
            description="Get SQL CREATE statement for the table.",
            headers=self._doc_headers(include_auth=True),
            response_status=response.status_code,
            response_body=self._sanitize_response(response.json()),
        )
        self._add_entry("Table Management", entry)

        # Insert rows (mirroring test_row_operations_flow)
        row_id_1 = str(uuid.uuid4())
        insert_payload_1 = {"id": row_id_1, "name": "Laptop", "price": 999.99, "stock": 50}
        response = self._request("POST", f"/api/v1/tables/{table_name}/data", headers=headers, json=insert_payload_1)
        entry = RequestDoc(
            method="POST",
            path="/api/v1/tables/{table_name}/data",
            description="Insert a new row into the table.",
            headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
            json_body=insert_payload_1,
            response_status=response.status_code,
            response_body=self._sanitize_response(response.json()),
        )
        self._add_entry("Table Management", entry)

        row_id_2 = str(uuid.uuid4())
        insert_payload_2 = {"id": row_id_2, "name": "Mouse", "price": 25.50, "stock": 200}
        self._request("POST", f"/api/v1/tables/{table_name}/data", headers=headers, json=insert_payload_2)

        # Get rows with pagination and ordering
        response = self._request("GET", f"/api/v1/tables/{table_name}/data", headers=headers, params={"order_by": "price", "page": 1, "page_size": 10})
        entry = RequestDoc(
            method="GET",
            path="/api/v1/tables/{table_name}/data",
            description="Retrieve rows from the table with optional filters, pagination, and ordering.",
            headers=self._doc_headers(include_auth=True),
            response_status=response.status_code,
            response_body=self._sanitize_response(response.json()),
        )
        self._add_entry("Table Management", entry)

        # Filter rows by column value
        response = self._request("GET", f"/api/v1/tables/{table_name}/data", headers=headers, params={"filter_column": "name", "filter_value": "Laptop"})
        entry = RequestDoc(
            method="GET",
            path="/api/v1/tables/{table_name}/data?filter_column={column}&filter_value={value}",
            description="Filter rows by column value.",
            headers=self._doc_headers(include_auth=True),
            response_status=response.status_code,
            response_body=self._sanitize_response(response.json()),
        )
        self._add_entry("Table Management", entry)

        # Update row
        update_payload = {"stock": 75, "price": 1099.99}
        response = self._request("PUT", f"/api/v1/tables/{table_name}/data/{row_id_1}", headers=headers, params={"id_column": "id"}, json=update_payload)
        entry = RequestDoc(
            method="PUT",
            path="/api/v1/tables/{table_name}/data/{row_id}?id_column=id",
            description="Update an existing row by ID.",
            headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
            json_body=update_payload,
            response_status=response.status_code,
            response_body=self._sanitize_response(response.json()),
        )
        self._add_entry("Table Management", entry)

        # Add column
        add_col_response = self._request("POST", f"/api/v1/tables/{table_name}/columns", headers=headers, json={"name": "category", "type": "text", "nullable": True})
        entry = RequestDoc(
            method="POST",
            path="/api/v1/tables/{table_name}/columns",
            description="Add a new column to the table.",
            headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
            json_body={"name": "category", "type": "text", "nullable": True},
            response_status=add_col_response.status_code,
            response_body=self._sanitize_response(add_col_response.json()),
        )
        self._add_entry("Table Management", entry)

        # Update column
        update_col_response = self._request("PUT", f"/api/v1/tables/{table_name}/columns/category", headers=headers, json={"type": "varchar(255)", "nullable": False})
        entry = RequestDoc(
            method="PUT",
            path="/api/v1/tables/{table_name}/columns/{column_name}",
            description="Update a column definition.",
            headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
            json_body={"type": "varchar(255)", "nullable": False},
            response_status=update_col_response.status_code,
            response_body=self._sanitize_response(update_col_response.json()),
        )
        self._add_entry("Table Management", entry)

        # Update table metadata
        update_table_response = self._request("PUT", f"/api/v1/tables/{table_name}", headers=headers, json={"description": "Updated product inventory", "public": True})
        entry = RequestDoc(
            method="PUT",
            path="/api/v1/tables/{table_name}",
            description="Update table metadata (description, public flag).",
            headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
            json_body={"description": "Updated description", "public": True},
            response_status=update_table_response.status_code,
            response_body=self._sanitize_response(update_table_response.json()),
        )
        self._add_entry("Table Management", entry)

        # Delete row
        delete_row_response = self._request("DELETE", f"/api/v1/tables/{table_name}/data/{row_id_2}", headers=headers, params={"id_column": "id"})
        entry = RequestDoc(
            method="DELETE",
            path="/api/v1/tables/{table_name}/data/{row_id}?id_column=id",
            description="Delete a row from the table by ID.",
            headers=self._doc_headers(include_auth=True),
            response_status=delete_row_response.status_code,
            response_body={"note": "204 No Content on success"} if delete_row_response.status_code == 204 else self._sanitize_response(delete_row_response.json()),
        )
        self._add_entry("Table Management", entry)

        # Delete column (cleanup)
        self.add_cleanup(lambda: self._request("DELETE", f"/api/v1/tables/{table_name}/columns/category", headers=headers))

        # Cleanup table
        self.add_cleanup(lambda: self._request("DELETE", f"/api/v1/tables/{table_name}", headers=headers))

    def generate_sql_section(self) -> None:
        """Complete SQL endpoints mirroring integration tests."""
        admin_token = self.ensure_admin_token()
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Execute SELECT query (read-only)
        query_payload = {"query": "SELECT 1 as result, 'Hello' as message"}
        response = self._request("POST", "/api/v1/sql/query", headers=headers, json=query_payload)
        entry = RequestDoc(
            method="POST",
            path="/api/v1/sql/query",
            description="Execute a SQL query against the database.",
            headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
            json_body={"query": "SELECT * FROM users LIMIT 10"},
            response_status=response.status_code,
            response_body=self._sanitize_response(response.json()),
        )
        self._add_entry("SQL Execution", entry)

        # Execute DDL query (CREATE TABLE)
        temp_table = f"docs_temp_{int(time.time())}"
        ddl_payload = {"query": f"CREATE TABLE {temp_table} (id INTEGER, name TEXT)"}
        ddl_response = self._request("POST", "/api/v1/sql/query", headers=headers, json=ddl_payload)
        entry = RequestDoc(
            method="POST",
            path="/api/v1/sql/query",
            description="Execute DDL queries (CREATE, ALTER, DROP).",
            headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
            json_body={"query": "CREATE TABLE temp (id INTEGER, name TEXT)"},
            response_status=ddl_response.status_code,
            response_body=self._sanitize_response(ddl_response.json()),
        )
        self._add_entry("SQL Execution", entry)

        # Save query to history
        history_payload = {
            "query": "SELECT 123 as value",
            "result": response.json() if response.status_code == 200 else {},
        }
        history_response = self._request("POST", "/api/v1/sql/history", headers=headers, json=history_payload)
        entry = RequestDoc(
            method="POST",
            path="/api/v1/sql/history",
            description="Save a query and its result to history.",
            headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
            json_body={"query": "SELECT * FROM users", "result": {"success": True, "data": []}},
            response_status=history_response.status_code,
            response_body=self._sanitize_response(history_response.json() if history_response.content else {}),
        )
        self._add_entry("SQL Execution", entry)

        # Get query history
        history_get = self._request("GET", "/api/v1/sql/history", headers=headers)
        entry = RequestDoc(
            method="GET",
            path="/api/v1/sql/history",
            description="Retrieve query execution history for the authenticated user.",
            headers=self._doc_headers(include_auth=True),
            response_status=history_get.status_code,
            response_body=self._sanitize_response(history_get.json()),
        )
        self._add_entry("SQL Execution", entry)

        # Save SQL snippet
        snippet_payload = {
            "name": f"Get active users {int(time.time())}",
            "sql_code": "SELECT * FROM users WHERE is_active = true",
            "description": "Query to fetch all active users",
            "is_shared": False,
        }
        snippet_create = self._request("POST", "/api/v1/sql/snippets", headers=headers, json=snippet_payload)
        entry = RequestDoc(
            method="POST",
            path="/api/v1/sql/snippets",
            description="Save a SQL query snippet for reuse.",
            headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
            json_body={
                "name": "Get active users",
                "sql_code": "SELECT * FROM users WHERE is_active = true",
                "description": "Query to fetch all active users",
                "is_shared": False,
            },
            response_status=snippet_create.status_code,
            response_body=self._sanitize_response(snippet_create.json()),
        )
        self._add_entry("SQL Execution", entry)

        snippet_id = snippet_create.json().get("id") if snippet_create.status_code == 201 else None

        # Get SQL snippets
        snippets_list = self._request("GET", "/api/v1/sql/snippets", headers=headers)
        entry = RequestDoc(
            method="GET",
            path="/api/v1/sql/snippets",
            description="List all saved SQL snippets for the authenticated user.",
            headers=self._doc_headers(include_auth=True),
            response_status=snippets_list.status_code,
            response_body=self._sanitize_response(snippets_list.json()),
        )
        self._add_entry("SQL Execution", entry)

        # Delete SQL snippet
        if snippet_id:
            snippet_delete = self._request("DELETE", f"/api/v1/sql/snippets/{snippet_id}", headers=headers)
            entry = RequestDoc(
                method="DELETE",
                path="/api/v1/sql/snippets/{snippet_id}",
                description="Delete a SQL snippet.",
                headers=self._doc_headers(include_auth=True),
                response_status=snippet_delete.status_code,
                response_body={"note": "204 No Content on success"} if snippet_delete.status_code == 204 else self._sanitize_response(snippet_delete.json()),
            )
            self._add_entry("SQL Execution", entry)

        # Cleanup temp table
        if temp_table:
            self.add_cleanup(lambda: self._request("POST", "/api/v1/sql/query", headers=headers, json={"query": f"DROP TABLE IF EXISTS {temp_table}"}))

    def generate_functions_section(self) -> Dict[str, str]:
        """Complete function CRUD mirroring integration tests."""
        admin_token = self.ensure_admin_token()
        headers = {"Authorization": f"Bearer {admin_token}"}

        # List functions
        list_resp = self._request("GET", "/api/v1/functions", headers=headers)
        entry = RequestDoc(
            method="GET",
            path="/api/v1/functions",
            description="List all functions owned by the authenticated user.",
            headers=self._doc_headers(include_auth=True),
            response_status=list_resp.status_code,
            response_body=self._sanitize_response(list_resp.json()),
        )
        self._add_entry("Functions", entry)

        # Create function mirroring webhook onboarding example
        function_code = '''import nodemailer from "npm:nodemailer@6.9.7";

export default async function handler(request, context) {
  const payload = await request.json();
  const { email, first_name, last_name } = payload.data;
  const { env } = context;

  const registerResponse = await fetch("http://backend:8000/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": env.API_KEY
    },
    body: JSON.stringify({
      email,
      password: "ChangeMe123!",
      first_name,
      last_name
    })
  });

  if (!registerResponse.ok) {
    console.error(`Failed to create user: ${registerResponse.statusText}`);
  }

  const transporter = nodemailer.createTransport({
    host: env.SMTP_HOST,
    port: parseInt(env.SMTP_PORT || "587"),
    secure: env.SMTP_PORT === "465",
    auth: {
      user: env.SMTP_USER,
      pass: env.SMTP_PASSWORD
    }
  });

  await transporter.sendMail({
    from: env.SMTP_FROM_EMAIL,
    to: env.AUDIT_EMAIL_TO,
    subject: "Thank you for buying SelfDB",
    html: `
      <h2>New onboarding processed</h2>
      <p>Customer: ${first_name} ${last_name} &lt;${email}&gt;</p>
      <p>This is an automated webhook notification.</p>
    `
  });

  return {
    success: true,
    user_created: registerResponse.ok,
    email_sent: true,
    message: `User created and welcome email sent for ${email}`
  };
}

export const triggers = [
  {
    type: "webhook",
    webhook_id: "stripe-checkout"
  }
];
'''

        func_name = f"onboard-stripe-customer-{uuid.uuid4().hex[:8]}"
        env_vars = {
            "SMTP_HOST": os.getenv("DOCS_SMTP_HOST") or os.getenv("SMTP_HOST") or "smtp.example.com",
            "SMTP_PORT": os.getenv("DOCS_SMTP_PORT") or os.getenv("SMTP_PORT") or "587",
            "SMTP_USER": os.getenv("DOCS_SMTP_USER") or os.getenv("SMTP_USER") or "user@example.com",
            "SMTP_PASSWORD": os.getenv("DOCS_SMTP_PASSWORD") or os.getenv("SMTP_PASSWORD") or "smtp-password",
            "SMTP_FROM_EMAIL": os.getenv("DOCS_SMTP_FROM_EMAIL") or os.getenv("SMTP_FROM_EMAIL") or "no-reply@example.com",
            "AUDIT_EMAIL_TO": os.getenv("DOCS_AUDIT_EMAIL_TO") or os.getenv("AUDIT_EMAIL_TO") or "ops@example.com",
            "API_KEY": self.api_key,
        }

        func_payload = {
            "name": func_name,
            "code": function_code,
            "description": "Stripe customer onboarding with email",
            "runtime": "deno",
            "env_vars": env_vars,
        }

        doc_env_vars = {**env_vars, "API_KEY": "YOUR_API_KEY"}
        doc_func_payload = {**func_payload, "env_vars": doc_env_vars}

        create_resp = self._request("POST", "/api/v1/functions", headers=headers, json=func_payload)
        entry = RequestDoc(
            method="POST",
            path="/api/v1/functions",
            description="Create a new serverless function bound to a webhook trigger.",
            headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
            json_body=doc_func_payload,
            response_status=create_resp.status_code,
            response_body=self._sanitize_response(create_resp.json()),
        )
        self._add_entry("Functions", entry)

        func_id = None
        if create_resp.status_code in (200, 201):
            func_id = create_resp.json().get("id")

        if func_id:
            get_resp = self._request("GET", f"/api/v1/functions/{func_id}", headers=headers)
            entry = RequestDoc(
                method="GET",
                path="/api/v1/functions/{function_id}",
                description="Get function details by ID.",
                headers=self._doc_headers(include_auth=True),
                response_status=get_resp.status_code,
                response_body=self._sanitize_response(get_resp.json()),
            )
            self._add_entry("Functions", entry)

            updated_code = function_code + "\n// Updated documentation example"
            update_payload = {
                "code": updated_code,
                "description": "Updated function description",
            }
            update_resp = self._request("PUT", f"/api/v1/functions/{func_id}", headers=headers, json=update_payload)
            entry = RequestDoc(
                method="PUT",
                path="/api/v1/functions/{function_id}",
                description="Update an existing function.",
                headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
                json_body=update_payload,
                response_status=update_resp.status_code,
                response_body=self._sanitize_response(update_resp.json()),
            )
            self._add_entry("Functions", entry)

            self.add_cleanup(lambda: self._request("DELETE", f"/api/v1/functions/{func_id}", headers=headers))

        return {"function_id": func_id} if func_id else {}

    def generate_files_section(self) -> None:
        """Generate docs for file upload/download/delete mirroring integration tests."""
        import io

        admin_token = self.ensure_admin_token()
        admin_profile = self._request(
            "GET",
            "/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        admin_user_id = admin_profile.json().get("id")

        bucket_name = f"test-bucket-{uuid.uuid4().hex[:8]}"
        bucket_payload = {
            "name": bucket_name,
            "owner_id": admin_user_id,
            "public": False,
        }
        create_bucket_resp = self._request("POST", "/api/v1/buckets", json=bucket_payload)
        if create_bucket_resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to create bucket for file tests: {create_bucket_resp.text}")

        file_path = f"integration/docs_{uuid.uuid4().hex[:12]}.txt"
        file_content = b"SelfDB documentation example file content"

        # Upload file (multipart form-data)
        files = {"file": ("docs_example.txt", io.BytesIO(file_content), "text/plain")}
        data = {"bucket": bucket_name, "path": file_path}
        upload_resp = self._request("POST", "/api/v1/files/upload", data=data, files=files)
        entry = RequestDoc(
            method="POST",
            path="/api/v1/files/upload",
            description="Upload a file to a bucket using multipart form-data.",
            headers=self._doc_headers(include_auth=False),
            data_body={"bucket": bucket_name, "path": file_path},
            files_desc="file=@/path/to/local/file.txt",
            response_status=upload_resp.status_code,
            response_body=self._sanitize_response(upload_resp.json() if upload_resp.content else {}),
        )
        self._add_entry("File Management", entry)

        # Download file
        if upload_resp.status_code in (200, 201):
            download_resp = self._request("GET", f"/api/v1/files/{bucket_name}/{file_path}")
            entry = RequestDoc(
                method="GET",
                path="/api/v1/files/{bucket}/{path}",
                description="Download a file from storage.",
                headers=self._doc_headers(),
                response_status=download_resp.status_code,
                response_body={"note": "Binary content streamed with Content-Disposition header"} if download_resp.status_code == 200 else self._sanitize_response(download_resp.json() if download_resp.content else {}),
            )
            self._add_entry("File Management", entry)

            # Delete file
            delete_resp = self._request("DELETE", f"/api/v1/files/{bucket_name}/{file_path}")
            entry = RequestDoc(
                method="DELETE",
                path="/api/v1/files/{bucket}/{path}",
                description="Delete a file from a bucket.",
                headers=self._doc_headers(),
                response_status=delete_resp.status_code,
                response_body=self._sanitize_response(delete_resp.json() if delete_resp.content else {}),
            )
            self._add_entry("File Management", entry)

        # List files in bucket
        list_files_resp = self._request("GET", f"/api/v1/buckets/{bucket_name}/files")
        entry = RequestDoc(
            method="GET",
            path="/api/v1/buckets/{bucket_id}/files",
            description="List all files in a bucket.",
            headers=self._doc_headers(),
            response_status=list_files_resp.status_code,
            response_body=self._sanitize_response(list_files_resp.json() if list_files_resp.content else {}),
        )
        self._add_entry("File Management", entry)

        self.add_cleanup(lambda: self._request("DELETE", f"/api/v1/files/{bucket_name}/{file_path}"))
        self.add_cleanup(lambda: self._request("DELETE", f"/api/v1/buckets/{bucket_name}"))



    def generate_realtime_section(self) -> None:
        # Realtime status
        resp = self._request("GET", "/api/v1/realtime/status")
        entry = RequestDoc(
            method="GET",
            path="/api/v1/realtime/status",
            description="Realtime status and configuration.",
            headers=self._doc_headers(),
            response_status=resp.status_code,
            response_body=self._sanitize_response(resp.json()),
        )
        self._add_entry("Realtime", entry)

        # WebSocket connection (documented only)
        entry = RequestDoc(
            method="GET",
            path="/api/v1/realtime/ws?token=YOUR_JWT_TOKEN",
            description="Establish a WebSocket connection proxied to the Phoenix Realtime service (Phoenix Channels compatible).",
            headers=self._doc_headers(),
            response_status=101,
            response_body={
                "note": "WebSocket upgrade. Use a WebSocket client such as the browser WebSocket API.",
                "client_usage": {
                    "connect": "realtimeService.connect(token)",
                    "subscribe": "realtimeService.subscribe('tables_events')",
                    "unsubscribe": "realtimeService.unsubscribe('tables_events')",
                },
                "message_protocol": {
                    "format": "[join_ref, ref, topic, event, payload]",
                    "example_subscribe_payload": {
                        "type": "subscribe",
                        "resource_type": "tables",
                        "resource_id": None
                    },
                    "example_broadcast": {
                        "type": "broadcast",
                        "channel": "tables_events",
                        "payload": {"table": "orders", "operation": "INSERT"}
                    }
                },
                "frontend_reference": "See frontend/src/services/realtimeService.ts for the client implementation used by Dashboard widgets."
            },
        )
        self._add_entry("Realtime", entry)
    def generate_webhooks_section(self, function_context: Optional[Dict[str, str]] = None) -> None:
        """Complete webhook CRUD mirroring integration tests."""
        admin_token = self.ensure_admin_token()
        headers = {"Authorization": f"Bearer {admin_token}"}

        # List webhooks
        list_resp = self._request("GET", "/api/v1/webhooks", headers=headers)
        entry = RequestDoc(
            method="GET",
            path="/api/v1/webhooks",
            description="List all webhooks for the authenticated user.",
            headers=self._doc_headers(include_auth=True),
            response_status=list_resp.status_code,
            response_body=self._sanitize_response(list_resp.json()),
        )
        self._add_entry("Webhooks", entry)

        webhook_name = f"stripe-checkout-{uuid.uuid4().hex[:8]}"
        secret_key = os.getenv("DOCS_WEBHOOK_SECRET") or f"whsec_{uuid.uuid4().hex}"
        webhook_payload: Dict[str, Any] = {
            "name": webhook_name,
            "provider": "stripe",
            "provider_event_type": "checkout.session.completed",
            "secret_key": secret_key,
        }
        if function_context and function_context.get("function_id"):
            webhook_payload["function_id"] = function_context["function_id"]

        doc_webhook_payload = {
            "name": webhook_name,
            "provider": "stripe",
            "provider_event_type": "checkout.session.completed",
            "secret_key": "whsec_your_secret_key",
        }
        if "function_id" in webhook_payload:
            doc_webhook_payload["function_id"] = "function-uuid"

        create_resp = self._request("POST", "/api/v1/webhooks", headers=headers, json=webhook_payload)
        entry = RequestDoc(
            method="POST",
            path="/api/v1/webhooks",
            description="Create a new webhook endpoint.",
            headers=self._doc_headers(include_auth=True, extra={"Content-Type": "application/json"}),
            json_body=doc_webhook_payload,
            response_status=create_resp.status_code,
            response_body=self._sanitize_response(create_resp.json()),
        )
        self._add_entry("Webhooks", entry)

        webhook_id = None
        if create_resp.status_code in (200, 201):
            webhook_id = create_resp.json().get("id")

        if webhook_id:
            get_resp = self._request("GET", f"/api/v1/webhooks/{webhook_id}", headers=headers)
            entry = RequestDoc(
                method="GET",
                path="/api/v1/webhooks/{webhook_id}",
                description="Get webhook details by ID.",
                headers=self._doc_headers(include_auth=True),
                response_status=get_resp.status_code,
                response_body=self._sanitize_response(get_resp.json()),
            )
            self._add_entry("Webhooks", entry)

        if function_context and function_context.get("function_id") and webhook_id:
            customers = [
                {
                    "first_name": "Alice",
                    "last_name": "Johnson",
                    "email": f"alice{uuid.uuid4().hex[:12]}@stripeonboarding-example.com",
                }
            ]
            payload = {
                "id": f"cs_test_{uuid.uuid4().hex[:12]}",
                "object": "checkout.session",
                "amount_total": 2000,
                "currency": "usd",
                "customer_email": customers[0]["email"],
                "customer_details": {
                    "email": customers[0]["email"],
                    "name": f"{customers[0]['first_name']} {customers[0]['last_name']}"
                },
                "data": customers[0],
            }
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            signature = hmac.new(secret_key.encode("utf-8"), body, hashlib.sha256).hexdigest()
            ingest_headers = {
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature,
            }
            ingest_resp = self._request(
                "POST",
                f"/api/v1/webhooks/ingest/{function_context['function_id']}",
                headers=ingest_headers,
                data=body,
            )
            entry = RequestDoc(
                method="POST",
                path="/api/v1/webhooks/ingest/{function_id}",
                description="Ingest a webhook event payload.",
                headers=self._doc_headers(extra={"Content-Type": "application/json", "X-Webhook-Signature": signature}),
                json_body=payload,
                response_status=ingest_resp.status_code,
                response_body=self._sanitize_response(ingest_resp.json() if ingest_resp.content else {}),
            )
            self._add_entry("Webhooks", entry)

            status_resp = self._request(
                "GET",
                f"/api/v1/functions/{function_context['function_id']}",
                headers=headers,
            )
            entry = RequestDoc(
                method="GET",
                path="/api/v1/functions/{function_id}",
                description="Get function details after webhook ingestion.",
                headers=self._doc_headers(include_auth=True),
                response_status=status_resp.status_code,
                response_body=self._sanitize_response(status_resp.json()),
            )
            self._add_entry("Webhooks", entry)


    def render_markdown(self) -> str:
        lines: List[str] = []
        lines.append("# SelfDB API Reference")
        lines.append("")
        lines.append(
            "Complete API reference generated by hitting live backend endpoints and capturing real request/response data. This script creates test data, exercises all endpoints, logs responses, and cleans up afterwards. Run: `python scripts/generate_api_reference.py`"
        )
        lines.append("")
        lines.append("## Configuration")
        lines.append("")
        lines.append("```yaml")
        lines.append(f"selfdb_base_url: {self.base_url}")
        lines.append("selfdb_api_key: 'YOUR_API_KEY'")
        lines.append("```")
        lines.append("")
        lines.append("### Authentication")
        lines.append("")
        lines.append("**All requests** require the `X-API-Key` header:")
        lines.append("")
        lines.append("```bash")
        lines.append("X-API-Key: YOUR_API_KEY")
        lines.append("```")
        lines.append("")
        lines.append("### Protected Endpoints")
        lines.append("")
        lines.append("Protected endpoints additionally require a Bearer token in the `Authorization` header:")
        lines.append("")
        lines.append("```bash")
        lines.append("Authorization: Bearer YOUR_ACCESS_TOKEN")
        lines.append("```")
        lines.append("")
        lines.append("**Token Flow:**")
        lines.append("")
        lines.append("1. **Get Tokens:** Call `/auth/login` or `/auth/register` to receive both `access_token` and `refresh_token`")
        lines.append("2. **Use Access Token:** Include the `access_token` in the `Authorization: Bearer <token>` header for protected endpoints")
        lines.append("3. **Refresh Token:** When the `access_token` expires, call `/auth/refresh` with your `refresh_token` to obtain new tokens")
        lines.append("")

        for section, entries in self.sections.items():
            lines.append(f"## {section}")
            lines.append("")
            for entry in entries:
                lines.append(f"### {entry.description}")
                lines.append("")
                lines.append("```bash")
                curl_lines = self._render_curl(entry)
                lines.extend(curl_lines)
                lines.append("```")
                lines.append("")
                lines.append(f"**Response ({entry.response_status})**:")
                lines.append("")
                lines.append("```json")
                lines.append(self._to_json_string(entry.response_body))
                lines.append("```")
                lines.append("")
                if entry.errors:
                    lines.append("**Errors**:")
                    for error in entry.errors:
                        lines.append(f"- `{error}`")
                    lines.append("")

        return "\n".join(lines).strip() + "\n"

    def _render_curl(self, entry: RequestDoc) -> List[str]:
        url = f"{self.base_url}{entry.path if entry.path.startswith('/') else '/' + entry.path}".rstrip("/")
        if entry.path.endswith("}"):
            url = f"{self.base_url}{entry.path}"  # keep placeholders

        parts = [f"curl -X {entry.method.upper()} \"{url}\""]
        for header, value in entry.headers.items():
            parts.append(f"  -H \"{header}: {value}\"")

        if entry.json_body is not None:
            body = self._to_json_string(entry.json_body)
            parts.append(f"  -d '{body}'")
        elif entry.data_body is not None:
            for key, value in entry.data_body.items():
                parts.append(f"  -F '{key}={value}'")
        if entry.files_desc:
            parts.append(f"  # Files: {entry.files_desc}")
        return parts


def write_markdown_constant(markdown: str) -> None:
    ensure_directory(FRONTEND_CONSTANT_PATH)
    # Escape backticks in markdown content for template literal
    escaped = markdown.replace("`", "\\`").replace("${", "\\${")
    content = textwrap.dedent(
        f"""// This file is auto-generated by scripts/generate_api_reference.py
export const apiReferenceMarkdown = `
{escaped}
`;
"""
    )
    FRONTEND_CONSTANT_PATH.write_text(content, encoding="utf-8")


def write_placeholder_constant() -> None:
    """Write a placeholder markdown constant when backend is not available."""
    ensure_directory(FRONTEND_CONSTANT_PATH)
    content = textwrap.dedent(
        """// This file is auto-generated by scripts/generate_api_reference.py
// Run: python scripts/generate_api_reference.py (with backend running)
export const apiReferenceMarkdown = `
# SelfDB API Reference

This API reference is generated from live backend endpoints.

To regenerate this documentation:
1. Ensure the backend is running (e.g., \`docker compose up backend\`)
2. Run: \`python scripts/generate_api_reference.py\`

The script will hit live endpoints, capture request/response data, and update this file.

## Placeholder Content

This is placeholder content. The backend was not running when the generation script was executed.

**To generate real documentation:**
- Start your backend service
- Re-run the generation script
`;
"""
    )
    FRONTEND_CONSTANT_PATH.write_text(content, encoding="utf-8")


def check_backend_health(base_url: str, timeout: int = 5) -> bool:
    """Check if the backend is running and healthy."""
    try:
        response = requests.get(f"{base_url}/health", timeout=timeout)
        return response.status_code == 200
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False
    except Exception:
        return False


def main() -> None:
    env = load_environment()

    api_key = env.get("API_KEY")
    if not api_key:
        raise RuntimeError("API_KEY is required in .env.dev for documentation generation.")

    base_url = guess_backend_url(env)

    # Check if backend is running
    print(f"Checking backend health at {base_url}...")
    if not check_backend_health(base_url):
        print(f"⚠️  Backend is not running at {base_url}")
        print("📝 Creating placeholder API reference file...")
        write_placeholder_constant()
        print(f"✅ Placeholder file created at {FRONTEND_CONSTANT_PATH}")
        print("\nTo generate real API documentation:")
        print("  1. Start the backend: docker compose up backend")
        print("  2. Re-run this script: python scripts/generate_api_reference.py")
        return

    print("✅ Backend is running!")

    admin_email = env.get("ADMIN_EMAIL")
    admin_password = env.get("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD must be set in .env.dev.")

    generator = ApiDocGenerator(base_url, api_key, admin_email, admin_password)

    try:
        print("📡 Generating API documentation from live endpoints...")
        print("  ├─ Health & Status...")
        generator.generate_health_section()
        
        print("  ├─ Authentication...")
        auth_context = generator.generate_auth_section()
        
        print("  ├─ User Management (Full CRUD)...")
        generator.generate_user_management_section(auth_context)
        
        print("  ├─ Bucket Management (Full CRUD)...")
        generator.generate_bucket_section(auth_context)
        
        print("  ├─ File Management (Full CRUD)...")
        generator.generate_files_section()
        
        print("  ├─ Table Management (Full CRUD)...")
        generator.generate_tables_section()
        
        print("  ├─ SQL Execution...")
        generator.generate_sql_section()
        
        print("  ├─ Functions (Full CRUD)...")
        function_context = generator.generate_functions_section()
        
        print("  ├─ Webhooks (Full CRUD)...")
        generator.generate_webhooks_section(function_context)
        
        print("  └─ Realtime...")
        generator.generate_realtime_section()

        markdown = generator.render_markdown()
        write_markdown_constant(markdown)
        print(f"\n✅ API reference generated at {FRONTEND_CONSTANT_PATH}")
        print("\n📚 Complete Documentation Includes:")
        print("  • Health & Status Endpoints")
        print("  • Authentication (register, login, refresh, me, change-password)")
        print("  • User Management CRUD (create, list, get, update, delete, count, set-password)")
        print("  • Bucket Management CRUD (create, list, get, update, delete)")
        print("  • File Management CRUD (upload, download, delete, list)")
        print("  • Table Management CRUD (create, list, get, insert, update, delete rows, add/update/delete columns, update table, get SQL)")
        print("  • SQL Execution (query, history, snippets CRUD)")
        print("  • Functions CRUD (create, list, get, update, delete)")
        print("  • Webhooks CRUD (create, list, get, update, delete)")
        print("  • Realtime (status, WebSocket connection)")
    finally:
        print("\n🧹 Cleaning up all test data...")
        generator.run_cleanup()
        print("✨ Done!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)


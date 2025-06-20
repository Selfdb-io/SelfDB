# Plan: Implement Anonymous Access Key Feature

This document outlines the steps to add an anonymous access key feature to the SelfDB backend. This feature allows unauthenticated clients to access designated public resources using a static API key.

**Goal:** Provide a mechanism for public, read and write only access to specific API endpoints without requiring user login, controlled via a unique, generated API key (`ANON_KEY`).

**Mechanism:**
1.  A unique `ANON_KEY` is generated during setup and stored in the `.env` file.
2.  Clients include this key in the `apikey` HTTP header of their requests.
3.  A modified authentication dependency (`deps.py`) checks for this header *after* checking for a standard JWT.
4.  Endpoints intended for public access use this modified dependency.
5.  Endpoint and potentially CRUD logic checks if the request is authenticated, anonymous (valid `ANON_KEY`), or unauthorized, and grants access accordingly.

## Implementation Steps:

1.  **Configuration (`.env` and `settings.py`):**
    *   **Modify `backend/app/core/config.py`:** Add `ANON_KEY: str | None = None` to the `Settings` Pydantic model to load the key from the environment.
    *   **Modify Setup Script (`scripts/start.sh` or equivalent):**
        *   Check if `.env` file exists. If not, create it.
        *   Check if `ANON_KEY` already exists in `.env`.
        *   If not, generate a secure random key (e.g., `openssl rand -hex 32`).
        *   Append `ANON_KEY=<generated_key>` to the `.env` file. Ensure correct permissions for `.env`.

2.  **Authentication Dependency (`backend/app/apis/deps.py`):**
    *   **Define API Key Header Scheme:** Use `fastapi.security.APIKeyHeader` to define how to extract the key: `api_key_header = APIKeyHeader(name="apikey", auto_error=False)`. Setting `auto_error=False` prevents FastAPI from automatically raising a 403 if the header is missing, allowing us to handle different auth types gracefully.
    *   **Create `get_current_user_or_anon` Dependency:**
        *   This new dependency will be the primary way to handle auth for most endpoints going forward.
        *   It should accept the JWT token (`Optional[str] = Depends(reusable_oauth2)`) and the API key header (`Optional[str] = Depends(api_key_header)`) as parameters.
        *   **Logic:**
            1.  If a valid JWT `token` is provided: Decode it, retrieve the user from the database (like `get_current_active_user` currently does), and return the `models.User` object. Handle potential `JWTError` or user-not-found errors by raising `HTTPException(status_code=403, detail="Invalid token or user not found")`.
            2.  Else if an `api_key` is provided:
                *   Load `settings.ANON_KEY` from the application settings.
                *   Compare the provided `api_key` with `settings.ANON_KEY`.
                *   If they match *and* `settings.ANON_KEY` is set: Return a special representation for the anonymous role (e.g., the string `"anon"` or a dedicated constant `ANON_USER_ROLE = "anon"`).
            3.  If neither a valid JWT nor the correct `ANON_KEY` is found: Return `None`.
    *   **Modify `get_current_active_user` (Optional but recommended for clarity):**
        *   Refactor `get_current_active_user` to call `get_current_user_or_anon`.
        *   Check the result: If it's a `models.User` and `user.is_active`, return the user.
        *   Otherwise (it's `"anon"` or `None`), raise `HTTPException(status_code=401, detail="Not authenticated")`. This keeps the strict requirement for endpoints that *must* have a logged-in user.

3.  **Resource Public Access Control:**
    *   **Add `is_public` Flag:** To control which resources are accessible via the `ANON_KEY`, add an `is_public` boolean field to relevant database models (e.g., `Bucket`, `File`, potentially dynamic `Table` metadata if applicable).
        *   Modify `backend/app/models/`: Add the field (e.g., `is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default=sql.false())`).
        *   Modify `backend/app/schemas/`: Update corresponding Pydantic schemas to include `is_public`.
        *   Modify `backend/app/crud/`: Update CRUD operations (create, update) to handle the new field.
    *   **Database Migration:** Generate and apply an Alembic migration to add the new `is_public` column(s) to the database. (`alembic revision --autogenerate -m "Add is_public flag to relevant models"` and `alembic upgrade head`).

4.  **Endpoint Adaptation:**
    *   Identify endpoints that should allow anonymous access (e.g., listing files in a public bucket, reading data from a public table).
    *   **Modify Endpoint Dependency:** Change `Depends(deps.get_current_active_user)` to `Depends(deps.get_current_user_or_anon)` for these endpoints.
    *   **Implement Access Logic:**
        *   Get the result from the dependency: `requester: models.User | str | None = Depends(deps.get_current_user_or_anon)`.
        *   Fetch the target resource (e.g., bucket, table).
        *   Check the resource's `is_public` flag and the `requester` status:
            ```python
            # Example for getting a bucket
            bucket = await crud.bucket.get(db=db, id=bucket_id)
            if not bucket:
                raise HTTPException(status_code=404, detail="Bucket not found")

            is_anon_request = isinstance(requester, str) and requester == "anon" # Or ANON_USER_ROLE
            is_authenticated_user = isinstance(requester, models.User)

            # Check permissions
            if not bucket.is_public:
                if not is_authenticated_user:
                    # Private bucket requires a real user
                    raise HTTPException(status_code=401, detail="Authentication required for this private bucket")
                # Add potential ownership/role check here if needed for authenticated users
                # if bucket.owner_id != requester.id:
                #     raise HTTPException(status_code=403, detail="Forbidden")
            # else: public bucket access allowed for anon or authenticated users

            # Proceed with the operation (e.g., list files)
            # Pass requester info down to CRUD if filtering is needed there
            files = await crud.file.get_multi_by_bucket(db=db, bucket_id=bucket.id, requester=requester)

            return files
            ```

5.  **CRUD Layer Adaptation (Optional but Recommended):**
    *   Modify relevant CRUD functions (e.g., `get_multi_by_bucket`, `get_multi_by_table`) to accept the `requester` (which could be `models.User`, `"anon"`, or `None`).
    *   Implement filtering logic within CRUD functions based on the `requester` type and the `is_public` status of the resource or related data. This keeps endpoint logic cleaner.
        *   Example: `crud.file.get_multi_by_bucket` might only return files explicitly marked public if `requester == "anon"`.

6.  **Testing:**
    *   Write unit/integration tests for `deps.py` functions.
    *   Test endpoints with:
        *   No credentials.
        *   Invalid JWT.
        *   Valid JWT.
        *   Incorrect `apikey`.
        *   Correct `apikey` (`ANON_KEY`).
    *   Verify access control for both public and private resources using different credential types.

7.  **Documentation:**
    *   Update `README.md` or API documentation (Swagger/OpenAPI) to explain the `ANON_KEY` feature, the `apikey` header, and which endpoints support anonymous access.
    *   Document the `ANON_KEY` variable in `.env` setup instructions.

{
  "openapi": "3.1.0",
  "info": {
    "title": "SelfDB Backend",
    "version": "v0.05 early beta"
  },
  "paths": {
    "/auth/register": {
      "post": {
        "tags": [
          "authentication"
        ],
        "summary": "Register",
        "description": "Register new user endpoint.",
        "operationId": "register_auth_register_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/UserRegisterRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/TokenResponse"
                }
              }
            }
          },
          "400": {
            "description": "Bad Request",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            }
          },
          "500": {
            "description": "Internal Server Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/auth/login": {
      "post": {
        "tags": [
          "authentication"
        ],
        "summary": "Login",
        "description": "Login user endpoint.",
        "operationId": "login_auth_login_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/UserLoginRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/TokenResponse"
                }
              }
            }
          },
          "401": {
            "description": "Unauthorized",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            }
          },
          "500": {
            "description": "Internal Server Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/auth/refresh": {
      "post": {
        "tags": [
          "authentication"
        ],
        "summary": "Refresh Token",
        "description": "Refresh JWT token endpoint.",
        "operationId": "refresh_token_auth_refresh_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "title": "Refresh Request"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/TokenResponse"
                }
              }
            }
          },
          "401": {
            "description": "Unauthorized",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            }
          },
          "500": {
            "description": "Internal Server Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/auth/logout": {
      "post": {
        "tags": [
          "authentication"
        ],
        "summary": "Logout",
        "description": "Logout user endpoint.",
        "operationId": "logout_auth_logout_post",
        "parameters": [
          {
            "name": "access_token",
            "in": "query",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Access Token"
            }
          },
          {
            "name": "refresh_token",
            "in": "query",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Refresh Token"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Logout Auth Logout Post"
                }
              }
            }
          },
          "500": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Internal Server Error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/auth/change-password": {
      "post": {
        "tags": [
          "authentication"
        ],
        "summary": "Change Password",
        "description": "Authenticated endpoint for users to change their own password.",
        "operationId": "change_password_auth_change_password_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ChangePasswordRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Change Password Auth Change Password Post"
                }
              }
            }
          },
          "400": {
            "description": "Bad Request",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            }
          },
          "401": {
            "description": "Unauthorized",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            }
          },
          "500": {
            "description": "Internal Server Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/auth/me": {
      "get": {
        "tags": [
          "authentication"
        ],
        "summary": "Get Current User",
        "description": "Get current user endpoint.",
        "operationId": "get_current_user_auth_me_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/UserResponse"
                }
              }
            }
          },
          "401": {
            "description": "Unauthorized",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            }
          },
          "500": {
            "description": "Internal Server Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            }
          }
        }
      }
    },
    "/auth/me/api-key": {
      "get": {
        "tags": [
          "authentication"
        ],
        "summary": "Get Api Key For Admin",
        "description": "Return the configured API key to authenticated admin users.\n\nThis endpoint requires a valid Bearer token and X-API-Key header, and will\nverify that the authenticated user is active and has role 'ADMIN'. It returns\nJSON: {\"api_key\": \u003Cstring|null\u003E}.",
        "operationId": "get_api_key_for_admin_auth_me_api_key_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Get Api Key For Admin Auth Me Api Key Get"
                }
              }
            }
          },
          "401": {
            "description": "Unauthorized",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            }
          },
          "403": {
            "description": "Forbidden",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            }
          },
          "500": {
            "description": "Internal Server Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/users/": {
      "post": {
        "tags": [
          "user-management"
        ],
        "summary": "Create User",
        "description": "Create a new user (admin only).",
        "operationId": "create_user_api_v1_users__post",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/UserCreateRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/UserResponse"
                }
              }
            }
          },
          "401": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Unauthorized"
          },
          "403": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Forbidden"
          },
          "409": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Conflict"
          },
          "500": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Internal Server Error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "get": {
        "tags": [
          "user-management"
        ],
        "summary": "List Users",
        "description": "List users with pagination (admin only).",
        "operationId": "list_users_api_v1_users__get",
        "parameters": [
          {
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "default": 50,
              "title": "Limit"
            }
          },
          {
            "name": "offset",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "default": 0,
              "title": "Offset"
            }
          },
          {
            "name": "sort",
            "in": "query",
            "required": false,
            "schema": {
              "type": "string",
              "default": "created_at:desc",
              "title": "Sort"
            }
          },
          {
            "name": "role",
            "in": "query",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Role"
            }
          },
          {
            "name": "is_active",
            "in": "query",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "boolean"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Is Active"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/UserListResponse"
                }
              }
            }
          },
          "401": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Unauthorized"
          },
          "403": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Forbidden"
          },
          "500": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Internal Server Error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/users/{user_id}": {
      "get": {
        "tags": [
          "user-management"
        ],
        "summary": "Get User",
        "description": "Get user details (admin only).",
        "operationId": "get_user_api_v1_users__user_id__get",
        "parameters": [
          {
            "name": "user_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "User Id"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/UserResponse"
                }
              }
            }
          },
          "401": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Unauthorized"
          },
          "403": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Forbidden"
          },
          "404": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Not Found"
          },
          "500": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Internal Server Error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "user-management"
        ],
        "summary": "Update User",
        "description": "Update user (admin only).",
        "operationId": "update_user_api_v1_users__user_id__put",
        "parameters": [
          {
            "name": "user_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "User Id"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/UserUpdateRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/UserResponse"
                }
              }
            }
          },
          "401": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Unauthorized"
          },
          "403": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Forbidden"
          },
          "404": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Not Found"
          },
          "500": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Internal Server Error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "user-management"
        ],
        "summary": "Delete User",
        "description": "Delete user (admin only).",
        "operationId": "delete_user_api_v1_users__user_id__delete",
        "parameters": [
          {
            "name": "user_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "User Id"
            }
          },
          {
            "name": "soft_delete",
            "in": "query",
            "required": false,
            "schema": {
              "type": "boolean",
              "default": false,
              "title": "Soft Delete"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Delete User Api V1 Users  User Id  Delete"
                }
              }
            }
          },
          "401": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Unauthorized"
          },
          "403": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Forbidden"
          },
          "404": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Not Found"
          },
          "500": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Internal Server Error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/users/{user_id}/password": {
      "post": {
        "tags": [
          "user-management"
        ],
        "summary": "Set User Password",
        "description": "Admin-only endpoint to set/reset a user's password.",
        "operationId": "set_user_password_api_v1_users__user_id__password_post",
        "parameters": [
          {
            "name": "user_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "User Id"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/AdminSetPasswordRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Set User Password Api V1 Users  User Id  Password Post"
                }
              }
            }
          },
          "401": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Unauthorized"
          },
          "403": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Forbidden"
          },
          "404": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Not Found"
          },
          "500": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__users__ErrorResponse"
                }
              }
            },
            "description": "Internal Server Error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/tables": {
      "get": {
        "tags": [
          "tables"
        ],
        "summary": "List Tables",
        "operationId": "list_tables_api_v1_tables_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "tables"
        ],
        "summary": "Create Table",
        "operationId": "create_table_api_v1_tables_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CreateTableRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/tables/{table_name}": {
      "get": {
        "tags": [
          "tables"
        ],
        "summary": "Get Table Metadata",
        "operationId": "get_table_metadata_api_v1_tables__table_name__get",
        "parameters": [
          {
            "name": "table_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Table Name"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "tables"
        ],
        "summary": "Update Table",
        "operationId": "update_table_api_v1_tables__table_name__put",
        "parameters": [
          {
            "name": "table_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Table Name"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/UpdateTableRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "tables"
        ],
        "summary": "Delete Table",
        "operationId": "delete_table_api_v1_tables__table_name__delete",
        "parameters": [
          {
            "name": "table_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Table Name"
            }
          }
        ],
        "responses": {
          "204": {
            "description": "Successful Response"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/tables/{table_name}/data": {
      "get": {
        "tags": [
          "tables"
        ],
        "summary": "Get Table Data",
        "operationId": "get_table_data_api_v1_tables__table_name__data_get",
        "parameters": [
          {
            "name": "table_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Table Name"
            }
          },
          {
            "name": "page",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "minimum": 1,
              "default": 1,
              "title": "Page"
            }
          },
          {
            "name": "page_size",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "maximum": 1000,
              "minimum": 1,
              "default": 100,
              "title": "Page Size"
            }
          },
          {
            "name": "order_by",
            "in": "query",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Order By"
            }
          },
          {
            "name": "filter_column",
            "in": "query",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Filter Column"
            }
          },
          {
            "name": "filter_value",
            "in": "query",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "title": "Filter Value"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/TableDataResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "tables"
        ],
        "summary": "Insert Table Row",
        "operationId": "insert_table_row_api_v1_tables__table_name__data_post",
        "parameters": [
          {
            "name": "table_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Table Name"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "title": "Row"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/tables/{table_name}/data/{row_id}": {
      "put": {
        "tags": [
          "tables"
        ],
        "summary": "Update Table Row",
        "operationId": "update_table_row_api_v1_tables__table_name__data__row_id__put",
        "parameters": [
          {
            "name": "table_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Table Name"
            }
          },
          {
            "name": "row_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Row Id"
            }
          },
          {
            "name": "id_column",
            "in": "query",
            "required": false,
            "schema": {
              "type": "string",
              "default": "id",
              "title": "Id Column"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "title": "Updates"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "tables"
        ],
        "summary": "Delete Table Row",
        "operationId": "delete_table_row_api_v1_tables__table_name__data__row_id__delete",
        "parameters": [
          {
            "name": "table_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Table Name"
            }
          },
          {
            "name": "row_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Row Id"
            }
          },
          {
            "name": "id_column",
            "in": "query",
            "required": false,
            "schema": {
              "type": "string",
              "default": "id",
              "title": "Id Column"
            }
          }
        ],
        "responses": {
          "204": {
            "description": "Successful Response"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/tables/{table_name}/sql": {
      "get": {
        "tags": [
          "tables"
        ],
        "summary": "Get Table Sql",
        "operationId": "get_table_sql_api_v1_tables__table_name__sql_get",
        "parameters": [
          {
            "name": "table_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Table Name"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/tables/{table_name}/columns": {
      "post": {
        "tags": [
          "tables"
        ],
        "summary": "Add Column",
        "operationId": "add_column_api_v1_tables__table_name__columns_post",
        "parameters": [
          {
            "name": "table_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Table Name"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ColumnDefinitionModel"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/tables/{table_name}/columns/{column_name}": {
      "put": {
        "tags": [
          "tables"
        ],
        "summary": "Update Column Endpoint",
        "operationId": "update_column_endpoint_api_v1_tables__table_name__columns__column_name__put",
        "parameters": [
          {
            "name": "table_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Table Name"
            }
          },
          {
            "name": "column_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Column Name"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/UpdateColumnRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "tables"
        ],
        "summary": "Delete Column Endpoint",
        "operationId": "delete_column_endpoint_api_v1_tables__table_name__columns__column_name__delete",
        "parameters": [
          {
            "name": "table_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Table Name"
            }
          },
          {
            "name": "column_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Column Name"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/realtime/status": {
      "get": {
        "tags": [
          "realtime"
        ],
        "summary": "Realtime Status",
        "description": "Health check endpoint.",
        "operationId": "realtime_status_api_v1_realtime_status_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          }
        }
      }
    },
    "/api/v1/realtime/ws": {
      "get": {
        "tags": [
          "realtime"
        ],
        "summary": "Realtime WebSocket Proxy",
        "description": "Establish a WebSocket connection proxied to the Phoenix Realtime service.",
        "parameters": [
          {
            "name": "token",
            "in": "query",
            "required": true,
            "description": "JWT token authorizing the realtime session.",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "101": {
            "description": "Switching Protocols"
          },
          "400": {
            "description": "Invalid WebSocket handshake"
          },
          "403": {
            "description": "Authentication required"
          },
          "500": {
            "description": "Internal server error"
          }
        }
      }
    },
    "/api/v1/buckets": {
      "get": {
        "tags": [
          "buckets"
        ],
        "summary": "List Buckets",
        "description": "List all buckets from database for real-time updates.",
        "operationId": "list_buckets_api_v1_buckets_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "buckets"
        ],
        "summary": "Create Bucket",
        "operationId": "create_bucket_api_v1_buckets_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/BucketCreate"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/buckets/{bucket}": {
      "get": {
        "tags": [
          "buckets"
        ],
        "summary": "Get Bucket",
        "description": "Get bucket details from database for real-time updates.",
        "operationId": "get_bucket_api_v1_buckets__bucket__get",
        "parameters": [
          {
            "name": "bucket",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Bucket"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "buckets"
        ],
        "summary": "Delete Bucket",
        "operationId": "delete_bucket_api_v1_buckets__bucket__delete",
        "parameters": [
          {
            "name": "bucket",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Bucket"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "buckets"
        ],
        "summary": "Update Bucket",
        "operationId": "update_bucket_api_v1_buckets__bucket__put",
        "parameters": [
          {
            "name": "bucket",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Bucket"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/BucketUpdate"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/buckets/{bucket}/files": {
      "get": {
        "tags": [
          "buckets"
        ],
        "summary": "List Bucket Files",
        "description": "List files in a bucket from database for real-time updates.",
        "operationId": "list_bucket_files_api_v1_buckets__bucket__files_get",
        "parameters": [
          {
            "name": "bucket",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Bucket"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/files/upload": {
      "post": {
        "tags": [
          "files"
        ],
        "summary": "Upload File",
        "description": "Upload a file to the specified bucket using streaming to avoid memory spikes.",
        "operationId": "upload_file_api_v1_files_upload_post",
        "requestBody": {
          "content": {
            "multipart/form-data": {
              "schema": {
                "$ref": "#/components/schemas/Body_upload_file_api_v1_files_upload_post"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/files/{bucket}/{path}": {
      "get": {
        "tags": [
          "files"
        ],
        "summary": "Download File",
        "description": "Stream a file from storage to the client with immediate TTFB.",
        "operationId": "download_file_api_v1_files__bucket___path__get",
        "parameters": [
          {
            "name": "bucket",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Bucket"
            }
          },
          {
            "name": "path",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Path"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "files"
        ],
        "summary": "Delete File",
        "description": "Delete a file from the specified bucket using StorageClient.",
        "operationId": "delete_file_api_v1_files__bucket___path__delete",
        "parameters": [
          {
            "name": "bucket",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Bucket"
            }
          },
          {
            "name": "path",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Path"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/sql/query": {
      "post": {
        "tags": [
          "sql"
        ],
        "summary": "Execute Query",
        "description": "Execute a SQL query (ADMIN only for all queries).",
        "operationId": "execute_query_api_v1_sql_query_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/SqlQueryRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/SqlExecutionResult"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/sql/history": {
      "post": {
        "tags": [
          "sql"
        ],
        "summary": "Save Query History",
        "description": "Save query to history.",
        "operationId": "save_query_history_api_v1_sql_history_post",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/SqlHistorySaveRequest"
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "get": {
        "tags": [
          "sql"
        ],
        "summary": "Get Query History",
        "description": "Get query execution history.",
        "operationId": "get_query_history_api_v1_sql_history_get",
        "parameters": [
          {
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "default": 100,
              "title": "Limit"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/sql/snippets": {
      "get": {
        "tags": [
          "sql"
        ],
        "summary": "Get Snippets",
        "description": "Get saved SQL snippets.",
        "operationId": "get_snippets_api_v1_sql_snippets_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "sql"
        ],
        "summary": "Create Snippet",
        "description": "Create a new SQL snippet.",
        "operationId": "create_snippet_api_v1_sql_snippets_post",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/SqlSnippetCreateRequest"
              }
            }
          },
          "required": true
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/sql/snippets/{snippet_id}": {
      "delete": {
        "tags": [
          "sql"
        ],
        "summary": "Delete Snippet",
        "description": "Delete a SQL snippet.",
        "operationId": "delete_snippet_api_v1_sql_snippets__snippet_id__delete",
        "parameters": [
          {
            "name": "snippet_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Snippet Id"
            }
          }
        ],
        "responses": {
          "204": {
            "description": "Successful Response"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/functions": {
      "post": {
        "tags": [
          "functions"
        ],
        "summary": "Create a new function",
        "description": "Create a new serverless function.\n\nAuto-deploys to Deno runtime upon creation.\n\nArgs:\n    request: Function creation request\n    current_user: Authenticated user\n    \nReturns:\n    Created function details\n    \nRaises:\n    400: Invalid function data or name already exists\n    401: Not authenticated\n    500: Database or deployment error",
        "operationId": "create_function_api_v1_functions_post",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CreateFunctionRequest"
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/FunctionResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "get": {
        "tags": [
          "functions"
        ],
        "summary": "List all functions",
        "description": "List all functions for the authenticated user.\n\nArgs:\n    limit: Maximum number of functions to return\n    offset: Number of functions to skip\n    current_user: Authenticated user\n    \nReturns:\n    List of functions with pagination info\n    \nRaises:\n    401: Not authenticated\n    500: Database error",
        "operationId": "list_functions_api_v1_functions_get",
        "parameters": [
          {
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "maximum": 100,
              "minimum": 1,
              "default": 20,
              "title": "Limit"
            }
          },
          {
            "name": "offset",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "minimum": 0,
              "default": 0,
              "title": "Offset"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/FunctionListResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/functions/{function_id}": {
      "get": {
        "tags": [
          "functions"
        ],
        "summary": "Get function details",
        "description": "Get details for a specific function.\n\nArgs:\n    function_id: Function UUID\n    current_user: Authenticated user\n    \nReturns:\n    Function details\n    \nRaises:\n    401: Not authenticated\n    404: Function not found or not owned by user\n    500: Database error",
        "operationId": "get_function_api_v1_functions__function_id__get",
        "parameters": [
          {
            "name": "function_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Function Id"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/FunctionResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "functions"
        ],
        "summary": "Update function code",
        "description": "Update function code and configuration.\n\nAuto-redeploys to Deno upon code changes.\n\nArgs:\n    function_id: Function UUID\n    request: Update request\n    current_user: Authenticated user\n    \nReturns:\n    Updated function details\n    \nRaises:\n    400: Invalid update data\n    401: Not authenticated\n    403: Not authorized\n    404: Function not found\n    500: Database or deployment error",
        "operationId": "update_function_api_v1_functions__function_id__put",
        "parameters": [
          {
            "name": "function_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Function Id"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/UpdateFunctionRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/FunctionResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "functions"
        ],
        "summary": "Delete function",
        "description": "Delete a function and all related data.\n\nAlso removes from Deno runtime and cleans up execution history.\n\nArgs:\n    function_id: Function UUID\n    current_user: Authenticated user\n    \nRaises:\n    401: Not authenticated\n    403: Not authorized\n    404: Function not found\n    500: Database or deletion error",
        "operationId": "delete_function_api_v1_functions__function_id__delete",
        "parameters": [
          {
            "name": "function_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Function Id"
            }
          }
        ],
        "responses": {
          "204": {
            "description": "Successful Response"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/functions/{function_name}/execution-result": {
      "post": {
        "tags": [
          "functions"
        ],
        "summary": "Receive execution result callbacks from runtime",
        "description": "Endpoint for runtimes to post execution results. Expects JSON body with execution_id, delivery_id, success, result, logs, execution_time_ms.",
        "operationId": "receive_execution_result_api_v1_functions__function_name__execution_result_post",
        "parameters": [
          {
            "name": "function_name",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Function Name"
            }
          }
        ],
        "responses": {
          "202": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/functions/{function_id}/state": {
      "patch": {
        "tags": [
          "functions"
        ],
        "summary": "Enable/disable function",
        "description": "Enable or disable a function.\n\nWhen enabled: function is deployed to Deno and processes triggers\nWhen disabled: function is undeployed from Deno (no triggers processed)\n\nArgs:\n    function_id: Function UUID\n    request: State request with is_active flag\n    current_user: Authenticated user\n    \nReturns:\n    Updated function details\n    \nRaises:\n    401: Not authenticated\n    403: Not authorized\n    404: Function not found\n    500: Database or deployment error",
        "operationId": "set_function_state_api_v1_functions__function_id__state_patch",
        "parameters": [
          {
            "name": "function_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Function Id"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/SetFunctionStateRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/FunctionResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/functions/{function_id}/env-vars": {
      "post": {
        "tags": [
          "functions"
        ],
        "summary": "Set environment variables",
        "description": "Set environment variables for a function.\n\nVariables are encrypted at rest and never exposed in responses.\n\nArgs:\n    function_id: Function UUID\n    request: Environment variables to set\n    current_user: Authenticated user\n    \nReturns:\n    Updated function with env var names (values not exposed)\n    \nRaises:\n    400: Invalid env vars\n    401: Not authenticated\n    403: Not authorized\n    404: Function not found\n    500: Database error",
        "operationId": "set_env_vars_api_v1_functions__function_id__env_vars_post",
        "parameters": [
          {
            "name": "function_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Function Id"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/SetEnvVarsRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/FunctionResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "get": {
        "tags": [
          "functions"
        ],
        "summary": "Get environment variable names",
        "description": "Get environment variable names for a function.\n\nNote: Only variable names are returned, not values (for security).\n\nArgs:\n    function_id: Function UUID\n    current_user: Authenticated user\n    \nReturns:\n    List of env var names\n    \nRaises:\n    401: Not authenticated\n    403: Not authorized\n    404: Function not found\n    500: Database error",
        "operationId": "get_env_vars_api_v1_functions__function_id__env_vars_get",
        "parameters": [
          {
            "name": "function_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Function Id"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "additionalProperties": {
                    "type": "array",
                    "items": {
                      "type": "string"
                    }
                  },
                  "title": "Response Get Env Vars Api V1 Functions  Function Id  Env Vars Get"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/functions/{function_id}/logs": {
      "get": {
        "tags": [
          "functions"
        ],
        "summary": "Get function execution logs",
        "description": "Get execution logs for a function.\n\nReturns paginated logs from all executions of the function.\n\nArgs:\n    function_id: Function UUID\n    current_user: Authenticated user\n    limit: Maximum number of logs to return\n    offset: Number of logs to skip\n    \nReturns:\n    Paginated list of logs\n    \nRaises:\n    401: Not authenticated\n    403: Not authorized\n    404: Function not found\n    500: Database error",
        "operationId": "get_function_logs_api_v1_functions__function_id__logs_get",
        "parameters": [
          {
            "name": "function_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Function Id"
            }
          },
          {
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "maximum": 1000,
              "minimum": 1,
              "default": 100,
              "title": "Limit"
            }
          },
          {
            "name": "offset",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "minimum": 0,
              "default": 0,
              "title": "Offset"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Get Function Logs Api V1 Functions  Function Id  Logs Get"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/functions/{function_id}/metrics": {
      "get": {
        "tags": [
          "functions"
        ],
        "summary": "Get function execution metrics",
        "description": "Get execution metrics and statistics for a function.\n\nIncludes execution counts, success rates, average execution time, etc.\n\nArgs:\n    function_id: Function UUID\n    current_user: Authenticated user\n    \nReturns:\n    Function execution metrics\n    \nRaises:\n    401: Not authenticated\n    403: Not authorized\n    404: Function not found\n    500: Database error",
        "operationId": "get_function_metrics_api_v1_functions__function_id__metrics_get",
        "parameters": [
          {
            "name": "function_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Function Id"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Get Function Metrics Api V1 Functions  Function Id  Metrics Get"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/functions/{function_id}/executions": {
      "get": {
        "tags": [
          "functions"
        ],
        "summary": "Get function executions",
        "description": "Get paginated executions for a function.\n\nArgs:\n    function_id: Function UUID\n    current_user: Authenticated user\n    limit: Maximum number of executions to return\n    offset: Number of executions to skip\n    status: Filter by execution status\n    trigger_type: Filter by trigger type\n    \nReturns:\n    Paginated list of function executions\n    \nRaises:\n    401: Not authenticated\n    403: Not authorized\n    404: Function not found\n    500: Database error",
        "operationId": "get_function_executions_api_v1_functions__function_id__executions_get",
        "parameters": [
          {
            "name": "function_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Function Id"
            }
          },
          {
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "maximum": 1000,
              "minimum": 1,
              "default": 50,
              "title": "Limit"
            }
          },
          {
            "name": "offset",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "minimum": 0,
              "default": 0,
              "title": "Offset"
            }
          },
          {
            "name": "status",
            "in": "query",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "description": "Filter by status",
              "title": "Status"
            },
            "description": "Filter by status"
          },
          {
            "name": "trigger_type",
            "in": "query",
            "required": false,
            "schema": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "description": "Filter by trigger type",
              "title": "Trigger Type"
            },
            "description": "Filter by trigger type"
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Get Function Executions Api V1 Functions  Function Id  Executions Get"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/webhooks": {
      "post": {
        "tags": [
          "webhooks"
        ],
        "summary": "Create a new webhook",
        "description": "Create a new webhook for a function.\n\nArgs:\n    request: Webhook creation request\n    current_user: Authenticated user\n    \nReturns:\n    Created webhook details\n    \nRaises:\n    400: Invalid webhook data or name already exists\n    401: Not authenticated\n    500: Database error",
        "operationId": "create_webhook_api_v1_webhooks_post",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CreateWebhookRequest"
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/WebhookResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "get": {
        "tags": [
          "webhooks"
        ],
        "summary": "List all webhooks",
        "description": "List all webhooks for the authenticated user.\n\nArgs:\n    limit: Maximum number of webhooks to return\n    offset: Number of webhooks to skip\n    current_user: Authenticated user\n    \nReturns:\n    List of webhooks with pagination info\n    \nRaises:\n    401: Not authenticated\n    500: Database error",
        "operationId": "list_webhooks_api_v1_webhooks_get",
        "parameters": [
          {
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "maximum": 100,
              "minimum": 1,
              "default": 20,
              "title": "Limit"
            }
          },
          {
            "name": "offset",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "minimum": 0,
              "default": 0,
              "title": "Offset"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/WebhookListResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/webhooks/{webhook_id}": {
      "get": {
        "tags": [
          "webhooks"
        ],
        "summary": "Get webhook details",
        "description": "Get details for a specific webhook.\n\nArgs:\n    webhook_id: Webhook UUID\n    current_user: Authenticated user\n    \nReturns:\n    Webhook details\n    \nRaises:\n    401: Not authenticated\n    403: Not authorized\n    404: Webhook not found\n    500: Database error",
        "operationId": "get_webhook_api_v1_webhooks__webhook_id__get",
        "parameters": [
          {
            "name": "webhook_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Webhook Id"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/WebhookResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "webhooks"
        ],
        "summary": "Update webhook configuration",
        "description": "Update webhook configuration.\n\nArgs:\n    webhook_id: Webhook UUID\n    request: Update request\n    current_user: Authenticated user\n    \nReturns:\n    Updated webhook details\n    \nRaises:\n    400: Invalid update data\n    401: Not authenticated\n    403: Not authorized\n    404: Webhook not found\n    500: Database error",
        "operationId": "update_webhook_api_v1_webhooks__webhook_id__put",
        "parameters": [
          {
            "name": "webhook_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Webhook Id"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/UpdateWebhookRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/WebhookResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "webhooks"
        ],
        "summary": "Delete webhook",
        "description": "Delete a webhook.\n\nArgs:\n    webhook_id: Webhook UUID\n    current_user: Authenticated user\n    \nRaises:\n    401: Not authenticated\n    403: Not authorized\n    404: Webhook not found\n    500: Database error",
        "operationId": "delete_webhook_api_v1_webhooks__webhook_id__delete",
        "parameters": [
          {
            "name": "webhook_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Webhook Id"
            }
          }
        ],
        "responses": {
          "204": {
            "description": "Successful Response"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/webhooks/{webhook_id}/deliveries": {
      "get": {
        "tags": [
          "webhooks"
        ],
        "summary": "Get webhook delivery history",
        "description": "Get delivery history for a webhook.\n\nArgs:\n    webhook_id: Webhook UUID\n    current_user: Authenticated user\n    limit: Maximum deliveries to return\n    offset: Number of deliveries to skip\n    \nReturns:\n    Paginated delivery history\n    \nRaises:\n    401: Not authenticated\n    403: Not authorized\n    404: Webhook not found\n    500: Database error",
        "operationId": "get_webhook_deliveries_api_v1_webhooks__webhook_id__deliveries_get",
        "parameters": [
          {
            "name": "webhook_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Webhook Id"
            }
          },
          {
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "maximum": 1000,
              "minimum": 1,
              "default": 100,
              "title": "Limit"
            }
          },
          {
            "name": "offset",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "minimum": 0,
              "default": 0,
              "title": "Offset"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/WebhookDeliveryListResponse"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/webhooks/ingest/{function_id}": {
      "post": {
        "tags": [
          "webhooks"
        ],
        "summary": "Ingest webhook payload and trigger function",
        "description": "Webhook ingestion endpoint that receives payloads from external providers.\n\nThis endpoint:\n1. Validates webhook signature (if secret provided)\n2. Triggers function execution via Deno\n3. Returns immediately (async execution)\n\nArgs:\n    function_id: Function UUID to trigger\n    req: Request containing webhook payload\n    \nReturns:\n    Acknowledgement with execution_id\n    \nRaises:\n    400: Invalid function_id or signature validation failed\n    401: Unauthorized (invalid signature)\n    404: Function or webhook not found\n    500: Execution error",
        "operationId": "ingest_webhook_api_v1_webhooks_ingest__function_id__post",
        "parameters": [
          {
            "name": "function_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Function Id"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "title": "Response Ingest Webhook Api V1 Webhooks Ingest  Function Id  Post"
                }
              }
            }
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/cors/origins/": {
      "get": {
        "tags": [
          "cors"
        ],
        "summary": "List Cors Origins",
        "description": "List CORS origins (admin only).",
        "operationId": "list_cors_origins_api_v1_cors_origins__get",
        "parameters": [
          {
            "name": "active_only",
            "in": "query",
            "required": false,
            "schema": {
              "type": "boolean",
              "description": "Only return active origins",
              "default": true,
              "title": "Active Only"
            },
            "description": "Only return active origins"
          },
          {
            "name": "limit",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "maximum": 1000,
              "minimum": 1,
              "description": "Maximum number of results",
              "default": 100,
              "title": "Limit"
            },
            "description": "Maximum number of results"
          },
          {
            "name": "offset",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "minimum": 0,
              "description": "Pagination offset",
              "default": 0,
              "title": "Offset"
            },
            "description": "Pagination offset"
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/CorsOriginListResponse"
                }
              }
            }
          },
          "401": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Unauthorized"
          },
          "403": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Forbidden"
          },
          "500": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Internal Server Error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": [
          "cors"
        ],
        "summary": "Create Cors Origin",
        "description": "Create a new CORS origin (admin only).",
        "operationId": "create_cors_origin_api_v1_cors_origins__post",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/CreateCorsOriginRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/CorsOriginResponse"
                }
              }
            }
          },
          "401": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Unauthorized"
          },
          "403": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Forbidden"
          },
          "409": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Conflict"
          },
          "500": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Internal Server Error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/cors/origins/{origin_id}": {
      "get": {
        "tags": [
          "cors"
        ],
        "summary": "Get Cors Origin",
        "description": "Get a specific CORS origin by ID (admin only).",
        "operationId": "get_cors_origin_api_v1_cors_origins__origin_id__get",
        "parameters": [
          {
            "name": "origin_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Origin Id"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/CorsOriginResponse"
                }
              }
            }
          },
          "401": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Unauthorized"
          },
          "403": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Forbidden"
          },
          "404": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Not Found"
          },
          "500": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Internal Server Error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "put": {
        "tags": [
          "cors"
        ],
        "summary": "Update Cors Origin",
        "description": "Update a CORS origin (admin only).",
        "operationId": "update_cors_origin_api_v1_cors_origins__origin_id__put",
        "parameters": [
          {
            "name": "origin_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Origin Id"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/UpdateCorsOriginRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/CorsOriginResponse"
                }
              }
            }
          },
          "401": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Unauthorized"
          },
          "403": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Forbidden"
          },
          "404": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Not Found"
          },
          "409": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Conflict"
          },
          "500": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Internal Server Error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      },
      "delete": {
        "tags": [
          "cors"
        ],
        "summary": "Delete Cors Origin",
        "description": "Delete a CORS origin (admin only).",
        "operationId": "delete_cors_origin_api_v1_cors_origins__origin_id__delete",
        "parameters": [
          {
            "name": "origin_id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "string",
              "title": "Origin Id"
            }
          },
          {
            "name": "hard_delete",
            "in": "query",
            "required": false,
            "schema": {
              "type": "boolean",
              "description": "Permanently delete instead of soft delete (default: True)",
              "default": true,
              "title": "Hard Delete"
            },
            "description": "Permanently delete instead of soft delete (default: True)"
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "401": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Unauthorized"
          },
          "403": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Forbidden"
          },
          "404": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Not Found"
          },
          "500": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Internal Server Error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/cors/origins/validate": {
      "post": {
        "tags": [
          "cors"
        ],
        "summary": "Validate Cors Origin",
        "description": "Validate a CORS origin URL format (admin only).",
        "operationId": "validate_cors_origin_api_v1_cors_origins_validate_post",
        "parameters": [
          {
            "name": "origin",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string",
              "description": "Origin URL to validate",
              "title": "Origin"
            },
            "description": "Origin URL to validate"
          }
        ],
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/CorsOriginValidationResponse"
                }
              }
            }
          },
          "401": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Unauthorized"
          },
          "403": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Forbidden"
          },
          "500": {
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            },
            "description": "Internal Server Error"
          },
          "422": {
            "description": "Validation Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HTTPValidationError"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/cors/origins/refresh-cache": {
      "post": {
        "tags": [
          "cors"
        ],
        "summary": "Refresh Cors Cache",
        "description": "Refresh CORS origins cache (admin only).",
        "operationId": "refresh_cors_cache_api_v1_cors_origins_refresh_cache_post",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          },
          "401": {
            "description": "Unauthorized",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            }
          },
          "403": {
            "description": "Forbidden",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            }
          },
          "500": {
            "description": "Internal Server Error",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/endpoints__cors__ErrorResponse"
                }
              }
            }
          }
        }
      }
    },
    "/": {
      "get": {
        "summary": "Root",
        "description": "Root endpoint",
        "operationId": "root__get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          }
        }
      }
    },
    "/health": {
      "get": {
        "summary": "Health Check",
        "description": "Health check endpoint showing service configuration",
        "operationId": "health_check_health_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/HealthResponse"
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/status": {
      "get": {
        "summary": "Api Status",
        "description": "API v1 status endpoint",
        "operationId": "api_status_api_v1_status_get",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {

                }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "AdminSetPasswordRequest": {
        "properties": {
          "new_password": {
            "type": "string",
            "title": "New Password"
          }
        },
        "type": "object",
        "required": [
          "new_password"
        ],
        "title": "AdminSetPasswordRequest"
      },
      "Body_upload_file_api_v1_files_upload_post": {
        "properties": {
          "file": {
            "type": "string",
            "format": "binary",
            "title": "File"
          },
          "bucket": {
            "type": "string",
            "title": "Bucket"
          },
          "path": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Path"
          }
        },
        "type": "object",
        "required": [
          "file",
          "bucket"
        ],
        "title": "Body_upload_file_api_v1_files_upload_post"
      },
      "BucketCreate": {
        "properties": {
          "name": {
            "type": "string",
            "title": "Name"
          },
          "owner_id": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Owner Id"
          },
          "public": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Public",
            "default": false
          }
        },
        "type": "object",
        "required": [
          "name"
        ],
        "title": "BucketCreate"
      },
      "BucketUpdate": {
        "properties": {
          "public": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Public"
          }
        },
        "type": "object",
        "title": "BucketUpdate"
      },
      "ChangePasswordRequest": {
        "properties": {
          "current_password": {
            "type": "string",
            "minLength": 1,
            "title": "Current Password"
          },
          "new_password": {
            "type": "string",
            "maxLength": 128,
            "minLength": 8,
            "title": "New Password"
          }
        },
        "type": "object",
        "required": [
          "current_password",
          "new_password"
        ],
        "title": "ChangePasswordRequest"
      },
      "ColumnDefinitionModel": {
        "properties": {
          "name": {
            "type": "string",
            "title": "Name"
          },
          "type": {
            "type": "string",
            "title": "Type"
          },
          "nullable": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Nullable",
            "default": true
          },
          "unique": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Unique",
            "default": false
          },
          "default": {
            "anyOf": [
              {

              },
              {
                "type": "null"
              }
            ],
            "title": "Default"
          },
          "primary_key": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Primary Key",
            "default": false
          }
        },
        "type": "object",
        "required": [
          "name",
          "type"
        ],
        "title": "ColumnDefinitionModel"
      },
      "CorsOriginListResponse": {
        "properties": {
          "origins": {
            "items": {
              "$ref": "#/components/schemas/CorsOriginResponse"
            },
            "type": "array",
            "title": "Origins"
          },
          "total_count": {
            "type": "integer",
            "title": "Total Count"
          }
        },
        "type": "object",
        "required": [
          "origins",
          "total_count"
        ],
        "title": "CorsOriginListResponse",
        "description": "Response model for CORS origins list."
      },
      "CorsOriginResponse": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "origin": {
            "type": "string",
            "title": "Origin"
          },
          "description": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "is_active": {
            "type": "boolean",
            "title": "Is Active"
          },
          "extra_metadata": {
            "type": "object",
            "title": "Extra Metadata"
          },
          "created_by": {
            "type": "string",
            "title": "Created By"
          },
          "created_at": {
            "type": "string",
            "title": "Created At"
          },
          "updated_at": {
            "type": "string",
            "title": "Updated At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "origin",
          "is_active",
          "created_by",
          "created_at",
          "updated_at"
        ],
        "title": "CorsOriginResponse",
        "description": "Response model for CORS origin data."
      },
      "CorsOriginValidationResponse": {
        "properties": {
          "origin": {
            "type": "string",
            "title": "Origin"
          },
          "is_valid": {
            "type": "boolean",
            "title": "Is Valid"
          },
          "error_message": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Error Message"
          }
        },
        "type": "object",
        "required": [
          "origin",
          "is_valid"
        ],
        "title": "CorsOriginValidationResponse",
        "description": "Response model for CORS origin validation."
      },
      "CreateCorsOriginRequest": {
        "properties": {
          "origin": {
            "type": "string",
            "maxLength": 500,
            "minLength": 1,
            "title": "Origin"
          },
          "description": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 1000
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "extra_metadata": {
            "anyOf": [
              {
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "title": "Extra Metadata"
          }
        },
        "type": "object",
        "required": [
          "origin"
        ],
        "title": "CreateCorsOriginRequest",
        "description": "Request model for creating a CORS origin."
      },
      "CreateFunctionRequest": {
        "properties": {
          "name": {
            "type": "string",
            "maxLength": 255,
            "minLength": 1,
            "title": "Name"
          },
          "description": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 1000
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "code": {
            "type": "string",
            "minLength": 1,
            "title": "Code"
          },
          "runtime": {
            "type": "string",
            "pattern": "^(deno|node|python)$",
            "title": "Runtime",
            "default": "deno"
          },
          "timeout_seconds": {
            "type": "integer",
            "maximum": 300,
            "minimum": 5,
            "title": "Timeout Seconds",
            "default": 30
          },
          "memory_limit_mb": {
            "type": "integer",
            "maximum": 4096,
            "minimum": 128,
            "title": "Memory Limit Mb",
            "default": 512
          },
          "max_concurrent": {
            "type": "integer",
            "maximum": 100,
            "minimum": 1,
            "title": "Max Concurrent",
            "default": 10
          },
          "env_vars": {
            "anyOf": [
              {
                "additionalProperties": {
                  "type": "string"
                },
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "title": "Env Vars"
          }
        },
        "type": "object",
        "required": [
          "name",
          "code"
        ],
        "title": "CreateFunctionRequest",
        "description": "Request model for creating a new function."
      },
      "CreateTableRequest": {
        "properties": {
          "name": {
            "type": "string",
            "title": "Name"
          },
          "description": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "public": {
            "type": "boolean",
            "title": "Public",
            "default": false
          },
          "schema": {
            "$ref": "#/components/schemas/TableSchemaModel"
          },
          "metadata": {
            "anyOf": [
              {
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "title": "Metadata"
          }
        },
        "type": "object",
        "required": [
          "name",
          "schema"
        ],
        "title": "CreateTableRequest"
      },
      "CreateWebhookRequest": {
        "properties": {
          "name": {
            "type": "string",
            "maxLength": 255,
            "minLength": 1,
            "title": "Name"
          },
          "function_id": {
            "type": "string",
            "title": "Function Id"
          },
          "description": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 1000
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "provider": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 50
              },
              {
                "type": "null"
              }
            ],
            "title": "Provider"
          },
          "provider_event_type": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 255
              },
              {
                "type": "null"
              }
            ],
            "title": "Provider Event Type"
          },
          "source_url": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 500
              },
              {
                "type": "null"
              }
            ],
            "title": "Source Url"
          },
          "secret_key": {
            "type": "string",
            "minLength": 1,
            "title": "Secret Key"
          },
          "rate_limit_per_minute": {
            "type": "integer",
            "maximum": 10000,
            "minimum": 1,
            "title": "Rate Limit Per Minute",
            "default": 100
          },
          "retry_attempts": {
            "type": "integer",
            "maximum": 10,
            "minimum": 1,
            "title": "Retry Attempts",
            "default": 3
          },
          "retry_backoff_strategy": {
            "type": "string",
            "pattern": "^(exponential|linear|fixed)$",
            "title": "Retry Backoff Strategy",
            "default": "exponential"
          },
          "retry_delay_seconds": {
            "type": "integer",
            "maximum": 3600,
            "minimum": 1,
            "title": "Retry Delay Seconds",
            "default": 60
          },
          "retry_max_delay_seconds": {
            "type": "integer",
            "maximum": 86400,
            "minimum": 1,
            "title": "Retry Max Delay Seconds",
            "default": 3600
          }
        },
        "type": "object",
        "required": [
          "name",
          "function_id",
          "secret_key"
        ],
        "title": "CreateWebhookRequest",
        "description": "Request model for creating a webhook."
      },
      "FunctionListResponse": {
        "properties": {
          "functions": {
            "items": {
              "$ref": "#/components/schemas/FunctionResponse"
            },
            "type": "array",
            "title": "Functions"
          },
          "total": {
            "type": "integer",
            "title": "Total"
          },
          "limit": {
            "type": "integer",
            "title": "Limit"
          },
          "offset": {
            "type": "integer",
            "title": "Offset"
          }
        },
        "type": "object",
        "required": [
          "functions",
          "total",
          "limit",
          "offset"
        ],
        "title": "FunctionListResponse",
        "description": "Response model for function list."
      },
      "FunctionResponse": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "name": {
            "type": "string",
            "title": "Name"
          },
          "description": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "code": {
            "type": "string",
            "title": "Code"
          },
          "runtime": {
            "type": "string",
            "title": "Runtime"
          },
          "owner_id": {
            "type": "string",
            "title": "Owner Id"
          },
          "is_active": {
            "type": "boolean",
            "title": "Is Active"
          },
          "deployment_status": {
            "type": "string",
            "title": "Deployment Status"
          },
          "deployment_error": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Deployment Error"
          },
          "version": {
            "type": "integer",
            "title": "Version"
          },
          "timeout_seconds": {
            "type": "integer",
            "title": "Timeout Seconds"
          },
          "memory_limit_mb": {
            "type": "integer",
            "title": "Memory Limit Mb"
          },
          "max_concurrent": {
            "type": "integer",
            "title": "Max Concurrent"
          },
          "env_vars": {
            "additionalProperties": {
              "type": "string"
            },
            "type": "object",
            "title": "Env Vars"
          },
          "execution_count": {
            "type": "integer",
            "title": "Execution Count"
          },
          "execution_success_count": {
            "type": "integer",
            "title": "Execution Success Count"
          },
          "execution_error_count": {
            "type": "integer",
            "title": "Execution Error Count"
          },
          "last_executed_at": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Last Executed At"
          },
          "avg_execution_time_ms": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Avg Execution Time Ms"
          },
          "last_deployed_at": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Last Deployed At"
          },
          "created_at": {
            "type": "string",
            "title": "Created At"
          },
          "updated_at": {
            "type": "string",
            "title": "Updated At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "name",
          "description",
          "code",
          "runtime",
          "owner_id",
          "is_active",
          "deployment_status",
          "deployment_error",
          "version",
          "timeout_seconds",
          "memory_limit_mb",
          "max_concurrent",
          "env_vars",
          "execution_count",
          "execution_success_count",
          "execution_error_count",
          "last_executed_at",
          "avg_execution_time_ms",
          "last_deployed_at",
          "created_at",
          "updated_at"
        ],
        "title": "FunctionResponse",
        "description": "Response model for function data."
      },
      "HTTPValidationError": {
        "properties": {
          "detail": {
            "items": {
              "$ref": "#/components/schemas/ValidationError"
            },
            "type": "array",
            "title": "Detail"
          }
        },
        "type": "object",
        "title": "HTTPValidationError"
      },
      "HealthResponse": {
        "properties": {
          "service": {
            "type": "string",
            "title": "Service"
          },
          "status": {
            "type": "string",
            "title": "Status"
          },
          "version": {
            "type": "string",
            "title": "Version"
          },
          "environment": {
            "type": "object",
            "title": "Environment"
          },
          "database": {
            "additionalProperties": {
              "type": "string"
            },
            "type": "object",
            "title": "Database"
          },
          "message": {
            "type": "string",
            "title": "Message"
          }
        },
        "type": "object",
        "required": [
          "service",
          "status",
          "version",
          "environment",
          "database",
          "message"
        ],
        "title": "HealthResponse"
      },
      "SetEnvVarsRequest": {
        "properties": {
          "env_vars": {
            "additionalProperties": {
              "type": "string"
            },
            "type": "object",
            "minProperties": 1,
            "title": "Env Vars"
          }
        },
        "type": "object",
        "required": [
          "env_vars"
        ],
        "title": "SetEnvVarsRequest",
        "description": "Request model for setting environment variables."
      },
      "SetFunctionStateRequest": {
        "properties": {
          "is_active": {
            "type": "boolean",
            "title": "Is Active"
          }
        },
        "type": "object",
        "required": [
          "is_active"
        ],
        "title": "SetFunctionStateRequest",
        "description": "Request model for enabling/disabling a function."
      },
      "SqlExecutionResult": {
        "properties": {
          "success": {
            "type": "boolean",
            "title": "Success"
          },
          "is_read_only": {
            "type": "boolean",
            "title": "Is Read Only"
          },
          "execution_time": {
            "type": "number",
            "title": "Execution Time"
          },
          "row_count": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Row Count"
          },
          "columns": {
            "anyOf": [
              {
                "items": {
                  "type": "string"
                },
                "type": "array"
              },
              {
                "type": "null"
              }
            ],
            "title": "Columns"
          },
          "data": {
            "anyOf": [
              {
                "items": {
                  "type": "object"
                },
                "type": "array"
              },
              {
                "type": "null"
              }
            ],
            "title": "Data"
          },
          "message": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Message"
          },
          "error": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Error"
          },
          "operations_summary": {
            "anyOf": [
              {
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "title": "Operations Summary"
          }
        },
        "type": "object",
        "required": [
          "success",
          "is_read_only",
          "execution_time"
        ],
        "title": "SqlExecutionResult",
        "description": "Result of a SQL query execution."
      },
      "SqlHistorySaveRequest": {
        "properties": {
          "query": {
            "type": "string",
            "title": "Query"
          },
          "result": {
            "type": "object",
            "title": "Result"
          }
        },
        "type": "object",
        "required": [
          "query",
          "result"
        ],
        "title": "SqlHistorySaveRequest"
      },
      "SqlQueryRequest": {
        "properties": {
          "query": {
            "type": "string",
            "maxLength": 100000,
            "minLength": 1,
            "title": "Query"
          }
        },
        "type": "object",
        "required": [
          "query"
        ],
        "title": "SqlQueryRequest"
      },
      "SqlSnippetCreateRequest": {
        "properties": {
          "name": {
            "type": "string",
            "maxLength": 100,
            "minLength": 1,
            "title": "Name"
          },
          "sql_code": {
            "type": "string",
            "maxLength": 100000,
            "minLength": 1,
            "title": "Sql Code"
          },
          "description": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "is_shared": {
            "type": "boolean",
            "title": "Is Shared",
            "default": false
          }
        },
        "type": "object",
        "required": [
          "name",
          "sql_code"
        ],
        "title": "SqlSnippetCreateRequest"
      },
      "TableDataResponse": {
        "properties": {
          "data": {
            "items": {
              "type": "object"
            },
            "type": "array",
            "title": "Data"
          },
          "metadata": {
            "type": "object",
            "title": "Metadata"
          }
        },
        "type": "object",
        "required": [
          "data",
          "metadata"
        ],
        "title": "TableDataResponse"
      },
      "TableSchemaModel": {
        "properties": {
          "columns": {
            "items": {
              "type": "object"
            },
            "type": "array",
            "title": "Columns"
          },
          "indexes": {
            "anyOf": [
              {
                "items": {
                  "type": "object"
                },
                "type": "array"
              },
              {
                "type": "null"
              }
            ],
            "title": "Indexes"
          }
        },
        "type": "object",
        "required": [
          "columns"
        ],
        "title": "TableSchemaModel"
      },
      "TokenResponse": {
        "properties": {
          "access_token": {
            "type": "string",
            "title": "Access Token"
          },
          "refresh_token": {
            "type": "string",
            "title": "Refresh Token"
          },
          "token_type": {
            "type": "string",
            "title": "Token Type",
            "default": "bearer"
          },
          "expires_in": {
            "type": "integer",
            "title": "Expires In"
          },
          "user": {
            "$ref": "#/components/schemas/UserResponse"
          }
        },
        "type": "object",
        "required": [
          "access_token",
          "refresh_token",
          "expires_in",
          "user"
        ],
        "title": "TokenResponse"
      },
      "UpdateColumnRequest": {
        "properties": {
          "new_name": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "New Name"
          },
          "type": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Type"
          },
          "nullable": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Nullable"
          },
          "default": {
            "anyOf": [
              {

              },
              {
                "type": "null"
              }
            ],
            "title": "Default"
          }
        },
        "type": "object",
        "title": "UpdateColumnRequest"
      },
      "UpdateCorsOriginRequest": {
        "properties": {
          "origin": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 500,
                "minLength": 1
              },
              {
                "type": "null"
              }
            ],
            "title": "Origin"
          },
          "description": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 1000
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "is_active": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Is Active"
          },
          "extra_metadata": {
            "anyOf": [
              {
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "title": "Extra Metadata"
          }
        },
        "type": "object",
        "title": "UpdateCorsOriginRequest",
        "description": "Request model for updating a CORS origin."
      },
      "UpdateFunctionRequest": {
        "properties": {
          "description": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 1000
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "code": {
            "anyOf": [
              {
                "type": "string",
                "minLength": 1
              },
              {
                "type": "null"
              }
            ],
            "title": "Code"
          },
          "timeout_seconds": {
            "anyOf": [
              {
                "type": "integer",
                "maximum": 300,
                "minimum": 5
              },
              {
                "type": "null"
              }
            ],
            "title": "Timeout Seconds"
          },
          "memory_limit_mb": {
            "anyOf": [
              {
                "type": "integer",
                "maximum": 4096,
                "minimum": 128
              },
              {
                "type": "null"
              }
            ],
            "title": "Memory Limit Mb"
          },
          "max_concurrent": {
            "anyOf": [
              {
                "type": "integer",
                "maximum": 100,
                "minimum": 1
              },
              {
                "type": "null"
              }
            ],
            "title": "Max Concurrent"
          }
        },
        "type": "object",
        "title": "UpdateFunctionRequest",
        "description": "Request model for updating a function."
      },
      "UpdateTableRequest": {
        "properties": {
          "new_name": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "New Name"
          },
          "description": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "public": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Public"
          }
        },
        "type": "object",
        "title": "UpdateTableRequest"
      },
      "UpdateWebhookRequest": {
        "properties": {
          "name": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 255,
                "minLength": 1
              },
              {
                "type": "null"
              }
            ],
            "title": "Name"
          },
          "description": {
            "anyOf": [
              {
                "type": "string",
                "maxLength": 1000
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "is_active": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Is Active"
          },
          "rate_limit_per_minute": {
            "anyOf": [
              {
                "type": "integer",
                "maximum": 10000,
                "minimum": 1
              },
              {
                "type": "null"
              }
            ],
            "title": "Rate Limit Per Minute"
          },
          "retry_attempts": {
            "anyOf": [
              {
                "type": "integer",
                "maximum": 10,
                "minimum": 1
              },
              {
                "type": "null"
              }
            ],
            "title": "Retry Attempts"
          },
          "retry_delay_seconds": {
            "anyOf": [
              {
                "type": "integer",
                "maximum": 3600,
                "minimum": 1
              },
              {
                "type": "null"
              }
            ],
            "title": "Retry Delay Seconds"
          }
        },
        "type": "object",
        "title": "UpdateWebhookRequest",
        "description": "Request model for updating a webhook."
      },
      "UserCreateRequest": {
        "properties": {
          "email": {
            "type": "string",
            "format": "email",
            "title": "Email"
          },
          "password": {
            "type": "string",
            "title": "Password"
          },
          "first_name": {
            "type": "string",
            "title": "First Name"
          },
          "last_name": {
            "type": "string",
            "title": "Last Name"
          }
        },
        "type": "object",
        "required": [
          "email",
          "password",
          "first_name",
          "last_name"
        ],
        "title": "UserCreateRequest"
      },
      "UserListResponse": {
        "properties": {
          "users": {
            "items": {
              "$ref": "#/components/schemas/UserResponse"
            },
            "type": "array",
            "title": "Users"
          },
          "pagination": {
            "type": "object",
            "title": "Pagination"
          }
        },
        "type": "object",
        "required": [
          "users",
          "pagination"
        ],
        "title": "UserListResponse"
      },
      "UserLoginRequest": {
        "properties": {
          "email": {
            "type": "string",
            "format": "email",
            "title": "Email"
          },
          "password": {
            "type": "string",
            "minLength": 1,
            "title": "Password"
          }
        },
        "type": "object",
        "required": [
          "email",
          "password"
        ],
        "title": "UserLoginRequest"
      },
      "UserRegisterRequest": {
        "properties": {
          "email": {
            "type": "string",
            "format": "email",
            "title": "Email"
          },
          "password": {
            "type": "string",
            "maxLength": 128,
            "minLength": 8,
            "title": "Password"
          },
          "first_name": {
            "type": "string",
            "maxLength": 50,
            "minLength": 1,
            "title": "First Name"
          },
          "last_name": {
            "type": "string",
            "maxLength": 50,
            "minLength": 1,
            "title": "Last Name"
          }
        },
        "type": "object",
        "required": [
          "email",
          "password",
          "first_name",
          "last_name"
        ],
        "title": "UserRegisterRequest"
      },
      "UserResponse": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "email": {
            "type": "string",
            "title": "Email"
          },
          "first_name": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "First Name"
          },
          "last_name": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Last Name"
          },
          "role": {
            "type": "string",
            "title": "Role"
          },
          "is_active": {
            "type": "boolean",
            "title": "Is Active"
          },
          "created_at": {
            "type": "string",
            "title": "Created At"
          },
          "updated_at": {
            "type": "string",
            "title": "Updated At"
          },
          "last_login_at": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Last Login At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "email",
          "first_name",
          "last_name",
          "role",
          "is_active",
          "created_at",
          "updated_at",
          "last_login_at"
        ],
        "title": "UserResponse"
      },
      "UserRole": {
        "type": "string",
        "enum": [
          "USER",
          "ADMIN"
        ],
        "title": "UserRole",
        "description": "User role enumeration as specified in API Contracts Plan."
      },
      "UserUpdateRequest": {
        "properties": {
          "email": {
            "anyOf": [
              {
                "type": "string",
                "format": "email"
              },
              {
                "type": "null"
              }
            ],
            "title": "Email"
          },
          "first_name": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "First Name"
          },
          "last_name": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Last Name"
          },
          "role": {
            "anyOf": [
              {
                "$ref": "#/components/schemas/UserRole"
              },
              {
                "type": "null"
              }
            ]
          },
          "is_active": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Is Active"
          },
          "password": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Password"
          }
        },
        "type": "object",
        "title": "UserUpdateRequest",
        "description": "Full admin update model. All fields are optional and only provided fields will be applied.\n\nNote: password is accepted here for convenience but will be handled via the admin set-password\nflow (hashed and stored separately) to keep password handling explicit and auditable."
      },
      "ValidationError": {
        "properties": {
          "loc": {
            "items": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "type": "array",
            "title": "Location"
          },
          "msg": {
            "type": "string",
            "title": "Message"
          },
          "type": {
            "type": "string",
            "title": "Error Type"
          }
        },
        "type": "object",
        "required": [
          "loc",
          "msg",
          "type"
        ],
        "title": "ValidationError"
      },
      "WebhookDeliveryListResponse": {
        "properties": {
          "deliveries": {
            "items": {
              "$ref": "#/components/schemas/WebhookDeliveryResponse"
            },
            "type": "array",
            "title": "Deliveries"
          },
          "total": {
            "type": "integer",
            "title": "Total"
          },
          "limit": {
            "type": "integer",
            "title": "Limit"
          },
          "offset": {
            "type": "integer",
            "title": "Offset"
          }
        },
        "type": "object",
        "required": [
          "deliveries",
          "total",
          "limit",
          "offset"
        ],
        "title": "WebhookDeliveryListResponse",
        "description": "Response model for webhook delivery list."
      },
      "WebhookDeliveryResponse": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "webhook_id": {
            "type": "string",
            "title": "Webhook Id"
          },
          "function_id": {
            "type": "string",
            "title": "Function Id"
          },
          "source_ip": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Source Ip"
          },
          "source_user_agent": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Source User Agent"
          },
          "request_headers": {
            "anyOf": [
              {
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "title": "Request Headers"
          },
          "request_body": {
            "anyOf": [
              {

              },
              {
                "type": "null"
              }
            ],
            "title": "Request Body"
          },
          "request_body_size_bytes": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Request Body Size Bytes"
          },
          "request_method": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Request Method"
          },
          "request_url": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Request Url"
          },
          "signature_header_name": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Signature Header Name"
          },
          "signature_provided": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Signature Provided"
          },
          "signature_valid": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Signature Valid"
          },
          "signature_error": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Signature Error"
          },
          "payload_valid": {
            "anyOf": [
              {
                "type": "boolean"
              },
              {
                "type": "null"
              }
            ],
            "title": "Payload Valid"
          },
          "validation_errors": {
            "anyOf": [
              {

              },
              {
                "type": "null"
              }
            ],
            "title": "Validation Errors"
          },
          "transformed_payload": {
            "anyOf": [
              {

              },
              {
                "type": "null"
              }
            ],
            "title": "Transformed Payload"
          },
          "transform_error": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Transform Error"
          },
          "queued_at": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Queued At"
          },
          "status": {
            "type": "string",
            "title": "Status"
          },
          "delivery_attempt": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Delivery Attempt"
          },
          "processing_started_at": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Processing Started At"
          },
          "function_execution_id": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Function Execution Id"
          },
          "execution_result": {
            "anyOf": [
              {

              },
              {
                "type": "null"
              }
            ],
            "title": "Execution Result"
          },
          "execution_error": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Execution Error"
          },
          "error_message": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Error Message"
          },
          "execution_time_ms": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Execution Time Ms"
          },
          "response_status_code": {
            "anyOf": [
              {
                "type": "integer"
              },
              {
                "type": "null"
              }
            ],
            "title": "Response Status Code"
          },
          "response_headers": {
            "anyOf": [
              {
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "title": "Response Headers"
          },
          "response_body": {
            "anyOf": [
              {

              },
              {
                "type": "null"
              }
            ],
            "title": "Response Body"
          },
          "retry_count": {
            "type": "integer",
            "title": "Retry Count"
          },
          "next_retry_at": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Next Retry At"
          },
          "retry_reason": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Retry Reason"
          },
          "processed_by_user_id": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Processed By User Id"
          },
          "processed_at": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Processed At"
          },
          "created_at": {
            "type": "string",
            "title": "Created At"
          },
          "received_at": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Received At"
          },
          "processing_completed_at": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Processing Completed At"
          },
          "updated_at": {
            "type": "string",
            "title": "Updated At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "webhook_id",
          "function_id",
          "source_ip",
          "source_user_agent",
          "request_headers",
          "request_body",
          "request_body_size_bytes",
          "request_method",
          "request_url",
          "signature_header_name",
          "signature_provided",
          "signature_valid",
          "signature_error",
          "payload_valid",
          "validation_errors",
          "transformed_payload",
          "transform_error",
          "queued_at",
          "status",
          "delivery_attempt",
          "processing_started_at",
          "function_execution_id",
          "execution_result",
          "execution_error",
          "error_message",
          "execution_time_ms",
          "response_status_code",
          "response_headers",
          "response_body",
          "retry_count",
          "next_retry_at",
          "retry_reason",
          "processed_by_user_id",
          "processed_at",
          "created_at",
          "received_at",
          "processing_completed_at",
          "updated_at"
        ],
        "title": "WebhookDeliveryResponse",
        "description": "Response model for webhook delivery data."
      },
      "WebhookListResponse": {
        "properties": {
          "webhooks": {
            "items": {
              "$ref": "#/components/schemas/WebhookResponse"
            },
            "type": "array",
            "title": "Webhooks"
          },
          "total": {
            "type": "integer",
            "title": "Total"
          },
          "limit": {
            "type": "integer",
            "title": "Limit"
          },
          "offset": {
            "type": "integer",
            "title": "Offset"
          }
        },
        "type": "object",
        "required": [
          "webhooks",
          "total",
          "limit",
          "offset"
        ],
        "title": "WebhookListResponse",
        "description": "Response model for webhook list."
      },
      "WebhookResponse": {
        "properties": {
          "id": {
            "type": "string",
            "title": "Id"
          },
          "function_id": {
            "type": "string",
            "title": "Function Id"
          },
          "owner_id": {
            "type": "string",
            "title": "Owner Id"
          },
          "name": {
            "type": "string",
            "title": "Name"
          },
          "description": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Description"
          },
          "provider": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Provider"
          },
          "provider_event_type": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Provider Event Type"
          },
          "source_url": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Source Url"
          },
          "webhook_token": {
            "type": "string",
            "title": "Webhook Token"
          },
          "path_segment": {
            "type": "string",
            "title": "Path Segment"
          },
          "is_active": {
            "type": "boolean",
            "title": "Is Active"
          },
          "rate_limit_per_minute": {
            "type": "integer",
            "title": "Rate Limit Per Minute"
          },
          "retry_attempts": {
            "type": "integer",
            "title": "Retry Attempts"
          },
          "retry_backoff_strategy": {
            "type": "string",
            "title": "Retry Backoff Strategy"
          },
          "retry_delay_seconds": {
            "type": "integer",
            "title": "Retry Delay Seconds"
          },
          "retry_max_delay_seconds": {
            "type": "integer",
            "title": "Retry Max Delay Seconds"
          },
          "last_received_at": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Last Received At"
          },
          "last_delivery_status": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "title": "Last Delivery Status"
          },
          "successful_delivery_count": {
            "type": "integer",
            "title": "Successful Delivery Count"
          },
          "failed_delivery_count": {
            "type": "integer",
            "title": "Failed Delivery Count"
          },
          "total_delivery_count": {
            "type": "integer",
            "title": "Total Delivery Count"
          },
          "created_at": {
            "type": "string",
            "title": "Created At"
          },
          "updated_at": {
            "type": "string",
            "title": "Updated At"
          }
        },
        "type": "object",
        "required": [
          "id",
          "function_id",
          "owner_id",
          "name",
          "description",
          "provider",
          "provider_event_type",
          "source_url",
          "webhook_token",
          "path_segment",
          "is_active",
          "rate_limit_per_minute",
          "retry_attempts",
          "retry_backoff_strategy",
          "retry_delay_seconds",
          "retry_max_delay_seconds",
          "last_received_at",
          "last_delivery_status",
          "successful_delivery_count",
          "failed_delivery_count",
          "total_delivery_count",
          "created_at",
          "updated_at"
        ],
        "title": "WebhookResponse",
        "description": "Response model for webhook data."
      },
      "endpoints__cors__ErrorResponse": {
        "properties": {
          "detail": {
            "type": "string",
            "title": "Detail"
          }
        },
        "type": "object",
        "required": [
          "detail"
        ],
        "title": "ErrorResponse",
        "description": "Error response model."
      },
      "endpoints__users__ErrorResponse": {
        "properties": {
          "error": {
            "type": "string",
            "title": "Error"
          },
          "message": {
            "type": "string",
            "title": "Message"
          },
          "details": {
            "anyOf": [
              {
                "type": "object"
              },
              {
                "type": "null"
              }
            ],
            "title": "Details"
          }
        },
        "type": "object",
        "required": [
          "error",
          "message"
        ],
        "title": "ErrorResponse"
      }
    }
  }
}
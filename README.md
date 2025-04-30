# SelfDB

SelfDB is a self-hosted, open-source alternative to Supabase, providing PostgreSQL database, authentication, object storage, and real-time capabilities in a single, containerized platform.

## Features

- **PostgreSQL Database**: Powerful, reliable database for your application data
- **Authentication**: Secure user authentication with JWT tokens and anonymous access capabilities
- **Object Storage**: S3-compatible file storage using MinIO
- **Real-time Updates**: WebSocket-based real-time data synchronization
- **Cloud Functions**: Serverless functions using Deno 2.0 for custom business logic
- **Containerized**: Easy deployment with Docker and Docker Compose
- **Production-Ready**: Includes security, logging, and monitoring considerations

## Prerequisites

- Docker and Docker Compose
- Git (for cloning the repository)

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/selfdb.git
   cd selfdb
   ```

2. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file to set secure passwords and configuration.

4. Start the application using the provided script (which sets up Docker volumes for data persistence):
   ```bash
   ./start.sh
   ```

   **Note:** The application uses Docker named volumes for data persistence. These volumes are managed by Docker and will persist even when containers are removed.

   Alternatively, you can start the services directly with Docker Compose:
   ```bash
   docker-compose up -d
   ```

5. The database will be automatically initialized on first startup with:
   - Database tables created via migrations
   - Default superuser created with the credentials specified in your `.env` file:
     - Email: `DEFAULT_ADMIN_EMAIL` (default: `admin@example.com`)
     - Password: `DEFAULT_ADMIN_PASSWORD` (default: `adminpassword`)
   - Anonymous API key (`ANON_KEY`) generated for public access to resources

   **Important:** Change these credentials in your `.env` file for production use!

   If you need to manually run the initialization later:
   ```bash
   docker-compose exec backend python -m app.initial_data
   ```

6. Access the application:
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - MinIO Console: http://localhost:9001 (login with MINIO_ROOT_USER and MINIO_ROOT_PASSWORD from .env)
   - Deno Runtime: http://localhost:8090 (internal service for cloud functions)

## Architecture

SelfDB consists of the following components:

- **PostgreSQL**: Database for storing application data
- **MinIO**: Object storage for files
- **Backend API**: FastAPI application providing REST endpoints and WebSocket connections
- **Frontend**: React application for user interface
- **Deno Runtime**: Serverless function execution environment using Deno 2.0

## Anonymous Access

SelfDB supports anonymous access to public resources using an API key. This allows unauthenticated clients to access designated public resources without requiring user login.

### How it works

1. A unique `ANON_KEY` is automatically generated during setup and stored in the `.env` file.
2. Clients include this key in the `apikey` HTTP header of their requests.
3. Endpoints check if the request is authenticated (JWT token), anonymous (valid `ANON_KEY`), or unauthorized.
4. Resources (like buckets and files) have an `is_public` flag that controls whether they can be accessed anonymously.

#### Backend Implementation

The SelfDB backend implements anonymous access through a dedicated authentication dependency:

- An `APIKeyHeader` scheme extracts the key from the `apikey` HTTP header
- The `get_current_user_or_anon` dependency function checks for both JWT tokens and the anon key
- When a valid anon key is provided, it returns a special `ANON_USER_ROLE` constant
- API endpoints can distinguish between authenticated users, anonymous users, and unauthorized requests
- This allows for fine-grained access control based on authentication status

### Using the Anonymous API Key

To access public resources without authentication:

```bash
# Example using curl
curl -H "apikey: YOUR_ANON_KEY" http://localhost:8000/api/v1/buckets/public
```

Where `YOUR_ANON_KEY` is the value generated in your `.env` file.

#### Client Implementation

In client applications, you typically want to use JWT tokens for authenticated users and fall back to the anon key for unauthenticated users. Here's an example using axios interceptors:

```typescript
// Get the API URL and anonymous key from environment variables
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const ANON_KEY = import.meta.env.VITE_ANON_KEY;

// Create a base axios instance for SelfDB API
const API = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add authentication to all requests
API.interceptors.request.use(config => {
  // First check for a token (authenticated user)
  const token = localStorage.getItem('access_token');

  if (token && config.headers) {
    // Use Bearer token for authenticated requests
    config.headers.Authorization = `Bearer ${token}`;
  } else if (ANON_KEY && config.headers) {
    // Fall back to anonymous key for unauthenticated requests
    config.headers.apikey = ANON_KEY;
  }

  return config;
});
```

This pattern allows your application to seamlessly handle both authenticated and anonymous users.

### Security Considerations

- The `ANON_KEY` provides read and write access to public resources.
- Only mark resources as public if you intend them to be accessible without authentication.
- For production use, consider regenerating the `ANON_KEY` periodically.
- Anonymous users can typically:
  - Read data from public tables
  - Write data to public tables (with appropriate permissions)
  - List public buckets
  - Upload files to public buckets
  - View files from public buckets
- Anonymous users cannot typically:
  - Access private resources
  - Modify or delete resources created by authenticated users
  - Access administrative endpoints

### Sample Application

For a complete example of anonymous access implementation, see the `open-discussion-board` sample application in the `@sample-apps/` directory. This application demonstrates:

- Support for both authenticated and anonymous users
- Anonymous posting of topics and comments without requiring registration
- Media upload support for both anonymous and authenticated users
- Proper implementation of the anon key in API requests
- File uploads to public buckets using anonymous access

To run the sample app:

1. Navigate to the sample app directory: `cd sample-apps/open-discussion-board`
2. Install dependencies: `npm install`
3. Set up environment variables: `./setup.sh` (automatically copies the ANON_KEY from your SelfDB `.env` file)
4. Start the development server: `npm run dev`

The app will be available at `http://localhost:5173`.

## Development

### Rebuilding Containers

During development, you may need to rebuild your containers without losing your data. Use the provided rebuild script:

```bash
./rebuild.sh
```

This script will rebuild all containers while preserving your data stored in Docker volumes.

### Backend

The backend is built with FastAPI and provides:

- REST API endpoints for authentication, file management, etc.
- WebSocket connections for real-time updates
- Database models and migrations
- Integration with MinIO for object storage
- Cloud function management and deployment
- Code validation and linting services for the function editor

To run the backend in development mode:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

The frontend is built with React and provides:

- User interface for authentication, file management, etc.
- Integration with the backend API
- Real-time updates using WebSockets
- Cloud function management interface

To run the frontend in development mode:

```bash
cd frontend
npm install
npm start
```

### Cloud Functions

SelfDB includes a serverless function execution environment powered by Deno 2.0. This allows you to write and deploy custom business logic that runs in response to HTTP requests, scheduled events, or database changes.

Key features of the cloud functions system:

- **Deno 2.0 Runtime**: Modern JavaScript/TypeScript runtime with built-in security
- **Multiple Trigger Types**: Functions can be triggered by HTTP requests, scheduled events, or database changes
- **Environment Variables**: Securely store and access configuration and secrets
- **Version History**: Track changes to your functions with automatic versioning
- **Database Access**: Direct access to your PostgreSQL database from functions
- **Event-Driven Architecture**: Build reactive applications with real-time database triggers

Cloud functions are stored in the `./functions` directory and are automatically loaded by the Deno runtime container. The frontend provides a complete management interface for creating, editing, and deploying functions.

Example function:

```typescript
// Simple HTTP function
export default async function handler(req) {
  // Access environment variables
  const dbUrl = Deno.env.get("DATABASE_URL");

  // Process HTTP request
  if (req instanceof Request) {
    const url = new URL(req.url);
    const params = Object.fromEntries(url.searchParams.entries());

    return new Response(JSON.stringify({
      message: "Hello from SelfDB function!",
      method: req.method,
      params: params
    }), {
      headers: { "Content-Type": "application/json" }
    });
  }

  // For non-HTTP invocations (scheduled runs, etc.)
  console.log("Function executed at:", new Date().toISOString());
  return { success: true };
}
```

## Production Deployment

For production deployment, consider the following:

1. Use strong, unique passwords in the `.env` file
2. Set up a reverse proxy (like Nginx) with SSL/TLS
3. Configure proper backup strategies for the data directories
4. Set up monitoring and logging

## Backup and Restore

To backup your data:

1. Stop the containers:
   ```bash
   docker-compose down
   ```

2. Backup the Docker volumes:
   ```bash
   # For PostgreSQL data
   docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar -czf /backup/postgres-backup.tar.gz /data

   # For MinIO data
   docker run --rm -v minio_data:/data -v $(pwd):/backup alpine tar -czf /backup/minio-backup.tar.gz /data
   ```

To restore from a backup:

1. Stop the containers:
   ```bash
   docker-compose down
   ```

2. Remove existing volumes (if any):
   ```bash
   docker volume rm postgres_data minio_data || true
   ```

3. Create empty volumes:
   ```bash
   docker volume create postgres_data
   docker volume create minio_data
   ```

4. Restore from backups:
   ```bash
   # For PostgreSQL data
   docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine sh -c "rm -rf /data/* && tar -xzf /backup/postgres-backup.tar.gz -C /"

   # For MinIO data
   docker run --rm -v minio_data:/data -v $(pwd):/backup alpine sh -c "rm -rf /data/* && tar -xzf /backup/minio-backup.tar.gz -C /"
   ```

5. Start the containers:
   ```bash
   docker-compose up -d
   ```

## Troubleshooting

### Volume Issues

If you encounter issues with the Docker volumes, you can use the cleanup script to reset your environment:

```bash
./cleanup.sh
```

This will:
1. Stop all containers
2. Remove all Docker volumes used by the application

After running the cleanup script, you can start fresh with:

```bash
./start.sh
```

**Note:** The cleanup script will delete all your data, so make sure you have backups if needed.

### Checking Volume Status

To check the status of your Docker volumes:

```bash
docker volume ls
```

To inspect a specific volume (e.g., postgres_data):

```bash
docker volume inspect postgres_data
```

### Cloud Function Issues

If you encounter issues with cloud functions:

1. Check the Deno runtime logs:
   ```bash
   docker logs selfdb_deno
   ```

2. Verify the function file exists in the `./functions` directory:
   ```bash
   ls -la ./functions
   ```

3. Check the health of the Deno runtime service:
   ```bash
   curl http://localhost:8090/health
   ```

4. If functions aren't loading properly, restart the Deno container:
   ```bash
   docker restart selfdb_deno
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.


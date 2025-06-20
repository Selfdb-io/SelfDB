# SelfDB Cloud Functions

This directory contains cloud functions for SelfDB. These functions can be triggered via HTTP requests, scheduled execution, database events, custom events, or run once on startup.

## Database Triggers

SelfDB now supports robust database triggers using PostgreSQL's LISTEN/NOTIFY mechanism. This allows your functions to react to database changes in real-time.

### How Database Triggers Work

1. When you define a function with a database trigger, SelfDB automatically:
   - Creates a PostgreSQL trigger function for the specified table
   - Creates a trigger on the table that fires on the specified operations (INSERT, UPDATE, DELETE)
   - Sets up a LISTEN on the specified channel
   - Processes notifications in real-time (no polling)

2. When a change occurs in the database:
   - The PostgreSQL trigger fires and sends a notification with the changed data
   - The SelfDB function runtime receives the notification and executes your function
   - Your function receives the operation type, table name, and data payload

### Creating a Function with Database Triggers

Here's an example of a function that reacts to changes in the `users` table:

```typescript
// Function metadata
export const description = "Reacts to changes in the users table";

// Define triggers for this function
export const triggers = [
  // Database trigger - listens for changes to the users table
  {
    type: "database",
    table: "users",
    operations: ["INSERT", "UPDATE", "DELETE"], // Optional: specify which operations to listen for
    channel: "users_changes" // Optional: specify a custom channel name (defaults to table_changes)
  }
];

// The function handler
export default async function handler(req, env) {
  // Get the trigger type from headers
  const triggerType = req.headers?.get("X-Trigger-Type");
  const dbChannel = req.headers?.get("X-Database-Channel");
  
  // If this is a database trigger
  if (triggerType === "database" && dbChannel) {
    // Get the notification payload
    const payload = await req.json();
    
    // The payload contains:
    // - operation: "INSERT", "UPDATE", or "DELETE"
    // - table: the table name
    // - data: the new record (for INSERT and UPDATE)
    // - old_data: the previous state (for UPDATE and DELETE)
    
    console.log(`Operation: ${payload.operation} on table ${payload.table}`);
    
    // Process based on operation type
    if (payload.operation === "INSERT") {
      // Handle new record
      return { success: true, message: "Processed new user" };
    } else if (payload.operation === "UPDATE") {
      // Handle updated record
      return { success: true, message: "Processed user update" };
    } else if (payload.operation === "DELETE") {
      // Handle deleted record
      return { success: true, message: "Processed user deletion" };
    }
  }
  
  // Handle other trigger types or HTTP requests
  return { message: "Function executed" };
}
```

### Testing Database Triggers

You can test database triggers in two ways:

1. **Make actual changes to the database**:
   - Insert, update, or delete records in the specified table
   - The function will be triggered automatically

2. **Manually send a notification**:
   - Make a POST request to `/db-notify` with a payload:
   ```json
   {
     "channel": "users_changes",
     "payload": {
       "operation": "INSERT",
       "table": "users",
       "data": {
         "id": "123e4567-e89b-12d3-a456-426614174000",
         "email": "user@example.com",
         "username": "newuser"
       }
     }
   }
   ```

### Best Practices

1. **Be specific about operations**: Only listen for the operations you need to process
2. **Keep functions focused**: Create separate functions for different business logic
3. **Handle errors gracefully**: Database triggers should be resilient
4. **Be mindful of performance**: Avoid heavy processing in database triggers
5. **Use idempotent operations**: Your function might be called multiple times for the same event

## Other Trigger Types

SelfDB functions also support:

- **HTTP triggers**: Respond to HTTP requests
- **Schedule triggers**: Run on a schedule using cron expressions
- **Event triggers**: React to custom events
- **One-time triggers**: Run once on startup

See the [How to Write Functions](../how_to_write_functions.md) documentation for more details.

# How to Write Functions for SelfDB

This guide explains how to create serverless functions for the SelfDB platform using the built-in function runtime.

## Table of Contents

1. [Introduction](#introduction)
2. [Function Structure](#function-structure)
3. [Trigger Types](#trigger-types)
4. [Environment Variables](#environment-variables)
5. [Database Access](#database-access)
6. [Examples](#examples)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)

## Introduction

SelfDB's serverless function runtime allows you to write and deploy TypeScript/JavaScript functions that can be triggered by HTTP requests, scheduled events, database changes, or custom events. Functions are automatically discovered and registered by the system.

Functions are stored in the `functions/` directory and are executed in a Deno runtime environment.

## Function Structure

Each function is a separate TypeScript file in the `functions/` directory. The file name (without the `.ts` extension) becomes the function name and the HTTP endpoint path.

A function file must have:

1. A default export function that serves as the handler
2. Optional metadata exports for configuration

### Basic Structure

```typescript
// @ts-nocheck
// deno-lint-ignore-file

// Function metadata (optional but recommended)
export const description = "Description of what this function does";

// Define triggers (optional - defaults to HTTP trigger if not specified)
export const triggers = [
  // Define one or more triggers here
];

// The function handler (required)
export default async function handler(req, env) {
  // Your function code here
  return {
    success: true,
    message: "Function executed successfully"
  };
}
```

### Handler Function

The handler function receives two parameters:

- `req`: A Request object (for HTTP triggers) or a mock Request object (for other triggers)
- `env`: An object containing environment variables

The handler function can return:

- A Response object
- Any JSON-serializable object (which will be converted to a JSON response)

## Trigger Types

Functions can have multiple triggers defined. If no triggers are defined, an HTTP trigger is added by default.

### HTTP Trigger

Responds to HTTP requests at the endpoint `/function-name`.

```typescript
{
  type: "http",
  method?: string | string[], // Optional: Specific HTTP methods to allow
  path?: string               // Optional: Custom path (defaults to /function-name)
}
```

Example:

```typescript
export const triggers = [
  {
    type: "http",
    method: ["GET", "POST"] // Only allow GET and POST requests
  }
];
```

### Schedule Trigger

Executes the function on a schedule using cron syntax.

```typescript
{
  type: "schedule",
  cron: string,    // Cron expression (e.g., "*/5 * * * *" for every 5 minutes)
  name?: string    // Optional: Name for this schedule
}
```

Example:

```typescript
export const triggers = [
  {
    type: "schedule",
    cron: "0 0 * * *", // Run at midnight every day
    name: "daily-job"
  }
];
```

### Database Trigger

Executes the function in response to database events. SelfDB automatically creates PostgreSQL triggers and functions to notify your function when database changes occur.

```typescript
{
  type: "database",
  table: string,        // Table name to watch
  operations?: string[], // Optional: Specific operations to watch ["INSERT", "UPDATE", "DELETE"]
  channel?: string      // Optional: PostgreSQL LISTEN/NOTIFY channel (defaults to `${table}_changes`)
}
```

Example:

```typescript
export const triggers = [
  {
    type: "database",
    table: "users",
    operations: ["INSERT", "UPDATE"]
  }
];
```

**How it works:**

1. When you define a database trigger, SelfDB automatically:
   - Creates a PostgreSQL trigger function for the specified table
   - Creates a trigger on the table that fires on the specified operations
   - Sets up a LISTEN on the specified channel
   - Processes notifications in real-time

2. When a change occurs in the database:
   - The PostgreSQL trigger fires and sends a notification with the changed data
   - The SelfDB function runtime receives the notification and executes your function
   - Your function receives a payload with the operation type, table name, and data

### Event Trigger

Executes the function in response to custom events.

```typescript
{
  type: "event",
  event: string // Event name to listen for
}
```

Example:

```typescript
export const triggers = [
  {
    type: "event",
    event: "user.signup"
  }
];
```

### One-Time Trigger

Executes the function once automatically when loaded and then marks it as completed if successful. The function will not run again unless manually triggered or if it fails.

```typescript
{
  type: "once",
  condition?: string // Optional: Condition to determine if it should run
}
```

Example:

```typescript
// Mark the function as run-once
export const runOnce = true;

export const triggers = [
  {
    type: "once"
  }
];
```

**Note**: One-time functions are automatically executed when the server starts. They are only marked as completed if they return `{ success: true, ... }`. If a function fails, it will be retried on the next server restart.

## Environment Variables

Environment variables are accessible through the `env` parameter passed to the handler function:

```typescript
export default async function handler(req, env) {
  // Access environment variables
  const dbUrl = env.DATABASE_URL;
  const apiKey = env.API_KEY;

  // Use environment variables
  // ...
}
```

## Database Access

Functions can access the database using the environment variables provided:

```typescript
export default async function handler(req, env) {
  // Connect to the database
  const client = await createClient({
    connectionString: env.DATABASE_URL,
  });

  try {
    await client.connect();

    // Execute queries
    const result = await client.queryObject("SELECT * FROM users");

    return {
      success: true,
      data: result.rows
    };
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  } finally {
    // Always close the connection
    await client.end();
  }
}
```

## Examples

### HTTP Function

```typescript
// simple-api.ts
export const description = "A simple API endpoint";

export const triggers = [
  {
    type: "http",
    method: ["GET"]
  }
];

export default async function handler(req, env) {
  const url = new URL(req.url);
  const name = url.searchParams.get("name") || "World";

  return {
    message: `Hello, ${name}!`,
    timestamp: new Date().toISOString()
  };
}
```

### Scheduled Function

```typescript
// daily-cleanup.ts
export const description = "Daily cleanup job";

export const triggers = [
  {
    type: "schedule",
    cron: "0 0 * * *", // Run at midnight every day
    name: "daily-cleanup"
  }
];

export default async function handler(req, env) {
  console.log("Running daily cleanup job");

  // Check if this is a scheduled execution
  const isScheduled = req.headers?.get("X-Trigger-Type") === "schedule";

  if (!isScheduled) {
    return {
      message: "This function is meant to be run on a schedule"
    };
  }

  // Perform cleanup tasks
  // ...

  return {
    success: true,
    message: "Cleanup completed",
    timestamp: new Date().toISOString()
  };
}
```

### Multi-Trigger Function

```typescript
// user-manager.ts
export const description = "User management function";

export const triggers = [
  // HTTP API for user management
  {
    type: "http",
    method: ["GET", "POST", "PUT", "DELETE"]
  },
  // Database trigger for user changes
  {
    type: "database",
    table: "users",
    operations: ["INSERT", "UPDATE", "DELETE"],
    channel: "users_changes"
  },
  // Weekly report generation
  {
    type: "schedule",
    cron: "0 0 * * 0", // Run at midnight on Sundays
    name: "weekly-user-report"
  },
  // Event trigger for user-related events
  {
    type: "event",
    event: "user.created"
  }
];

export default async function handler(req, env) {
  // Determine the trigger type
  const triggerType = req.headers?.get("X-Trigger-Type");
  const eventName = req.headers?.get("X-Event-Name");
  const dbChannel = req.headers?.get("X-Database-Channel");

  if (triggerType === "schedule") {
    // Handle scheduled execution
    return generateWeeklyReport(env);
  } else if (triggerType === "database") {
    // Handle database trigger
    return handleDatabaseEvent(req, dbChannel, env);
  } else if (triggerType === "event" && eventName === "user.created") {
    // Handle user.created event
    return handleUserCreatedEvent(req, env);
  } else if (triggerType === "once") {
    // Handle one-time execution
    return handleOneTimeSetup(env);
  } else {
    // Handle HTTP request
    return handleHttpRequest(req, env);
  }
}

async function generateWeeklyReport(env) {
  // Generate weekly report
  // ...
  return { success: true, message: "Weekly report generated" };
}

async function handleDatabaseEvent(req, channel, env) {
  // Get the notification payload
  const payload = await req.json();

  // The payload contains:
  // - operation: "INSERT", "UPDATE", or "DELETE"
  // - table: the table name
  // - data: the new record (for INSERT and UPDATE)
  // - old_data: the previous state (for UPDATE and DELETE)
  console.log(`Database event: ${payload.operation} on ${payload.table}`);

  // Handle database event based on operation
  if (payload.operation === "INSERT") {
    console.log("New record:", payload.data);
    // Handle insert operation
  } else if (payload.operation === "UPDATE") {
    console.log("Updated record:", payload.data);
    console.log("Previous state:", payload.old_data);
    // Handle update operation
  } else if (payload.operation === "DELETE") {
    console.log("Deleted record:", payload.old_data);
    // Handle delete operation
  }

  return { success: true, message: "Database event handled" };
}

async function handleUserCreatedEvent(req, env) {
  // Get the event data
  const userData = await req.json();

  // Process the user created event
  // ...

  return { success: true, message: "User created event handled" };
}

async function handleOneTimeSetup(env) {
  // Perform one-time setup tasks
  // ...

  return { success: true, message: "One-time setup completed" };
}

async function handleHttpRequest(req, env) {
  // Handle HTTP request
  // ...
  return { success: true, message: "HTTP request handled" };
}
```

### One-Time Setup Function

```typescript
// setup.ts
export const description = "One-time setup function";

// Mark this function as run-once
export const runOnce = true;

export const triggers = [
  // HTTP trigger for manual execution
  {
    type: "http",
    method: ["GET", "POST"]
  },
  // One-time trigger
  {
    type: "once"
  }
];

export default async function handler(req, env) {
  console.log("One-time setup function executed");

  // Get the trigger type from headers
  const triggerType = req.headers?.get("X-Trigger-Type");

  // If this is a one-time trigger or HTTP POST request
  if (triggerType === "once" || req.method === "POST") {
    // Perform setup tasks
    const setupTasks = [
      "Creating default configuration",
      "Setting up initial database schema",
      "Creating admin user"
    ];

    // In a real implementation, you would perform actual setup tasks here

    return {
      success: true,
      message: "One-time setup completed successfully",
      tasks: setupTasks
    };
  }

  // If this is a GET request, just return status
  return {
    success: true,
    message: "One-time setup function",
    status: "This function will only run once successfully"
  };
}
```

## Deployment

Functions are automatically deployed when you add, modify, or delete files in the `functions/` directory. The system watches for file changes and updates the function registry accordingly.

To manually reload all functions, you can make a request to the reload endpoint:

```
GET http://localhost:8090/reload
```

## API Endpoints

The function runtime provides several API endpoints for interacting with functions:

### Function Management

- **List Functions**: `GET /functions` - Lists all registered functions and their metadata
- **Reload Functions**: `GET /reload` - Reloads all functions from the filesystem
- **Function Status**: `GET /function-status/{name}` - Gets the status of a specific function
- **Health Check**: `GET /health` - Checks the health of the function runtime

### Event System

- **Emit Event**: `POST /emit-event` - Emits a custom event to trigger event-based functions

  Example request body:
  ```json
  {
    "event": "user.created",
    "data": {
      "id": "123",
      "email": "user@example.com"
    }
  }
  ```

### Database Notifications

- **Database Notify**: `POST /db-notify` - Sends a notification on a PostgreSQL channel

  Example request body:
  ```json
  {
    "channel": "users_changes",
    "payload": {
      "operation": "INSERT",
      "table": "users",
      "data": {
        "id": "123",
        "email": "user@example.com"
      }
    }
  }
  ```

  **Note**: This endpoint is primarily for testing. In production, database triggers are automatically created and will send notifications when database changes occur.

## Troubleshooting

### Viewing Logs

Function logs are available in the Deno container logs:

```bash
docker logs selfdb_deno
```

### Common Issues

1. **Function not found**: Make sure the file is in the `functions/` directory and has a `.ts` extension.

2. **Function not executing**: Check that the function has the correct trigger type defined.

3. **Syntax errors**: Check the logs for any syntax errors in your function code.

4. **Database connection issues**: Verify that the database connection string is correct and that the database is accessible from the function container.

5. **Permission errors**: The Deno runtime may require explicit permissions for certain operations. Check the logs for permission errors.

### Testing Functions

You can test HTTP functions by making requests to the function endpoint:

```
GET http://localhost:8090/function-name
```

You can list all registered functions with:

```
GET http://localhost:8090/functions
```

And check the health of the function runtime with:

```
GET http://localhost:8090/health
```
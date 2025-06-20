# Testing Database Triggers in SelfDB

This document provides instructions for testing the improved database trigger functionality in SelfDB.

## Overview

The database trigger system has been enhanced to:

1. Automatically create PostgreSQL trigger functions and triggers for tables
2. Use real-time notifications instead of polling
3. Provide detailed payloads with operation type, table name, and data

## Test Files

The following files are provided for testing:

- `test-db-trigger.ts`: A function that creates a test table and performs INSERT, UPDATE, and DELETE operations
- `test-triggers-handler.ts`: A function that listens for changes to the test_triggers table
- `db-trigger-example.ts`: A function that demonstrates database triggers for the users table

## Testing Steps

### 1. Start the SelfDB Environment

Make sure your SelfDB environment is running:

```bash
./start.sh
```

### 2. Check Function Registration

Access the functions list endpoint to verify that the test functions are registered:

```
GET http://localhost:8090/functions
```

You should see the test functions in the list.

### 3. Run the Test Function

Make a POST request to the test-db-trigger function:

```
POST http://localhost:8090/test-db-trigger
```

This will:
1. Create a test_triggers table if it doesn't exist
2. Set up a trigger function and trigger for the table
3. Perform INSERT, UPDATE, and DELETE operations on the table

### 4. Check the Logs

Check the logs of the Deno container to see if the test-triggers-handler function was triggered:

```bash
docker logs selfdb_deno
```

You should see log messages indicating that:
1. The test-triggers-handler function was executed
2. Database notifications were received for each operation
3. The function processed the INSERT, UPDATE, and DELETE operations

### 5. Test with the Users Table

You can also test with the users table by:

1. Creating a new user in the SelfDB UI
2. Updating the user
3. Deleting the user

Check the logs to see if the db-trigger-example function was triggered for these operations.

### 6. Manual Testing

You can manually trigger database notifications using the /db-notify endpoint:

```
POST http://localhost:8090/db-notify
```

With a request body like:

```json
{
  "channel": "test_triggers_changes",
  "payload": {
    "operation": "INSERT",
    "table": "test_triggers",
    "data": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "Manual Test",
      "value": 42,
      "created_at": "2023-01-01T00:00:00Z"
    }
  }
}
```

## Troubleshooting

If the database triggers are not working as expected:

1. Check that the PostgreSQL connection is established:
   ```
   GET http://localhost:8090/health
   ```
   The response should show `database: "connected"`.

2. Verify that the triggers are set up in PostgreSQL:
   ```sql
   SELECT * FROM pg_trigger WHERE tgname LIKE '%notify_trigger';
   ```

3. Check for any errors in the Deno container logs:
   ```bash
   docker logs selfdb_deno
   ```

4. Try reloading the functions:
   ```
   GET http://localhost:8090/reload
   ```

## Next Steps

Once you've verified that the database triggers are working correctly, you can:

1. Create your own functions with database triggers
2. Integrate database triggers with your application logic
3. Combine database triggers with other trigger types for complex workflows

# Message Notifications Cloud Function

This cloud function handles message notifications for the realtime messaging app. It listens for PostgreSQL notifications on the `new_message` channel and processes them.

## How It Works

1. The function connects to the PostgreSQL database using the credentials from the environment variables.
2. It checks if the `messages` table exists.
3. It sets up a listener for the `new_message` channel.
4. When a new message is inserted into the `messages` table, the `notify_new_message` trigger function sends a notification to the `new_message` channel.
5. The function receives the notification and processes it.

## Prerequisites

Before using this function, you need to:

1. Create the `messages` table using the SQL script in `sample-apps/realtime-messaging-app/db/create_messages_table.sql`.
2. Create the trigger function and trigger using the SQL script in `sample-apps/realtime-messaging-app/db/create_message_triggers.sql`.

## Usage

You can invoke this function manually via HTTP to start listening for message notifications:

```
POST /api/v1/functions/message-notifications
```

The function will return a response indicating that it's now listening for message notifications.

## Integration with the Frontend

The frontend application uses a polling mechanism to check for new messages every 2 seconds. This approach is used because:

1. It's simple and reliable.
2. It works with the existing SelfDB backend without modifications.
3. It doesn't require complex WebSocket handling.

The polling mechanism queries the database for new messages since the last poll and updates the UI accordingly.

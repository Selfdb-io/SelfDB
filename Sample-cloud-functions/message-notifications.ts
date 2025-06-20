// @ts-nocheck
// deno-lint-ignore-file

// Function metadata
export const description = "Message notifications handler for realtime messaging app";

// Define triggers for this function
export const triggers = [
  // HTTP trigger for manual execution
  {
    type: "http",
    method: ["GET", "POST"]
  },
  // Database trigger for messages table
  {
    type: "database",
    table: "messages",
    operations: ["INSERT"],
    channel: "new_message"
  }
];

// Import the PostgreSQL client
import { Client } from "https://deno.land/x/postgres@v0.17.0/mod.ts";

// The function handler
export default async function handler(req, env) {
  console.log("Message notifications handler executed");

  if (req.method === "GET") {
    return {
      success: true,
      message: "Message notifications handler",
      description: "This function handles message notifications for the realtime messaging app",
      usage: "Make a POST request to start listening for message notifications"
    };
  } else if (req.method === "POST") {
    try {
      // Create a database client
      const client = new Client({
        user: env.POSTGRES_USER || "selfdb_user",
        password: env.POSTGRES_PASSWORD || "selfdb_password",
        database: env.POSTGRES_DB || "selfdb",
        hostname: env.POSTGRES_HOST || "postgres",
        port: parseInt(env.POSTGRES_PORT || "5432")
      });

      // Connect to the database
      await client.connect();
      console.log("Connected to the database");

      // Check if the messages table exists
      const checkTableQuery = `
        SELECT EXISTS (
          SELECT FROM information_schema.tables
          WHERE table_schema = 'public'
          AND table_name = 'messages'
        );
      `;
      const tableExists = await client.queryArray(checkTableQuery);

      if (!tableExists.rows[0][0]) {
        return {
          success: false,
          message: "Messages table does not exist",
          hint: "Make sure to create the messages table first"
        };
      }

      // Check if the trigger function exists
      const checkTriggerFunctionQuery = `
        SELECT EXISTS (
          SELECT FROM pg_proc
          JOIN pg_namespace ON pg_namespace.oid = pg_proc.pronamespace
          WHERE proname = 'notify_new_message'
          AND nspname = 'public'
        );
      `;
      const triggerFunctionExists = await client.queryArray(checkTriggerFunctionQuery);

      if (!triggerFunctionExists.rows[0][0]) {
        console.log("Creating notify_new_message trigger function...");

        // Create the trigger function
        const createTriggerFunctionQuery = `
          CREATE OR REPLACE FUNCTION notify_new_message()
          RETURNS TRIGGER AS $$
          BEGIN
            PERFORM pg_notify('new_message', row_to_json(NEW)::text);
            RETURN NEW;
          END;
          $$ LANGUAGE plpgsql;
        `;
        await client.queryArray(createTriggerFunctionQuery);

        // Create the trigger
        const createTriggerQuery = `
          DROP TRIGGER IF EXISTS notify_on_new_message ON messages;
          CREATE TRIGGER notify_on_new_message
          AFTER INSERT ON messages
          FOR EACH ROW
          EXECUTE FUNCTION notify_new_message();
        `;
        await client.queryArray(createTriggerQuery);

        console.log("Trigger function and trigger created successfully");
      } else {
        console.log("Trigger function already exists");
      }

      // Set up a listener for the new_message channel
      await client.queryArray(`LISTEN new_message`);
      console.log("Listening for new_message notifications");

      // Return a response to the client
      return {
        success: true,
        message: "Now listening for message notifications",
        note: "The function is now listening for new_message notifications. When a new message is inserted into the messages table, the notify_new_message trigger will send a notification to this function."
      };
    } catch (error) {
      console.error("Error setting up message notifications:", error);
      return {
        success: false,
        message: "Failed to set up message notifications",
        error: error.message
      };
    }
  }
}

// @ts-nocheck
// deno-lint-ignore-file

// Function metadata
export const description = "Test script for database triggers";

// Define triggers for this function
export const triggers = [
  // HTTP trigger for manual execution
  {
    type: "http",
    method: ["GET", "POST"]
  }
];

// Import the PostgreSQL client
import { Client } from "https://deno.land/x/postgres@v0.17.0/mod.ts";

// The function handler
export default async function handler(req, env) {
  console.log("Test database trigger function executed");
  
  if (req.method === "GET") {
    return {
      success: true,
      message: "Test database trigger function",
      description: "This function helps test the database trigger functionality",
      usage: "Make a POST request to run the test"
    };
  } else if (req.method === "POST") {
    try {
      // Create a database client
      const client = new Client({
        user: env.POSTGRES_USER || "postgres",
        password: env.POSTGRES_PASSWORD || "postgres",
        database: env.POSTGRES_DB || "postgres",
        hostname: env.POSTGRES_HOST || "postgres",
        port: parseInt(env.POSTGRES_PORT || "5432")
      });
      
      // Connect to the database
      await client.connect();
      console.log("Connected to the database");
      
      // Check if the test table exists
      const checkTableQuery = `
        SELECT EXISTS (
          SELECT FROM information_schema.tables 
          WHERE table_schema = 'public' 
          AND table_name = 'test_triggers'
        );
      `;
      const tableExists = await client.queryArray(checkTableQuery);
      
      // Create the test table if it doesn't exist
      if (!tableExists.rows[0][0]) {
        console.log("Creating test_triggers table");
        const createTableQuery = `
          CREATE TABLE test_triggers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            value INTEGER NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
          );
        `;
        await client.queryArray(createTableQuery);
        console.log("Created test_triggers table");
      }
      
      // Create a trigger function and trigger for the test table
      console.log("Setting up trigger for test_triggers table");
      const createTriggerFunctionQuery = `
        CREATE OR REPLACE FUNCTION notify_test_triggers_changes()
        RETURNS TRIGGER AS $$
        DECLARE
          payload JSON;
        BEGIN
          IF (TG_OP = 'DELETE') THEN
            payload = json_build_object(
              'operation', TG_OP,
              'table', TG_TABLE_NAME,
              'old_data', row_to_json(OLD)
            );
          ELSE
            payload = json_build_object(
              'operation', TG_OP,
              'table', TG_TABLE_NAME,
              'data', row_to_json(NEW),
              'old_data', CASE WHEN TG_OP = 'UPDATE' THEN row_to_json(OLD) ELSE NULL END
            );
          END IF;
          
          PERFORM pg_notify('test_triggers_changes', payload::text);
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
      `;
      await client.queryArray(createTriggerFunctionQuery);
      
      // Check if the trigger exists
      const checkTriggerQuery = `
        SELECT EXISTS (
          SELECT 1 FROM pg_trigger 
          WHERE tgname = 'test_triggers_notify_trigger'
            AND tgrelid = 'test_triggers'::regclass
        );
      `;
      const triggerExists = await client.queryArray(checkTriggerQuery);
      
      // Create the trigger if it doesn't exist
      if (!triggerExists.rows[0][0]) {
        const createTriggerQuery = `
          CREATE TRIGGER test_triggers_notify_trigger
          AFTER INSERT OR UPDATE OR DELETE ON test_triggers
          FOR EACH ROW
          EXECUTE FUNCTION notify_test_triggers_changes();
        `;
        await client.queryArray(createTriggerQuery);
        console.log("Created trigger for test_triggers table");
      }
      
      // Insert a test record
      console.log("Inserting test record");
      const insertQuery = `
        INSERT INTO test_triggers (name, value)
        VALUES ($1, $2)
        RETURNING *;
      `;
      const insertResult = await client.queryObject(insertQuery, ["Test Record", Math.floor(Math.random() * 100)]);
      const insertedRecord = insertResult.rows[0];
      
      // Update the test record
      console.log("Updating test record");
      const updateQuery = `
        UPDATE test_triggers
        SET value = $1
        WHERE id = $2
        RETURNING *;
      `;
      const updateResult = await client.queryObject(updateQuery, [Math.floor(Math.random() * 100), insertedRecord.id]);
      const updatedRecord = updateResult.rows[0];
      
      // Delete the test record
      console.log("Deleting test record");
      const deleteQuery = `
        DELETE FROM test_triggers
        WHERE id = $1
        RETURNING *;
      `;
      const deleteResult = await client.queryObject(deleteQuery, [updatedRecord.id]);
      const deletedRecord = deleteResult.rows[0];
      
      // Close the database connection
      await client.end();
      
      return {
        success: true,
        message: "Database trigger test completed",
        operations: [
          {
            type: "INSERT",
            record: insertedRecord
          },
          {
            type: "UPDATE",
            record: updatedRecord
          },
          {
            type: "DELETE",
            record: deletedRecord
          }
        ],
        note: "Check the logs to see if the db-trigger-example function was triggered"
      };
    } catch (error) {
      console.error("Error testing database triggers:", error);
      return {
        success: false,
        message: "Failed to test database triggers",
        error: error.message
      };
    }
  }
}

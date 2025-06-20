// @ts-nocheck
// deno-lint-ignore-file

// Function metadata
export const description = "Handler for test_triggers table changes";

// Define triggers for this function
export const triggers = [
  // HTTP trigger for manual execution
  {
    type: "http",
    method: ["GET", "POST"]
  },
  // Database trigger - listens for changes to the test_triggers table
  {
    type: "database",
    table: "test_triggers",
    operations: ["INSERT", "UPDATE", "DELETE"],
    channel: "test_triggers_changes"
  }
];

// The function handler
export default async function handler(req, env) {
  console.log("Test triggers handler function executed");

  // Get the trigger type from headers
  const triggerType = req.headers?.get("X-Trigger-Type");
  const dbChannel = req.headers?.get("X-Database-Channel");

  // If this is a database trigger
  if (triggerType === "database" && dbChannel) {
    console.log(`Handling database notification on channel: ${dbChannel}`);

    try {
      // Get the notification payload
      const payload = await req.json();

      // Log the operation and data
      console.log(`Operation: ${payload.operation}`);
      console.log(`Table: ${payload.table}`);

      // Process based on operation type
      if (payload.operation === "INSERT") {
        console.log("New record:", payload.data);
        return {
          success: true,
          message: `Processed INSERT operation on ${payload.table}`,
          data: payload.data
        };
      } else if (payload.operation === "UPDATE") {
        console.log("Updated record:", payload.data);
        console.log("Previous state:", payload.old_data);
        return {
          success: true,
          message: `Processed UPDATE operation on ${payload.table}`,
          data: payload.data,
          old_data: payload.old_data,
          changes: getChanges(payload.data, payload.old_data)
        };
      } else if (payload.operation === "DELETE") {
        console.log("Deleted record:", payload.old_data);
        return {
          success: true,
          message: `Processed DELETE operation on ${payload.table}`,
          old_data: payload.old_data
        };
      } else {
        return {
          success: false,
          message: `Unknown operation: ${payload.operation}`
        };
      }
    } catch (error) {
      console.error("Error processing database notification:", error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  // If this is an HTTP request
  if (req.method === "GET") {
    return {
      success: true,
      message: "Test triggers handler function",
      description: "This function handles changes to the test_triggers table",
      trigger: {
        type: "database",
        table: "test_triggers",
        operations: ["INSERT", "UPDATE", "DELETE"],
        channel: "test_triggers_changes"
      },
      usage: "Run the test-db-trigger function to test this handler"
    };
  }
}

// Utility function to compare objects and find changes
function getChanges(newObj, oldObj) {
  const changes = {};

  for (const key in newObj) {
    if (JSON.stringify(newObj[key]) !== JSON.stringify(oldObj[key])) {
      changes[key] = {
        from: oldObj[key],
        to: newObj[key]
      };
    }
  }

  return changes;
}

// @ts-nocheck
// deno-lint-ignore-file

// Function metadata
export const description = "Demonstrates database trigger functionality";

// Define triggers for this function
export const triggers = [
  // HTTP trigger for manual execution
  {
    type: "http",
    method: ["GET", "POST"]
  },
  // Database trigger - listens for changes to the users table
  {
    type: "database",
    table: "users",
    operations: ["INSERT", "UPDATE", "DELETE"],
    channel: "users_changes"
  }
];

// The function handler
export default async function handler(req, env) {
  console.log("Database trigger demo function executed");
  
  // Get the trigger type from headers
  const triggerType = req.headers?.get("X-Trigger-Type");
  const dbChannel = req.headers?.get("X-Database-Channel");
  
  // If this is a database trigger
  if (triggerType === "database" && dbChannel) {
    console.log(`Handling database notification on channel: ${dbChannel}`);
    
    try {
      // Get the notification payload
      const payload = await req.json();
      
      // Process based on operation type
      if (payload.operation === "INSERT") {
        return handleInsert(payload.data);
      } else if (payload.operation === "UPDATE") {
        return handleUpdate(payload.data, payload.old_data);
      } else if (payload.operation === "DELETE") {
        return handleDelete(payload.old_data);
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
      message: "Database trigger demo function",
      trigger: {
        type: "database",
        table: "users",
        operations: ["INSERT", "UPDATE", "DELETE"],
        channel: "users_changes"
      },
      usage: "POST to /db-notify with { channel: 'users_changes', payload: { operation: 'INSERT', data: { ... } } }"
    };
  } else if (req.method === "POST") {
    try {
      // Get the request body
      const body = await req.json();
      
      // Return instructions on how to trigger a database notification
      return {
        success: true,
        message: "To trigger this function via database notification, make a POST request to /db-notify with the following body:",
        example: {
          channel: "users_changes",
          payload: {
            operation: "INSERT",
            data: {
              id: "123e4567-e89b-12d3-a456-426614174000",
              email: "user@example.com",
              username: "newuser",
              created_at: new Date().toISOString()
            }
          }
        }
      };
    } catch (error) {
      return {
        success: false,
        message: "Invalid JSON in request body"
      };
    }
  }
}

// Handler for INSERT operations
function handleInsert(data) {
  console.log("Processing INSERT operation:", data);
  
  // In a real implementation, you might:
  // - Send a welcome email
  // - Create related resources
  // - Update analytics
  
  return {
    success: true,
    message: "INSERT operation processed successfully",
    data: data,
    timestamp: new Date().toISOString()
  };
}

// Handler for UPDATE operations
function handleUpdate(data, oldData) {
  console.log("Processing UPDATE operation:", { old: oldData, new: data });
  
  // In a real implementation, you might:
  // - Send notification about profile changes
  // - Update related resources
  // - Log changes for audit
  
  return {
    success: true,
    message: "UPDATE operation processed successfully",
    changes: {
      before: oldData,
      after: data
    },
    timestamp: new Date().toISOString()
  };
}

// Handler for DELETE operations
function handleDelete(data) {
  console.log("Processing DELETE operation:", data);
  
  // In a real implementation, you might:
  // - Clean up related resources
  // - Archive data
  // - Update analytics
  
  return {
    success: true,
    message: "DELETE operation processed successfully",
    deletedData: data,
    timestamp: new Date().toISOString()
  };
}

// @ts-nocheck
// deno-lint-ignore-file

// Function metadata
export const description = "Example function demonstrating improved database trigger functionality";

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
  console.log("Database trigger example function executed");
  
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
          old_data: payload.old_data
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
      message: "Database trigger example function",
      description: "This function demonstrates the improved database trigger functionality",
      trigger: {
        type: "database",
        table: "users",
        operations: ["INSERT", "UPDATE", "DELETE"],
        channel: "users_changes"
      },
      usage: "Make changes to the users table to trigger this function automatically"
    };
  } else if (req.method === "POST") {
    try {
      // Get the request body
      const body = await req.json();
      
      // Return instructions on how to trigger a database notification manually
      return {
        success: true,
        message: "To manually trigger this function via database notification, make a POST request to /db-notify with the following body:",
        example: {
          channel: "users_changes",
          payload: {
            operation: "INSERT",
            table: "users",
            data: {
              id: "123e4567-e89b-12d3-a456-426614174000",
              email: "user@example.com",
              username: "newuser",
              created_at: new Date().toISOString()
            }
          }
        },
        note: "However, this function will be automatically triggered when changes are made to the users table"
      };
    } catch (error) {
      return {
        success: false,
        message: "Invalid JSON in request body"
      };
    }
  }
}

// Helper functions for processing different operations
function handleInsert(data) {
  // Process the inserted data
  // For example, you could send a welcome email to a new user
  return {
    success: true,
    message: "Processed new record",
    data: data
  };
}

function handleUpdate(data, oldData) {
  // Process the updated data
  // For example, you could track changes to important fields
  return {
    success: true,
    message: "Processed updated record",
    data: data,
    changes: getChanges(data, oldData)
  };
}

function handleDelete(oldData) {
  // Process the deleted data
  // For example, you could clean up related resources
  return {
    success: true,
    message: "Processed deleted record",
    data: oldData
  };
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

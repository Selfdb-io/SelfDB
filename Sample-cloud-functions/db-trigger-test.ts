// @ts-nocheck
// deno-lint-ignore-file

// Function metadata
export const description = "Test function for database triggers";

// Define triggers for this function
export const triggers = [
  // HTTP trigger for manual execution
  {
    type: "http",
    method: ["GET", "POST"]
  }
];

// The function handler
export default async function handler(req, env) {
  console.log("Database trigger test function executed");
  
  // Get the trigger type from headers
  const triggerType = req.headers?.get("X-Trigger-Type");
  const dbChannel = req.headers?.get("X-Database-Channel");
  
  // If this is a simulated database trigger
  if (triggerType === "database" && dbChannel) {
    console.log(`Handling simulated database notification on channel: ${dbChannel}`);
    
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
  
  // If this is a regular HTTP request
  if (req.method === "GET") {
    return {
      success: true,
      message: "Database trigger test function",
      description: "This function can be used to test database trigger handling",
      usage: "Send a POST request with X-Trigger-Type and X-Database-Channel headers to simulate a database trigger"
    };
  } else if (req.method === "POST") {
    try {
      // Get the request body
      const body = await req.json();
      
      // Simulate a database trigger
      console.log("Simulating database trigger with payload:", body);
      
      // Create a simulated database notification
      const simulatedPayload = {
        operation: body.operation || "INSERT",
        table: body.table || "test_table",
        data: body.data || { id: "test-id", name: "Test Record" },
        old_data: body.old_data
      };
      
      // Process the simulated notification
      if (simulatedPayload.operation === "INSERT") {
        console.log("Simulated INSERT operation");
        console.log("New record:", simulatedPayload.data);
        return {
          success: true,
          message: `Simulated INSERT operation on ${simulatedPayload.table}`,
          data: simulatedPayload.data
        };
      } else if (simulatedPayload.operation === "UPDATE") {
        console.log("Simulated UPDATE operation");
        console.log("Updated record:", simulatedPayload.data);
        console.log("Previous state:", simulatedPayload.old_data);
        return {
          success: true,
          message: `Simulated UPDATE operation on ${simulatedPayload.table}`,
          data: simulatedPayload.data,
          old_data: simulatedPayload.old_data
        };
      } else if (simulatedPayload.operation === "DELETE") {
        console.log("Simulated DELETE operation");
        console.log("Deleted record:", simulatedPayload.old_data);
        return {
          success: true,
          message: `Simulated DELETE operation on ${simulatedPayload.table}`,
          old_data: simulatedPayload.old_data
        };
      } else {
        return {
          success: false,
          message: `Unknown operation: ${simulatedPayload.operation}`
        };
      }
    } catch (error) {
      console.error("Error processing request:", error);
      return {
        success: false,
        message: "Invalid JSON in request body"
      };
    }
  }
}

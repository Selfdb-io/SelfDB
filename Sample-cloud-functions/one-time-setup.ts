// @ts-nocheck
// deno-lint-ignore-file

// Function metadata
export const description = "One-time setup function that runs only once";

// Mark this function as run-once
export const runOnce = true;

// Define triggers for this function
export const triggers = [
  // HTTP trigger for manual execution
  {
    type: "http",
    method: ["GET", "POST"]
  },
  // One-time trigger - runs once when loaded
  {
    type: "once"
  }
];

// The function handler
export default async function handler(req, env) {
  console.log("One-time setup function executed");
  
  // Get the trigger type from headers
  const triggerType = req.headers?.get("X-Trigger-Type");
  
  // If this is a one-time trigger or HTTP request
  if (triggerType === "once" || req.method === "POST") {
    console.log("Performing one-time setup tasks...");
    
    // Simulate setup tasks
    const setupTasks = [
      "Creating default configuration",
      "Setting up initial database schema",
      "Creating admin user",
      "Setting up default permissions"
    ];
    
    // In a real implementation, you would perform actual setup tasks here
    
    // Simulate task execution with delays
    const results = {};
    for (const task of setupTasks) {
      console.log(`Executing task: ${task}`);
      // Simulate task execution
      results[task] = "Completed";
    }
    
    return {
      success: true,
      message: "One-time setup completed successfully",
      tasks: results,
      timestamp: new Date().toISOString()
    };
  }
  
  // If this is a GET request, just return status
  if (req.method === "GET") {
    return {
      success: true,
      message: "One-time setup function",
      status: "This function will only run once successfully",
      note: "To manually trigger, make a POST request to this endpoint"
    };
  }
}

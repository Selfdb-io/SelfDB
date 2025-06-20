// @ts-nocheck
// deno-lint-ignore-file

// Function metadata
export const description = "A sample function demonstrating the trigger system";

// Define triggers for this function
export const triggers = [
  // HTTP trigger - responds to HTTP requests
  {
    type: "http",
    method: ["GET", "POST"] // Only allow GET and POST methods
  },
  // Schedule trigger - runs on a schedule
  {
    type: "schedule",
    cron: "*/5 * * * *", // Run every 5 minutes
    name: "sample-function-schedule"
  }
];

// The function handler
export default async function handler(req, env) {
  console.log("Sample function executed");
  
  // Check if this is a scheduled execution
  const isScheduled = req.headers?.get("X-Trigger-Type") === "schedule";
  
  if (isScheduled) {
    console.log("Running as scheduled task");
    // Do scheduled task work here
    return {
      success: true,
      message: "Scheduled execution completed",
      timestamp: new Date().toISOString(),
      executionType: "scheduled"
    };
  }
  
  // Handle HTTP request
  const url = new URL(req.url);
  const params = Object.fromEntries(url.searchParams.entries());
  
  return {
    success: true,
    message: "Sample function executed successfully",
    method: req.method,
    path: url.pathname,
    params: params,
    timestamp: new Date().toISOString(),
    executionType: "http"
  };
}

// @ts-nocheck
// deno-lint-ignore-file
// SelfDB Serverless Function Runtime
import { serve } from "https://deno.land/std@0.224.0/http/server.ts";
import { delay } from "https://deno.land/std@0.224.0/async/delay.ts";
import postgres from "https://deno.land/x/postgresjs@v3.4.5/mod.js";

// Simple EventEmitter implementation
class EventEmitter {
  #events = new Map();

  on(event, listener) {
    if (!this.#events.has(event)) {
      this.#events.set(event, []);
    }
    this.#events.get(event).push(listener);
    return this;
  }

  removeAllListeners(event) {
    if (this.#events.has(event)) {
      this.#events.delete(event);
    }
    return this;
  }

  emit(event, ...args) {
    if (!this.#events.has(event)) {
      return false;
    }
    for (const listener of this.#events.get(event)) {
      listener(...args);
    }
    return true;
  }
}

// Define trigger types
type HttpTrigger = {
  type: "http";
  method?: string | string[];
  path?: string;
};

type ScheduleTrigger = {
  type: "schedule";
  cron: string;
  name?: string;
};

type DatabaseTrigger = {
  type: "database";
  table: string;
  operations?: string[];
  channel?: string; // PostgreSQL LISTEN/NOTIFY channel
};

type EventTrigger = {
  type: "event";
  event: string;
};

type OneTimeTrigger = {
  type: "once";
  condition?: string; // Optional condition to determine if it should run
};

type Trigger = HttpTrigger | ScheduleTrigger | DatabaseTrigger | EventTrigger | OneTimeTrigger;

// Function execution status
type ExecutionStatus = {
  lastRun?: Date;
  runCount: number;
  hasCompleted: boolean;
  lastResult?: any;
  error?: string;
};

// Function metadata interface
interface FunctionMetadata {
  name: string;
  description?: string;
  triggers?: Trigger[];
  handler: Function;
  path: string;
  filePath: string;
  status: ExecutionStatus;
  runOnce?: boolean; // If true, function will only run once successfully and then be marked as completed
}

// Registry for all functions
let functionRegistry: Map<string, FunctionMetadata> = new Map();
const completedRunOnceFunctions: Set<string> = new Set();

// Event bus for custom events
const eventBus = new EventEmitter();

// Database client for LISTEN/NOTIFY
let sql: any = null;

// Map of active database listeners
const dbListeners: Map<string, boolean> = new Map();

// CORS headers to allow requests from the frontend
const corsHeaders = {
  "Access-Control-Allow-Origin": "http://localhost:3000",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, apikey",
  "Access-Control-Max-Age": "86400",
};

// Backend API client helper
const BACKEND_URL = Deno.env.get("BACKEND_URL") || "http://backend:8000/api/v1";
const ANON_KEY = Deno.env.get("ANON_KEY") || "";

async function callBackend(path, options = {}) {
  const url = path.startsWith("http") ? path : `${BACKEND_URL}${path.startsWith("/") ? path : "/" + path}`;
  const headers = new Headers(options.headers || {});
  headers.set("apikey", ANON_KEY);
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const resp = await fetch(url, { ...options, headers });
  const text = await resp.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }
  if (!resp.ok) throw new Error(`Backend error ${resp.status}: ${text}`);
  return data;
}

// Function to parse cron expression and check if it should run
function shouldRunCron(cronExpression: string, date: Date = new Date()): boolean {
  // Simple cron parser for "* * * * *" format (minute, hour, day, month, weekday)
  const parts = cronExpression.trim().split(" ");
  if (parts.length !== 5) return false;

  const minute = date.getMinutes();
  const hour = date.getHours();
  const day = date.getDate();
  const month = date.getMonth() + 1; // 1-12
  const weekday = date.getDay(); // 0-6, 0 is Sunday

  // Check each part of the cron expression
  // For simplicity, we only implement "*" (any) and direct number matching
  if (parts[0] !== "*" && parseInt(parts[0]) !== minute) return false;
  if (parts[1] !== "*" && parseInt(parts[1]) !== hour) return false;
  if (parts[2] !== "*" && parseInt(parts[2]) !== day) return false;
  if (parts[3] !== "*" && parseInt(parts[3]) !== month) return false;
  if (parts[4] !== "*" && parseInt(parts[4]) !== weekday) return false;

  return true;
}

// Function to load and register a function
async function loadFunction(filePath: string): Promise<FunctionMetadata | null> {
  try {
    console.log(`Loading function from: ${filePath}`);
    const module = await import(filePath + `?ts=${Date.now()}`);

    if (typeof module.default !== "function") {
      console.log(`Module ${filePath} does not export a default function`);
      return null;
    }

    // Extract function name from file path
    const fileName = filePath.split("/").pop() || "";
    const functionName = fileName.replace(/\.ts$/, "");
    const httpPath = `/${functionName}`;

    // Check if this function was previously completed (if runOnce)
    const initialHasCompleted = completedRunOnceFunctions.has(functionName);

    const executionStatus: ExecutionStatus = {
      runCount: 0, // Reset on load; persist if needed across full restarts
      hasCompleted: initialHasCompleted,
      lastResult: undefined, // Clear last result on reload
      error: undefined // Clear last error on reload
    };

    // Get function metadata
    const metadata: FunctionMetadata = {
      name: functionName,
      description: module.description || "",
      triggers: module.triggers || [],
      handler: module.default,
      path: httpPath,
      filePath: filePath,
      status: executionStatus, // Use status that respects previous completion for runOnce
      runOnce: module.runOnce === true
    };

    // If no triggers are defined, add default HTTP trigger
    if (!metadata.triggers || metadata.triggers.length === 0) {
      metadata.triggers = [{ type: "http" }];
    }

    // Always register the function. Execution logic will decide if it actually runs.
    functionRegistry.set(functionName, metadata);
    if (metadata.runOnce && metadata.status.hasCompleted) {
      console.log(`Registered (already completed) one-time function: ${functionName}`);
    } else {
      console.log(`Registered function: ${functionName}`);
    }

    // Set up event listeners for event triggers
    const eventTriggers = metadata.triggers.filter(t => t.type === "event") as EventTrigger[];
    eventTriggers.forEach(trigger => {
      // Remove any existing listeners to avoid duplicates
      eventBus.removeAllListeners(trigger.event);

      eventBus.on(trigger.event, async (eventData) => {
        console.log(`Event triggered: ${trigger.event} for function ${functionName}`);
        await executeEventFunction(metadata, trigger.event, eventData);
      });
      console.log(`  - Event trigger: ${trigger.event}`);
    });

    // Set up database listeners for database triggers
    const dbTriggers = metadata.triggers.filter(t => t.type === "database") as DatabaseTrigger[];
    dbTriggers.forEach(trigger => {
      const channel = trigger.channel || `${trigger.table}_changes`;
      setupDatabaseListener(channel, metadata, trigger);
      console.log(`  - Database trigger: ${trigger.table} (${trigger.operations?.join(", ") || "all operations"}) on channel ${channel}`);
    });

    // Log other trigger types concisely
    metadata.triggers.forEach(trigger => {
      if (trigger.type === "http") {
        console.log(`  - HTTP trigger: ${metadata.path}`);
      } else if (trigger.type === "schedule") {
        console.log(`  - Schedule trigger: ${(trigger as ScheduleTrigger).cron}`);
      }
      // type: "once" in triggers array is informational; runOnce property controls behavior.
      // type: "event" and "database" are logged above.
    });
    
    // If it's a runOnce function, log its one-time nature and status clearly.
    if (metadata.runOnce) {
        console.log(`  - Function configured for one-time execution${metadata.status.hasCompleted ? ' (already completed)' : ''}`);
    }

    return metadata;
  } catch (err) {
    console.error(`Error loading function ${filePath}:`, err);
    return null;
  }
}

// Function to scan and load all functions
async function scanAndLoadFunctions() {
  // completedRunOnceFunctions Set persists across calls to scanAndLoadFunctions within the same server instance.
  // Clear the main registry to reload definitions
  functionRegistry.clear();

  // Scan directory for function files
  for await (const entry of Deno.readDir(".")) {
    if (entry.isFile && entry.name.endsWith(".ts") && entry.name !== "server.ts" && entry.name !== "server.ts.new") {
      await loadFunction(`./${entry.name}`);
    }
  }

  console.log(`Loaded ${functionRegistry.size} functions`);

  // Execute all one-time functions that haven't completed yet
  const oneTimeFunctionsToExecute = [];
  for (const fn of functionRegistry.values()) {
    // Execute if it's runOnce, not in our completed Set, and its current status also shows not completed.
    if (fn.runOnce && !completedRunOnceFunctions.has(fn.name) && !fn.status.hasCompleted) {
      oneTimeFunctionsToExecute.push(fn);
    }
  }

  if (oneTimeFunctionsToExecute.length > 0) {
    console.log(`Found ${oneTimeFunctionsToExecute.length} one-time functions to execute`);

    // Execute each one-time function
    for (const fn of oneTimeFunctionsToExecute) {
      console.log(`Auto-executing one-time function: ${fn.name}`);
      try {
        await executeOneTimeFunction(fn); // This function will update completedRunOnceFunctions
      } catch (err) {
        console.error(`Error auto-executing one-time function ${fn.name}:`, err);
        // Do not add to completedRunOnceFunctions if it errors, so it might retry if server restarts
      }
    }
  }
}

// Setup database connection for LISTEN/NOTIFY
async function setupDatabaseConnection() {
  if (sql) {
    try {
      await sql.end();
    } catch (e) {
      console.error("Error closing existing database connection:", e);
    }
  }

  try {
    sql = postgres({
      user: Deno.env.get("POSTGRES_USER") || "postgres",
      password: Deno.env.get("POSTGRES_PASSWORD") || "postgres",
      database: Deno.env.get("POSTGRES_DB") || "postgres",
      host: Deno.env.get("POSTGRES_HOST") || "postgres",
      port: parseInt(Deno.env.get("POSTGRES_PORT") || "5432"),
      onnotice: (notice) => {
        console.log("PostgreSQL notice:", notice);
      }
    });

    console.log("Connected to database for LISTEN/NOTIFY");

    // Re-establish all active listeners
    for (const channel of dbListeners.keys()) {
      await setupChannelListener(channel);
    }

    console.log("Database connection ready for notifications");
    return true;
  } catch (error) {
    console.error("Failed to connect to database:", error);
    sql = null;
    return false;
  }
}

// Setup a listener for a specific channel
async function setupChannelListener(channel: string) {
  if (!sql) {
    await setupDatabaseConnection();
    if (!sql) return false;
  }

  try {
    // Use postgres.js listen functionality which creates a dedicated connection
    await sql.listen(channel, (payload) => {
      console.log(`Received notification on channel ${channel}:`, payload);
      handleDatabaseNotification(channel, payload);
    });

    dbListeners.set(channel, true);
    console.log(`Set up LISTEN on channel: ${channel}`);
    return true;
  } catch (error) {
    console.error(`Error setting up listener for channel ${channel}:`, error);
    return false;
  }
}

// Helper function to create a PostgreSQL trigger for a table
async function createDatabaseTrigger(table: string, channel: string, operations: string[] = ["INSERT", "UPDATE", "DELETE"]) {
  if (!sql) {
    const connected = await setupDatabaseConnection();
    if (!connected) {
      console.error(`Failed to create database trigger for table ${table}`);
      return false;
    }
  }

  try {
    // Check if the trigger function exists
    const functionExists = await sql`
      SELECT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = ${'notify_' + table + '_changes'}
      );
    `;

    if (!functionExists[0].exists) {
      // Create the trigger function if it doesn't exist
      await sql.unsafe(`
        CREATE OR REPLACE FUNCTION notify_${table}_changes()
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

          PERFORM pg_notify('${channel}', payload::text);
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
      `);
      console.log(`Created trigger function notify_${table}_changes`);
    }

    // Check if the trigger exists
    try {
      const triggerExists = await sql`
        SELECT EXISTS (
          SELECT 1 FROM pg_trigger
          WHERE tgname = ${table + '_notify_trigger'}
            AND tgrelid = ${table}::regclass
        );
      `;

      if (!triggerExists[0].exists) {
        // Create the trigger if it doesn't exist
        const operationsStr = operations.join(' OR ');
        await sql.unsafe(`
          CREATE TRIGGER ${table}_notify_trigger
          AFTER ${operationsStr} ON "${table}"
          FOR EACH ROW
          EXECUTE FUNCTION notify_${table}_changes();
        `);
        console.log(`Created database trigger for table ${table} on operations: ${operations.join(', ')}`);
      }
    } catch (e) {
      // Table might not exist yet, which is fine
      console.log(`Table ${table} does not exist yet, trigger will be created when table is created`);
    }

    return true;
  } catch (error) {
    console.error(`Error creating database trigger for table ${table}:`, error);
    return false;
  }
}

// Setup a database listener for a specific channel
async function setupDatabaseListener(channel: string, fn: FunctionMetadata, trigger: DatabaseTrigger) {
  if (!sql) {
    const connected = await setupDatabaseConnection();
    if (!connected) {
      console.error(`Failed to set up database listener for channel ${channel}`);
      return;
    }
  }

  try {
    if (!dbListeners.has(channel)) {
      // Set up the listener using postgres.js listen functionality
      await setupChannelListener(channel);

      // Create database trigger if table is specified
      if (trigger.table) {
        await createDatabaseTrigger(trigger.table, channel, trigger.operations);
      }
    }
  } catch (error) {
    console.error(`Error setting up database listener for channel ${channel}:`, error);
  }
}

// Handle database notifications
async function handleDatabaseNotification(channel: string, payload: string) {
  console.log(`Received notification on channel ${channel}: ${payload || ""}`);

  // Find all functions that are listening to this channel
  for (const [name, fn] of functionRegistry.entries()) {
    // If it's a runOnce function that has completed, skip it for database triggers too.
    if (fn.runOnce && (completedRunOnceFunctions.has(name) || fn.status.hasCompleted)) {
        continue;
    }

    const dbTriggers = fn.triggers?.filter(t => t.type === "database") as DatabaseTrigger[] || [];

    for (const trigger of dbTriggers) {
      const triggerChannel = trigger.channel || `${trigger.table}_changes`;

      if (triggerChannel === channel) {
        console.log(`Executing function ${name} for database notification on channel ${channel}`);

        try {
          // Parse the payload as JSON if possible
          let payloadObj = {};
          if (payload) {
            try {
              payloadObj = JSON.parse(payload);
            } catch (e) {
              payloadObj = { raw: payload };
            }
          }

          // Check if the operation matches (if specified)
          if (trigger.operations && payloadObj.hasOwnProperty("operation")) {
            if (!trigger.operations.includes(payloadObj.operation)) {
              console.log(`Skipping function ${name} because operation ${payloadObj.operation} is not in [${trigger.operations.join(", ")}]`);
              continue;
            }
          }

          // Create a mock request for the handler
          const mockRequest = {
            method: "POST",
            headers: new Headers({
              "Content-Type": "application/json",
              "X-Trigger-Type": "database",
              "X-Database-Channel": channel
            }),
            json: () => Promise.resolve(payloadObj)
          };

          // Execute the function
          const result = await fn.handler(mockRequest, { env: Deno.env.toObject(), callBackend });
          console.log(`Database trigger function ${name} completed with result:`, result);

          // Update function status
          fn.status.lastRun = new Date();
          fn.status.runCount++;
          fn.status.lastResult = result;

          // If this is a one-time function, mark as completed only if successful
          if (fn.runOnce && result && result.success === true) {
            fn.status.hasCompleted = true;
            completedRunOnceFunctions.add(fn.name); // Add to Set
            console.log(`One-time database-triggered function ${name} has completed successfully and will not run again`);
          }
        } catch (err) {
          console.error(`Error in database trigger function ${name}:`, err);
          fn.status.error = err.message;
        }
      }
    }
  }
}

// Execute a function triggered by an event
async function executeEventFunction(fn: FunctionMetadata, eventName: string, eventData: any) {
  // If it's a runOnce function, check completion status first
  if (fn.runOnce && (completedRunOnceFunctions.has(fn.name) || fn.status.hasCompleted)) {
    console.log(`Skipping one-time event function ${fn.name} as it has already completed.`);
    return { success: true, message: "One-time function already completed." };
  }

  try {
    // Create a mock request for the handler
    const mockRequest = {
      method: "POST",
      headers: new Headers({
        "Content-Type": "application/json",
        "X-Trigger-Type": "event",
        "X-Event-Name": eventName
      }),
      json: () => Promise.resolve(eventData)
    };

    // Execute the function
    const result = await fn.handler(mockRequest, { env: Deno.env.toObject(), callBackend });
    console.log(`Event function ${fn.name} completed with result:`, result);

    // Update function status
    fn.status.lastRun = new Date();
    fn.status.runCount++;
    fn.status.lastResult = result;

    // If this is a one-time function, mark as completed only if successful
    if (fn.runOnce && result && result.success === true) {
      fn.status.hasCompleted = true;
      completedRunOnceFunctions.add(fn.name); // Add to Set
      console.log(`One-time event function ${fn.name} has completed successfully and will not run again`);
    }

    return result;
  } catch (err) {
    console.error(`Error in event function ${fn.name}:`, err);
    fn.status.error = err.message;
    throw err;
  }
}

// Execute a one-time function
async function executeOneTimeFunction(fn: FunctionMetadata) {
  // Double check completion status using both the Set and the function's current status
  if (completedRunOnceFunctions.has(fn.name) || fn.status.hasCompleted) {
    console.log(`Skipping execution of one-time function ${fn.name} as it has already completed.`);
    return { success: true, message: "Already completed" }; // Provide a consistent return
  }

  try {
    // Create a mock request for the handler
    const mockRequest = {
      method: "POST",
      headers: new Headers({
        "Content-Type": "application/json",
        "X-Trigger-Type": "once"
      })
    };

    // Execute the function
    const result = await fn.handler(mockRequest, { env: Deno.env.toObject(), callBackend });
    console.log(`One-time function ${fn.name} completed with result:`, result);

    // Update function status
    fn.status.lastRun = new Date();
    fn.status.runCount++;
    fn.status.lastResult = result;

    // Only mark as completed if the function was successful
    if (result && result.success === true) {
      fn.status.hasCompleted = true;
      completedRunOnceFunctions.add(fn.name); // Add to Set
      console.log(`One-time function ${fn.name} has completed successfully and will not run again`);
    } else {
      console.log(`One-time function ${fn.name} did not complete successfully. Status: ${fn.status.hasCompleted}`);
      // Do not add to completedRunOnceFunctions if not successful, allowing potential retry on next full server start
    }

    return result;
  } catch (err) {
    console.error(`Error in one-time function ${fn.name}:`, err);
    fn.status.error = err.message; // Update status with error
    fn.status.lastRun = new Date(); // Update last run even on error
    fn.status.runCount++; // Increment run count even on error
    // Do not add to completedRunOnceFunctions on error
    throw err; // Re-throw to be caught by the caller in scanAndLoadFunctions if needed
  }
}

// Function to execute a function with timeout
async function executeFunction(fn, req, context = {}) {
  const FUNCTION_TIMEOUT = parseInt(Deno.env.get("FUNCTION_TIMEOUT") || "30000");
  return new Promise((resolve) => {
    const timeoutId = setTimeout(() => {
      console.warn(`Function execution timed out after ${FUNCTION_TIMEOUT}ms`);
      resolve(new Response(JSON.stringify({ error: "Function execution timed out" }), {
        status: 504,
        headers: { "Content-Type": "application/json" }
      }));
    }, FUNCTION_TIMEOUT);
    Promise.resolve().then(async () => {
      try {
        const result = await fn(req, context);
        clearTimeout(timeoutId);
        if (result instanceof Response) {
          resolve(result);
        } else {
          resolve(new Response(JSON.stringify(result), {
            headers: { "Content-Type": "application/json" }
          }));
        }
      } catch (error) {
        clearTimeout(timeoutId);
        console.error("Function execution error:", error);
        resolve(new Response(JSON.stringify({
          error: "Function execution failed",
          message: error.message || "Unknown error"
        }), {
          status: 500,
          headers: { "Content-Type": "application/json" }
        }));
      }
    });
  });
}

// Start the scheduler
async function startScheduler() {
  console.log("Starting scheduler...");

  // Track last run times for scheduled functions
  const lastRunTimes = new Map<string, Date>();

  while (true) {
    try {
      const now = new Date();
      let scheduledCount = 0;

      // Find all functions with schedule triggers
      for (const [name, fn] of functionRegistry.entries()) {
        // Skip one-time functions that have already completed (using the Set and status)
        if (fn.runOnce && (completedRunOnceFunctions.has(name) || fn.status.hasCompleted)) {
          continue;
        }

        const scheduleTriggers = fn.triggers?.filter(t => t.type === "schedule") as ScheduleTrigger[] || [];

        for (const trigger of scheduleTriggers) {
          const triggerKey = `${name}:${trigger.cron}`;

          try {
            if (shouldRunCron(trigger.cron, now)) {
              // Check if it's been at least 50 seconds since the last run to avoid duplicate runs
              const lastRun = lastRunTimes.get(triggerKey);
              if (!lastRun || (now.getTime() - lastRun.getTime()) >= 50000) {
                console.log(`Running scheduled function: ${name} at ${now.toISOString()}`);
                lastRunTimes.set(triggerKey, now);
                scheduledCount++;

                // Create a mock request for the handler
                const mockRequest = {
                  method: "POST",
                  headers: new Headers({
                    "Content-Type": "application/json",
                    "X-Trigger-Type": "schedule"
                  })
                };

                // Execute the function
                try {
                  const result = await fn.handler(mockRequest, { env: Deno.env.toObject(), callBackend });
                  console.log(`Scheduled function ${name} completed with result:`, result);

                  // Update function status
                  fn.status.lastRun = now;
                  fn.status.runCount++;
                  fn.status.lastResult = result;

                  // If this is a one-time function, mark as completed only if successful
                  if (fn.runOnce && result && result.success === true) {
                    fn.status.hasCompleted = true;
                    completedRunOnceFunctions.add(fn.name); // Add to Set
                    console.log(`One-time scheduled function ${name} has completed successfully and will not run again`);
                  }
                } catch (err) {
                  console.error(`Error in scheduled function ${name}:`, err);
                  fn.status.error = err.message;
                }
              }
            }
          } catch (err) {
            console.error(`Error checking schedule for ${name}:`, err);
          }
        }
      }

      if (scheduledCount === 0) {
        // Only log every minute if nothing was executed
        if (now.getSeconds() < 10) {
          console.log(`Scheduler check at ${now.toISOString()} - no functions to execute`);
        }
      }
    } catch (err) {
      console.error("Error in scheduler loop:", err);
    }

    // Check every 5 seconds
    await delay(5000);
  }
}

// HTTP handler for the server
async function handleRequest(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const path = url.pathname;

  // Handle CORS preflight requests
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: corsHeaders,
    });
  }

  // Health check endpoint
  if (path === "/health") {
    return new Response(JSON.stringify({
      status: "ok",
      functions: functionRegistry.size,
      database: sql ? "connected" : "disconnected",
      listeners: Array.from(dbListeners.keys())
    }), {
      headers: { "Content-Type": "application/json", ...corsHeaders }
    });
  }

  // List functions endpoint
  if (path === "/functions") {
    const functions = Array.from(functionRegistry.entries()).map(([name, fn]) => ({
      name,
      path: fn.path,
      description: fn.description,
      triggers: fn.triggers,
      status: {
        lastRun: fn.status.lastRun,
        runCount: fn.status.runCount,
        hasCompleted: fn.status.hasCompleted,
        error: fn.status.error
      },
      runOnce: fn.runOnce
    }));

    return new Response(JSON.stringify(functions), {
      headers: { "Content-Type": "application/json", ...corsHeaders }
    });
  }

  // Get function status endpoint
  if (path.startsWith("/function-status/")) {
    const functionName = path.replace("/function-status/", "");
    const fn = functionRegistry.get(functionName);

    if (!fn) {
      return new Response(JSON.stringify({ error: `Function '${functionName}' not found` }), {
        status: 404,
        headers: { "Content-Type": "application/json", ...corsHeaders }
      });
    }

    return new Response(JSON.stringify({
      name: fn.name,
      status: {
        lastRun: fn.status.lastRun,
        runCount: fn.status.runCount,
        hasCompleted: fn.status.hasCompleted,
        lastResult: fn.status.lastResult,
        error: fn.status.error
      },
      runOnce: fn.runOnce
    }), {
      headers: { "Content-Type": "application/json", ...corsHeaders }
    });
  }

  // Reload functions endpoint
  if (path === "/reload") {
    await scanAndLoadFunctions();
    return new Response(JSON.stringify({ success: true, count: functionRegistry.size }), {
      headers: { "Content-Type": "application/json", ...corsHeaders }
    });
  }

  // Emit event endpoint
  if (path === "/emit-event" && req.method === "POST") {
    try {
      const body = await req.json();

      if (!body.event) {
        return new Response(JSON.stringify({ error: "Missing 'event' field in request body" }), {
          status: 400,
          headers: { "Content-Type": "application/json", ...corsHeaders }
        });
      }

      const eventName = body.event;
      const eventData = body.data || {};

      // Check if any functions are listening for this event
      let hasListeners = false;
      for (const fn of functionRegistry.values()) {
        const eventTriggers = fn.triggers?.filter(t => t.type === "event") as EventTrigger[] || [];
        if (eventTriggers.some(t => t.event === eventName)) {
          hasListeners = true;
          break;
        }
      }

      // Emit the event
      eventBus.emit(eventName, eventData);

      return new Response(JSON.stringify({
        success: true,
        event: eventName,
        hasListeners: hasListeners,
        message: hasListeners ? `Event '${eventName}' emitted and will be processed by listeners` : `Event '${eventName}' emitted but no functions are listening for it`
      }), {
        headers: { "Content-Type": "application/json", ...corsHeaders }
      });
    } catch (error) {
      return new Response(JSON.stringify({ error: "Invalid JSON in request body" }), {
        status: 400,
        headers: { "Content-Type": "application/json", ...corsHeaders }
      });
    }
  }

  // Database notification endpoint
  if (path === "/db-notify" && req.method === "POST") {
    try {
      const body = await req.json();

      if (!body.channel) {
        return new Response(JSON.stringify({ error: "Missing 'channel' field in request body" }), {
          status: 400,
          headers: { "Content-Type": "application/json", ...corsHeaders }
        });
      }

      const channel = body.channel;
      const payload = body.payload ? JSON.stringify(body.payload) : "";

      // Check if we have a database connection
      if (!sql) {
        await setupDatabaseConnection();
        if (!sql) {
          return new Response(JSON.stringify({ error: "Database connection not available" }), {
            status: 500,
            headers: { "Content-Type": "application/json", ...corsHeaders }
          });
        }
      }

      // Send the notification using PostgreSQL NOTIFY
      await sql.notify(channel, payload);
      console.log(`Sent notification on channel ${channel}: ${payload}`);

      return new Response(JSON.stringify({
        success: true,
        channel: channel,
        message: `Notification sent on channel '${channel}'`
      }), {
        headers: { "Content-Type": "application/json", ...corsHeaders }
      });
    } catch (error) {
      return new Response(JSON.stringify({ error: error.message || "Error sending database notification" }), {
        status: 500,
        headers: { "Content-Type": "application/json", ...corsHeaders }
      });
    }
  }

  // Extract function name from path
  const segments = path.split("/").filter(Boolean);
  const functionName = segments[0];

  if (!functionName) {
    return new Response(JSON.stringify({ error: "Function name not specified" }), {
      status: 400,
      headers: { "Content-Type": "application/json", ...corsHeaders }
    });
  }

  // Find the function
  const fn = functionRegistry.get(functionName);

  if (!fn) {
    return new Response(JSON.stringify({ error: `Function '${functionName}' not found` }), {
      status: 404,
      headers: { "Content-Type": "application/json", ...corsHeaders }
    });
  }

  // Check if the function has an HTTP trigger
  const httpTriggers = fn.triggers?.filter(t => t.type === "http") as HttpTrigger[] || [];

  if (httpTriggers.length === 0) {
    return new Response(JSON.stringify({ error: `Function '${functionName}' does not have an HTTP trigger` }), {
      status: 400,
      headers: { "Content-Type": "application/json", ...corsHeaders }
    });
  }

  // Check if the HTTP method is allowed
  const allowedMethods = httpTriggers.flatMap(t => t.method ? (Array.isArray(t.method) ? t.method : [t.method]) : ["GET", "POST", "PUT", "DELETE", "PATCH"]);

  if (!allowedMethods.includes(req.method)) {
    return new Response(JSON.stringify({ error: `Method '${req.method}' not allowed for function '${functionName}'` }), {
      status: 405,
      headers: { "Content-Type": "application/json", ...corsHeaders }
    });
  }

  // Execute the function
  try {
    const response = await executeFunction(fn.handler, req, { env: Deno.env.toObject(), callBackend });

    // Add CORS headers to the response
    const headers = new Headers(response.headers);
    Object.entries(corsHeaders).forEach(([key, value]) => {
      headers.set(key, value);
    });

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers
    });
  } catch (err) {
    console.error(`Error executing function '${functionName}':`, err);
    return new Response(JSON.stringify({ error: "Internal server error", message: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json", ...corsHeaders }
    });
  }
}

// Initialize and start the server
async function main() {
  console.log("SelfDB Serverless Function Runtime starting...");

  // Initialize database connection for LISTEN/NOTIFY
  await setupDatabaseConnection();

  // Load all functions initially
  await scanAndLoadFunctions();

  // Start the scheduler in the background
  startScheduler();

  // Start file watcher to detect changes, with debouncing
  const watcher = Deno.watchFs(".");
  let reloadTimeout: number | undefined;
  (async () => {
    for await (const event of watcher) {
      if (event.kind === "create" || event.kind === "modify" || event.kind === "remove") {
        const affectedFiles = event.paths.filter(path =>
          path.endsWith(".ts") &&
          !path.endsWith("server.ts") && // Ignore server.ts itself
          !path.endsWith("server.ts.new") // Ignore temp files if any
        );

        if (affectedFiles.length > 0) {
          console.log(`Detected file changes in: ${affectedFiles.join(", ")}. Debouncing reload (1s)...`);
          clearTimeout(reloadTimeout);
          reloadTimeout = setTimeout(async () => {
            console.log("Debounced reload: Scanning and loading functions...");
            await scanAndLoadFunctions();
          }, 1000); // 1-second debounce
        }
      }
    }
  })();

  // Set up database reconnection logic
  setInterval(async () => {
    if (!sql) {
      console.log("Database connection lost, attempting to reconnect...");
      await setupDatabaseConnection();
    }
  }, 30000); // Check every 30 seconds

  // Start the HTTP server
  const PORT = 8090;
  console.log(`SelfDB Serverless Function Runtime listening on :${PORT}`);
  await serve(handleRequest, { port: PORT });
}

// Start the server
main().catch(err => {
  console.error("Fatal error:", err);
  Deno.exit(1);
});



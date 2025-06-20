// @ts-nocheck
// deno-lint-ignore-file

// Function metadata
export const description = "Example function demonstrating database access";

// Define triggers for this function
export const triggers = [
  // HTTP trigger
  {
    type: "http",
    method: ["GET"]
  }
];

// Import the PostgreSQL client
import { Client } from "https://deno.land/x/postgres@v0.17.0/mod.ts";

// The function handler
export default async function handler(req, env) {
  console.log("Database example function executed");
  
  // Create a database client
  const client = new Client({
    user: env.POSTGRES_USER || "postgres",
    password: env.POSTGRES_PASSWORD || "postgres",
    database: env.POSTGRES_DB || "postgres",
    hostname: env.POSTGRES_HOST || "postgres",
    port: parseInt(env.POSTGRES_PORT || "5432")
  });
  
  try {
    // Connect to the database
    await client.connect();
    console.log("Connected to the database");
    
    // Execute a query
    const result = await client.queryObject`
      SELECT 
        table_name, 
        (SELECT count(*) FROM ${client.raw(table_name)}) as row_count
      FROM 
        information_schema.tables
      WHERE 
        table_schema = 'public'
        AND table_type = 'BASE TABLE'
      ORDER BY 
        table_name
    `;
    
    // Process the results
    const tables = result.rows.map(row => ({
      name: row.table_name,
      rowCount: parseInt(row.row_count)
    }));
    
    return {
      success: true,
      message: "Database query executed successfully",
      tables: tables,
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    console.error("Database error:", error);
    return {
      success: false,
      message: "Failed to execute database query",
      error: error.message
    };
  } finally {
    // Always close the connection
    try {
      await client.end();
      console.log("Database connection closed");
    } catch (closeError) {
      console.error("Error closing database connection:", closeError);
    }
  }
}

### copy and paste this function in the SelfDB Fuctions Tabs to create 10 sample users

```typescript
// @ts-nocheck
// deno-lint-ignore-file

export const description = "Create 10 test users via the backend API (run once)";

// Mark this function to run only once by the SelfDB runtime
export const runOnce = true;

export const triggers = [
  {
    type: "http",
    method: ["POST"] // Allows manual triggering via POST
  },
  {
    type: "once" // Allows automatic triggering once by the runtime
  }
];

export default async function handler(req, env) {
  const triggerType = req.headers?.get("X-Trigger-Type");

  // Only proceed with user creation if triggered by 'once' or a manual 'POST'
  if (triggerType !== "once" && req.method !== "POST") {
    // If triggered by something else (e.g., GET request to the HTTP endpoint),
    // we just return a status message without performing the action.
    // Returning success: true here indicates the *handler* ran successfully,
    // not that the main task was done, which is appropriate if we're
    // explicitly choosing *not* to run the main task based on trigger type.
    console.log(`Function skipped: Not triggered by 'once' or 'POST'. Trigger type: ${triggerType}, Method: ${req.method}`);
    return {
      success: true,
      message: "This function is configured to run only once (automatically) or via POST (manually). Skipping execution for this trigger.",
      trigger: triggerType || req.method
    };
  }

  console.log('Starting user creation task...');
  console.log(`Trigger type: ${triggerType}`);
  console.log(`Request method: ${req.method}`);


  const baseUrl = 'http://backend:8000/api/v1';
  // Use environment variables or fallbacks
  const adminEmail = env?.DEFAULT_ADMIN_EMAIL;
  const adminPassword = env?.DEFAULT_ADMIN_PASSWORD; // Be cautious with default passwords

  console.log(`Using admin credentials: ${adminEmail} (password hidden)`);
  console.log(`Environment variables available: ${Object.keys(env || {}).join(', ')}`); // Added || {} for safety


  try {
    console.log('Attempting to log in...');
    const loginResponse = await fetch(`${baseUrl}/auth/login`, { // Fixed backticks
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        'username': adminEmail,
        'password': adminPassword,
      }),
    });

    if (!loginResponse.ok) {
      const errorText = await loginResponse.text();
      console.error(`Login failed with status ${loginResponse.status}: ${errorText}`); // Fixed backticks
      // Returning success: false will cause the 'once' trigger to retry on next restart
      return {
        success: false,
        message: `User creation failed: Login failed with status ${loginResponse.status}`, // Fixed backticks
        error: errorText
      };
    }

    console.log('Login successful');

    const loginData = await loginResponse.json();
    const access_token = loginData.access_token;

    if (!access_token) {
      console.error('No access token returned from login');
       // Returning success: false will cause the 'once' trigger to retry on next restart
      return {
        success: false,
        message: 'User creation failed: No access token returned from login',
      };
    }

    const results = [];
    console.log('Creating 10 test users...');
    for (let i = 1; i <= 10; i++) {
      const email = `testuser${i}@example.com`; // Fixed backticks
      const password = `password${i}`; // Fixed backticks

      try {
        console.log(`Attempting to create user: ${email}`);
        const createResponse = await fetch(`${baseUrl}/users`, { // Fixed backticks
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${access_token}`, // Fixed backticks
          },
          body: JSON.stringify({
            email,
            password,
            is_active: true,
            is_superuser: false,
          }),
        });

        if (createResponse.ok) {
          const user = await createResponse.json();
          console.log(`User created successfully: ${email}`);
          results.push({ email, success: true, id: user.id });
        } else {
          const errorText = await createResponse.text();
           // Log the error, but don't fail the *entire* function yet if one user fails
          console.error(`Failed to create user ${email}: ${errorText}`);
          results.push({ email, success: false, error: errorText });
        }
      } catch (err) {
         // Log the error, but don't fail the *entire* function yet if one user fetch fails
        console.error(`Exception creating user ${email}: ${err.message}`);
        results.push({ email, success: false, error: err.message });
      }

      // Add a small delay between user creations
      await new Promise(resolve => setTimeout(resolve, 500));
    }

    // Determine overall success based on whether *any* users were attempted
    const overallSuccess = results.length > 0 && results.every(r => r.success);

    return {
      // Return success: true if at least some attempts were made and none failed critically
      // Returning success: true here will mark the 'once' trigger as completed.
      success: true, // Or change to overallSuccess if you require all 10 to succeed
      message: "User creation task completed",
      created: results.filter(r => r.success).length,
      failed: results.filter(r => !r.success).length,
      details: results
    };

  } catch (error) {
    // This catches errors from login fetch or other unexpected exceptions
    console.error('An unhandled error occurred during user creation:', error);
    // Returning success: false will cause the 'once' trigger to retry on next restart
    return {
      success: false,
      message: 'User creation failed due to an unexpected error',
      error: error.message
    };
  }
}

```
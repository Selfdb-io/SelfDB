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

export default async function handler(req, context) {
  const { env, callBackend } = context;
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

  // Use environment variables or fallbacks
  const adminEmail = env?.DEFAULT_ADMIN_EMAIL;
  const adminPassword = env?.DEFAULT_ADMIN_PASSWORD;

  console.log(`Using admin credentials: ${adminEmail} (password hidden)`);
  console.log(`Environment variables available: ${Object.keys(env || {}).join(', ')}`);

  try {
    console.log('Attempting to log in...');
    const loginData = await callBackend("/auth/login", {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        'username': adminEmail,
        'password': adminPassword,
      }),
    });

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
      const email = `testuser${i}@example.com`;
      const password = `password${i}`;
      try {
        console.log(`Attempting to create user: ${email}`);
        const user = await callBackend("/users", {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${access_token}`,
          },
          body: JSON.stringify({
            email,
            password,
            is_active: true,
            is_superuser: false,
          }),
        });
          console.log(`User created successfully: ${email}`);
          results.push({ email, success: true, id: user.id });
      } catch (err) {
         // Log the error, but don't fail the *entire* function yet if one user fetch fails
        console.error(`Failed to create user ${email}: ${err.message}`);
        results.push({ email, success: false, error: err.message });
      }
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
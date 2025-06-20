// @ts-nocheck
// deno-lint-ignore-file
// Simple test function
export default async function handler(req, env) {
  console.log('Test function executed');
  
  return {
    success: true,
    message: 'Test function executed successfully',
    timestamp: new Date().toISOString(),
    env: {
      hasAdmin: !!env?.ADMIN_EMAIL,
      adminEmail: env?.ADMIN_EMAIL ? env.ADMIN_EMAIL.substring(0, 3) + '...' : 'not set'
    }
  };
}

import { defineConfig } from 'cypress';

const config = defineConfig({
  e2e: {
    // Use CYPRESS_BASE_URL env var if set, otherwise default to Docker frontend
    // Test against Docker:  npm run test:e2e (default)
    // Test against Vite dev: CYPRESS_BASE_URL=http://localhost:5173 npm run cypress
    baseUrl: process.env.CYPRESS_BASE_URL || 'http://localhost:3000',
    supportFile: 'tests/e2e/support/e2e.ts',
    specPattern: 'tests/e2e/**/*.cy.{js,jsx,ts,tsx}',
    videosFolder: 'tests/e2e/videos',
    screenshotsFolder: 'tests/e2e/screenshots',
    fixturesFolder: 'tests/e2e/fixtures',
    viewportWidth: 1280,
    viewportHeight: 720,
    video: false,
    screenshotOnRunFailure: true,
    defaultCommandTimeout: 10000,
    requestTimeout: 10000,
    responseTimeout: 10000,
    env: {
      // Test credentials from .env.dev
      adminEmail: 'admin@example.com',
      adminPassword: 'adminpassword123',
      apiUrl: 'http://localhost:8000',
    },
  },
  component: {
    devServer: {
      framework: 'react',
      bundler: 'vite',
    },
    supportFile: 'tests/e2e/support/component.ts',
    specPattern: 'src/**/*.cy.{js,jsx,ts,tsx}',
  },
});

export default config;

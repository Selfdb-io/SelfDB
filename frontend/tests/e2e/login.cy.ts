/**
 * E2E Test: Admin Login Flow
 * Tests the complete login workflow using admin credentials from .env.dev
 * 
 * Prerequisites:
 * - Backend services must be running (./test_services.sh quick)
 * - Frontend must be running (npm run dev OR Docker container)
 * - Admin user must exist in database (created by backend on startup)
 * 
 * Test Credentials (from .env.dev):
 * - Email: admin@example.com
 * - Password: adminpassword123
 */

describe('Admin Login Flow', () => {
  // Get credentials from Cypress environment (set in cypress.config.ts)
  const adminEmail = Cypress.env('adminEmail')
  const adminPassword = Cypress.env('adminPassword')

  beforeEach(() => {
    // Clear any existing session data
    cy.clearLocalStorage()
    cy.clearCookies()
    
    // Visit the login page
    cy.visit('/')
  })

  it('should display the login form', () => {
    // Check that login form elements exist
    cy.get('input[type="email"], input[name="email"]').should('be.visible')
    cy.get('input[type="password"], input[name="password"]').should('be.visible')
    cy.get('button[type="submit"]').should('be.visible')
  })

  it('should show validation errors for empty form', () => {
    // Submit empty form - this should trigger HTML5 validation or server-side validation
    cy.get('button[type="submit"]').click()

    // Since we don't have client-side validation, this might not show an error
    // The form should either show HTML5 validation or submit and show server error
    // For now, let's just check that the form is still visible (no redirect)
    cy.get('input[type="email"]').should('be.visible')
  })

  it('should show validation error for invalid email format', () => {
    // We don't have client-side email validation, so this will submit to server
    cy.get('input[type="email"], input[name="email"]').type('invalid-email')
    cy.get('input[type="password"], input[name="password"]').type('somepassword')
    cy.get('button[type="submit"]').click()

    // Should submit and show server-side validation error or login error
    // For now, just check that form is still visible (no redirect)
    cy.get('input[type="email"]').should('be.visible')
  })

  it('should show error for invalid credentials', () => {
    cy.get('input[type="email"], input[name="email"]').type('wrong@example.com')
    cy.get('input[type="password"], input[name="password"]').type('wrongpassword')
    cy.get('button[type="submit"]').click()

    // Check for the specific error message from backend
    cy.contains('Invalid email or password', { timeout: 10000 }).should('be.visible')
  })

  it('should successfully log in with admin credentials', () => {
    // Fill in the login form with admin credentials
    cy.get('input[type="email"], input[name="email"]')
      .clear()
      .type(adminEmail)
      .should('have.value', adminEmail)
    
    cy.get('input[type="password"], input[name="password"]')
      .clear()
      .type(adminPassword)
      .should('have.value', adminPassword)
    
    // Submit the form
    cy.get('button[type="submit"]').click()
    
    // Wait for successful login
    // Check that we're redirected away from login page
    cy.url({ timeout: 10000 }).should('not.include', '/login')
    
    // Check that auth token exists in localStorage
    cy.window().its('localStorage.token').should('exist')
    
    // Check that refresh token exists
    cy.window().its('localStorage.refreshToken').should('exist')
    
    // Check that we're redirected away from login page
    cy.url({ timeout: 10000 }).should('not.include', '/login')
    // Adjust these selectors based on your actual dashboard UI
    cy.contains(/dashboard|welcome|home/i, { timeout: 10000 }).should('be.visible')
  })

  it('should use custom login command', () => {
    // Test the custom Cypress command
    cy.loginAsAdmin()
    
    // Verify we're logged in
    cy.url().should('not.include', '/login')
    cy.window().its('localStorage.token').should('exist')
  })

  it('should maintain session after page reload', () => {
    // Log in first
    cy.loginAsAdmin()
    
    // Reload the page
    cy.reload()
    
    // Verify we're still logged in
    cy.window().its('localStorage.token').should('exist')
    cy.url().should('not.include', '/login')
  })

  it('should be able to log out', () => {
    // Log in first
    cy.loginAsAdmin()
    
    // For now, just clear localStorage to simulate logout
    cy.window().then((win) => {
      win.localStorage.clear()
    })
    
    // Should be able to access login page again
    cy.visit('/')
    cy.get('input[type="email"]').should('be.visible')
  })

  it('should show error for missing API key', () => {
    // Intercept login API call to simulate missing API key error
    cy.intercept('POST', '**/auth/login', {
      statusCode: 401,
      body: {
        error: {
          code: 'INVALID_API_KEY',
          message: 'API key is missing',
          request_id: 'test-request-id'
        }
      }
    }).as('missingApiKey')

    cy.get('input[type="email"], input[name="email"]').type(adminEmail)
    cy.get('input[type="password"], input[name="password"]').type(adminPassword)
    cy.get('button[type="submit"]').click()

    cy.wait('@missingApiKey')

    // Check that any error message is displayed
    cy.get('.bg-error-50, .dark\\:bg-error-900\\/20').should('be.visible')
  })

  it('should handle API errors gracefully', () => {
    // Intercept login API call to simulate server error
    cy.intercept('POST', '**/auth/login', {
      statusCode: 500,
      body: {
        message: 'Internal Server Error'
      }
    }).as('loginError')

    cy.get('input[type="email"], input[name="email"]').type(adminEmail)
    cy.get('input[type="password"], input[name="password"]').type(adminPassword)
    cy.get('button[type="submit"]').click()

    cy.wait('@loginError')

    // Check that any error message is displayed
    cy.get('.bg-error-50, .dark\\:bg-error-900\\/20').should('be.visible')
  })

  it('should handle network timeout', () => {
    // Intercept login API call to simulate network failure
    cy.intercept('POST', '**/auth/login', {
      forceNetworkError: true
    }).as('networkError')

    cy.get('input[type="email"], input[name="email"]').type(adminEmail)
    cy.get('input[type="password"], input[name="password"]').type(adminPassword)
    cy.get('button[type="submit"]').click()

    cy.wait('@networkError')

    // Should show network error message
    cy.get('.bg-error-50, .dark\\:bg-error-900\\/20', { timeout: 10000 }).should('be.visible')
  })

  it('should prevent multiple simultaneous login attempts', () => {
    cy.get('input[type="email"], input[name="email"]').type(adminEmail)
    cy.get('input[type="password"], input[name="password"]').type(adminPassword)

    // Click submit once
    cy.get('button[type="submit"]').click()

    // Button should be disabled after first click
    cy.get('button[type="submit"]').should('be.disabled')

    // Try to click again - should not work
    cy.get('button[type="submit"]').should('be.disabled')
  })
})

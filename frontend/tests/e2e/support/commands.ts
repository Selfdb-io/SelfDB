/// <reference types="cypress" />

// ***********************************************
// Custom commands for E2E testing
// ***********************************************

declare global {
  namespace Cypress {
    interface Chainable {
      /**
       * Custom command to log in programmatically
       * @example cy.login('admin@example.com', 'password123')
       */
      login(email: string, password: string): Chainable<void>
      
      /**
       * Custom command to log in with admin credentials from env
       * @example cy.loginAsAdmin()
       */
      loginAsAdmin(): Chainable<void>
      
      /**
       * Custom command to log out
       * @example cy.logout()
       */
      logout(): Chainable<void>
      
      /**
       * Custom command to check if user is logged in
       * @example cy.isLoggedIn()
       */
      isLoggedIn(): Chainable<boolean>
    }
  }
}

/**
 * Login command - fills login form and submits
 */
Cypress.Commands.add('login', (email: string, password: string) => {
  cy.visit('/')
  cy.get('input[type="email"], input[name="email"]').clear().type(email)
  cy.get('input[type="password"], input[name="password"]').clear().type(password)
  cy.get('button[type="submit"]').click()
  
  // Wait for successful login (token in localStorage)
  cy.window().its('localStorage.token').should('exist')
})

/**
 * Login as admin using credentials from Cypress env
 */
Cypress.Commands.add('loginAsAdmin', () => {
  const email = Cypress.env('adminEmail')
  const password = Cypress.env('adminPassword')
  cy.login(email, password)
})

/**
 * Logout command - clears localStorage and navigates to login
 */
Cypress.Commands.add('logout', () => {
  cy.window().then((win) => {
    win.localStorage.clear()
  })
  cy.visit('/')
})

/**
 * Check if user is logged in
 */
Cypress.Commands.add('isLoggedIn', () => {
  return cy.window().then((win) => {
    return !!win.localStorage.getItem('token')
  })
})

export {}

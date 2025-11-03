/// <reference types="cypress" />

describe('Auth: Create and Delete User', () => {
  const adminEmail = 'admin@example.com';
  const adminPassword = 'adminpassword123';
  const validUser = {
    email: 'cypressuser@example.com',
    password: 'CypressPass123!',
    firstName: 'Cypress',
    lastName: 'User'
  };
  const invalidUsers = [
    { email: 'bademail', password: 'short', firstName: '', lastName: '' }, // All invalid
    { email: '', password: 'CypressPass123!', firstName: 'Cypress', lastName: 'User' }, // Missing email
    { email: 'cypressuser2@example.com', password: 'short', firstName: 'Cypress', lastName: 'User' }, // Weak password
    { email: 'cypressuser3@example.com', password: 'CypressPass123!', firstName: '', lastName: 'User' } // Missing first name
  ];

  beforeEach(() => {
    cy.visit('http://localhost:3000/login');
    // Login via the real form
    cy.get('input[type="email"]').clear().type(adminEmail);
    cy.get('input[type="password"]').clear().type(adminPassword);
    cy.contains('button', 'Sign in').click();

    // Wait for dashboard to load and navigate to Authentication (quick action)
    cy.contains('Authentication').should('exist').click();
    // ensure we're on the Auth page
    cy.contains('Auth').should('be.visible');
  });

  it('should fail to create user with invalid email and weak password', () => {
    cy.contains('button', 'Add User').click();

    // Wait for the modal email input to appear and be enabled, then use the form nearest that input
    cy.get('input#email', { timeout: 10000 }).should('be.visible').and('not.be.disabled').clear().type('bademail');
    cy.get('input#password').should('be.visible').and('not.be.disabled').clear().type('short');
    cy.get('input#first_name').should('be.visible').and('not.be.disabled').clear();
    cy.get('input#last_name').should('be.visible').and('not.be.disabled').clear();

    // Submit using the form that contains the email input to ensure we click the modal's submit
    cy.get('input#email').closest('form').within(() => {
      cy.get('button[type="submit"]').should('not.be.disabled').click();
    });

    // Expect modal to remain open (form didn't submit due to validation)
    cy.get('input#email').should('be.visible');
  });

  it('should create a user, verify creation, delete user, and verify deletion', () => {
    cy.contains('button', 'Add User').click();

    // Wait for modal inputs and fill them
    cy.get('input#email', { timeout: 10000 }).should('be.visible').and('not.be.disabled').clear().type(validUser.email);
    cy.get('input#password').should('be.visible').and('not.be.disabled').clear().type(validUser.password);
    cy.get('input#first_name').should('be.visible').and('not.be.disabled').clear().type(validUser.firstName);
    cy.get('input#last_name').should('be.visible').and('not.be.disabled').clear().type(validUser.lastName);

    // Submit using the form nearest the email input
    cy.get('input#email').closest('form').within(() => {
      cy.get('button[type="submit"]').should('not.be.disabled').click();
    });

    // Wait for created user to appear in the UI (search by visible text)
    cy.contains(validUser.email, { timeout: 20000 }).should('exist');

    // Small delay to see the user created
    cy.wait(2000);

    // Delete user: find the button in the same container as the email
    cy.contains(validUser.email).parent().parent().find('button').click();

    // Confirm delete in confirmation dialog
    cy.contains('button', 'Delete User').should('be.visible').click();

    // Verify user no longer appears
    cy.contains(validUser.email).should('not.exist');
  });
});

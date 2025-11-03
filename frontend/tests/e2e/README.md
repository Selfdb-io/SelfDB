# Cypress E2E Testing for SelfDB Frontend

## 🎯 Purpose

End-to-end testing for the SelfDB frontend using Cypress. Tests real user workflows including authentication, navigation, and CRUD operations.

## 🚀 Quick Start

### Prerequisites

1. **Backend services running**:
   ```bash
   ./test_services.sh quick
   ```

2. **Frontend running** (choose one):
   ```bash
   # Option 1: Vite dev server
   cd frontend && npm run dev

   # Option 2: Docker container (already running if you used test_services.sh)
   # Frontend accessible at http://localhost:3000
   ```

### Running E2E Tests

```bash
cd frontend

# Open Cypress Test Runner (interactive)
npm run test:e2e:open

# Run tests in headless mode (CI)
npm run test:e2e

# Or use Cypress directly
npm run cypress
npm run cypress:headless
```

## 📝 Test Structure

```
tests/e2e/
├── support/
│   ├── e2e.ts              # Global E2E setup
│   ├── component.ts        # Component testing setup
│   └── commands.ts         # Custom Cypress commands
├── fixtures/
│   └── credentials.json    # Test data
└── login.cy.ts             # Login flow E2E test
```

## 🧪 Available Tests

### Login Flow (`login.cy.ts`)

Tests the complete authentication workflow:

- ✅ Display login form
- ✅ Validate empty form submission
- ✅ Validate email format
- ✅ Show error for invalid credentials
- ✅ Successfully log in with admin credentials
- ✅ Maintain session after page reload
- ✅ Log out functionality
- ✅ Handle API errors gracefully
- ✅ Handle network timeouts
- ✅ Prevent multiple simultaneous login attempts

**Test Credentials** (from `.env.dev`):
- Email: `admin@example.com`
- Password: `adminpassword123`

## 🛠️ Custom Commands

### `cy.login(email, password)`
Logs in with specified credentials:
```typescript
cy.login('admin@example.com', 'adminpassword123')
```

### `cy.loginAsAdmin()`
Logs in with admin credentials from Cypress env:
```typescript
cy.loginAsAdmin()
```

### `cy.logout()`
Logs out the current user:
```typescript
cy.logout()
```

### `cy.isLoggedIn()`
Checks if user is currently logged in:
```typescript
cy.isLoggedIn().then((loggedIn) => {
  if (loggedIn) {
    // User is logged in
  }
})
```

## ⚙️ Configuration

### Cypress Config (`cypress.config.ts`)

```typescript
{
  baseUrl: 'http://localhost:3000',
  env: {
    adminEmail: 'admin@example.com',
    adminPassword: 'adminpassword123',
    apiUrl: 'http://localhost:8000',
  },
  viewportWidth: 1280,
  viewportHeight: 720,
  video: false,
  screenshotOnRunFailure: true,
}
```

### Environment Variables

Tests use credentials from Cypress environment configuration, which matches `.env.dev`:
- `Cypress.env('adminEmail')` → `admin@example.com`
- `Cypress.env('adminPassword')` → `adminpassword123`

## 📊 Test Results

```bash
npm run test:e2e

Running:  login.cy.ts

  Admin Login Flow
    ✓ should display the login form (250ms)
    ✓ should show validation errors for empty form (180ms)
    ✓ should show validation error for invalid email format (200ms)
    ✓ should show error for invalid credentials (850ms)
    ✓ should successfully log in with admin credentials (1200ms)
    ✓ should use custom login command (950ms)
    ✓ should maintain session after page reload (800ms)
    ✓ should be able to log out (650ms)
    ✓ should handle API errors gracefully (450ms)
    ✓ should handle network timeout (15500ms)
    ✓ should prevent multiple simultaneous login attempts (350ms)

  11 passing (22s)
```

## 🎥 Screenshots & Videos

- **Screenshots**: Captured on test failure → `tests/e2e/screenshots/`
- **Videos**: Disabled by default (can enable in config) → `tests/e2e/videos/`

## 🐛 Debugging

### Open Cypress Test Runner
```bash
npm run cypress
```
This opens an interactive UI where you can:
- See tests running in real browser
- Use browser DevTools
- See command log with DOM snapshots
- Retry individual tests

### Common Issues

**Issue**: Tests fail with "baseUrl not accessible"  
**Solution**: Make sure frontend is running on `http://localhost:3000`

**Issue**: Login fails with "Invalid credentials"  
**Solution**: Check that admin user exists in database (backend creates it on startup)

**Issue**: Timeout errors  
**Solution**: Increase timeout in `cypress.config.ts` or check backend services are running

## 📚 Writing New E2E Tests

### Example: Testing User Management

```typescript
// tests/e2e/users.cy.ts
describe('User Management', () => {
  beforeEach(() => {
    cy.loginAsAdmin()
    cy.visit('/users')
  })

  it('should display user list', () => {
    cy.contains('Users').should('be.visible')
    cy.get('[data-testid="user-table"]').should('exist')
  })

  it('should create a new user', () => {
    cy.get('[data-testid="create-user-button"]').click()
    cy.get('input[name="email"]').type('newuser@example.com')
    cy.get('input[name="first_name"]').type('New')
    cy.get('input[name="last_name"]').type('User')
    cy.get('button[type="submit"]').click()
    
    cy.contains('User created successfully').should('be.visible')
  })
})
```

## 🎯 Best Practices

1. **Use data-testid attributes** for stable selectors
2. **Clean up test data** in `afterEach` hooks
3. **Use custom commands** for repeated actions
4. **Mock external API calls** when appropriate
5. **Test both success and error scenarios**
6. **Keep tests independent** - don't rely on test execution order

## 🔗 Resources

- [Cypress Documentation](https://docs.cypress.io/)
- [Cypress Best Practices](https://docs.cypress.io/guides/references/best-practices)
- [Cypress React Component Testing](https://docs.cypress.io/guides/component-testing/react/overview)

---

**Next Steps**: Add more E2E tests for other features (user management, storage, tables, etc.)

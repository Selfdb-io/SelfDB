# Frontend Testing Framework Setup - Quick Start Guide

## 🎉 **Setup Complete!**

All frontend testing infrastructure has been configured following TDD principles.

**Includes**: Vitest (unit/integration) + Cypress (E2E)

---

## ✅ **What's Been Created**

### **1. Environment Configuration**
- ✓ `frontend/.env.development` with dynamic WebSocket URL
- ✓ `src/utils/websocket.ts` for WS URL generation (http → ws, https → wss)

### **2. Testing Framework** 
- ✓ Vitest + React Testing Library configured
- ✓ 90%+ coverage requirement enforced
- ✓ Test directory structure established
- ✓ Example tests for reference

### **3. File Structure**
```
frontend/
├── .env.development              ← NEW: Dev environment config
├── vite.config.ts                ← UPDATED: Test configuration
├── package.json                  ← UPDATED: Test scripts & deps
├── src/
│   └── utils/
│       └── websocket.ts          ← NEW: Dynamic WS URL utility
└── tests/                        ← NEW: All tests go here
    ├── setup.ts                  ← Test environment setup
    ├── helpers/
    │   ├── test-utils.tsx        ← Custom render utilities
    │   └── mock-api.ts           ← API mocking helpers
    ├── unit/
    │   ├── components/
    │   │   └── LoginForm.test.tsx    ← Example component test
    │   ├── services/
    │   └── utils/
    │       └── websocket.test.ts     ← Example utility test
    ├── integration/
    └── e2e/
```

---

## 🚀 **Quick Start (3 Steps)**

### **Step 1: Install Dependencies**
```bash
cd frontend
npm install
```

This will install all testing dependencies:
- `vitest` - Fast test runner
- `@testing-library/react` - React component testing
- `@testing-library/jest-dom` - DOM assertions
- `@testing-library/user-event` - User interactions
- `jsdom` - Browser environment
- `@vitest/coverage-v8` - Coverage reports

### **Step 2: Verify Setup**
```bash
# Run the example tests
npm test

# Expected output:
# ✓ tests/unit/utils/websocket.test.ts (7 tests)
# ✓ tests/unit/components/LoginForm.test.tsx (7 tests)
```

### **Step 3: Start Developing**
```bash
# Terminal 1: Backend services
cd ..
./test_services.sh quick

# Terminal 2: Frontend dev server
cd frontend
npm run dev

# Terminal 3: Test watch mode
cd frontend
npm run test:watch
```

---

## 📝 **Available Test Commands**

```bash
npm test                  # Run all tests once
npm run test:watch        # Watch mode for TDD
npm run test:ui           # Visual test interface
npm run test:coverage     # Full coverage report
```

---

## 🧪 **How to Write Tests (TDD Pattern)**

### **1. Component Test Example**
```typescript
// tests/unit/components/MyComponent.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '../../helpers/test-utils';
import userEvent from '@testing-library/user-event';
import MyComponent from '@/components/MyComponent';

describe('MyComponent', () => {
  it('should render with correct text', () => {
    render(<MyComponent title="Hello" />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('should handle button click', async () => {
    const user = userEvent.setup();
    render(<MyComponent />);
    
    await user.click(screen.getByRole('button'));
    expect(screen.getByText('Clicked!')).toBeInTheDocument();
  });
});
```

### **2. Service Test Example**
```typescript
// tests/unit/services/myService.test.ts
import { describe, it, expect, vi } from 'vitest';
import { mockApiSuccess } from '../../helpers/mock-api';
import { myService } from '@/services/myService';
import axios from 'axios';

vi.mock('axios');

describe('myService', () => {
  it('should fetch data successfully', async () => {
    const mockData = { id: 1, name: 'Test' };
    axios.get.mockResolvedValue(mockApiSuccess(mockData));
    
    const result = await myService.getData();
    expect(result).toEqual(mockData);
  });
});
```

### **3. Utility Test Example**
```typescript
// tests/unit/utils/myUtil.test.ts
import { describe, it, expect } from 'vitest';
import { myUtilFunction } from '@/utils/myUtil';

describe('myUtilFunction', () => {
  it('should transform input correctly', () => {
    expect(myUtilFunction('input')).toBe('expected output');
  });
});
```

---

## 🎯 **TDD Workflow (RED-GREEN-REFACTOR)**

### **Example: Adding a New Feature**

```bash
# 1. RED: Write failing test
cat > tests/unit/components/UserList.test.tsx << 'EOF'
import { describe, it, expect } from 'vitest';
import { render, screen } from '../../helpers/test-utils';
import UserList from '@/components/UserList';

describe('UserList', () => {
  it('should display list of users', () => {
    const users = [{ id: 1, name: 'Alice' }];
    render(<UserList users={users} />);
    expect(screen.getByText('Alice')).toBeInTheDocument();
  });
});
EOF

# 2. Run test (should fail)
npm test -- UserList

# 3. GREEN: Implement minimal code
# Create src/components/UserList.tsx with minimal implementation

# 4. Run test again (should pass)
npm test -- UserList

# 5. REFACTOR: Clean up code while keeping tests green
# Improve implementation, run tests to ensure they still pass
```

---

## 📊 **Coverage Requirements**

All code must meet **90%+ coverage** for:
- ✓ Lines
- ✓ Functions  
- ✓ Branches
- ✓ Statements

```bash
# Generate coverage report
npm run test:coverage

# View HTML report
open coverage/index.html
```

---

## 🛠️ **Testing Utilities Provided**

### **Custom Render (`test-utils.tsx`)**
Automatically wraps components with:
- React Router (`BrowserRouter`)
- Auth Context (`AuthProvider`)

```typescript
import { render, screen } from '../../helpers/test-utils';
// Component is automatically wrapped with providers
```

### **API Mocking (`mock-api.ts`)**
```typescript
import { 
  mockApiSuccess, 
  mockApiError,
  mockUser,
  setupAuthStorage 
} from '../../helpers/mock-api';

// Mock successful response
axios.get.mockResolvedValue(mockApiSuccess({ data: 'test' }));

// Mock error response
axios.get.mockRejectedValue(mockApiError('Not found', 404));

// Setup auth storage
setupAuthStorage(); // Sets token and user in localStorage
```

---

## 🌐 **WebSocket URL Configuration**

WebSocket URLs are **dynamically generated** from API URL:

```typescript
import { getConfiguredWebSocketUrl } from '@/utils/websocket';

const wsUrl = getConfiguredWebSocketUrl();
// http://localhost:8000/api/v1 → ws://localhost:8000/ws
// https://api.example.com/api/v1 → wss://api.example.com/ws
```

---

## 🔧 **Environment Variables**

```bash
# frontend/.env.development
VITE_API_URL=http://localhost:8000/api/v1
VITE_API_KEY=dev_api_key_not_for_production
VITE_ENV=development
VITE_DEBUG=true
```

Access in code:
```typescript
const apiUrl = import.meta.env.VITE_API_URL;
const apiKey = import.meta.env.VITE_API_KEY;
```

---

## 📚 **Next Steps: Phase 8.2 - User Management CRUD**

Now that testing is set up, follow the **one-feature-at-a-time** approach:

1. ✅ Write test for user listing
2. ✅ Implement user listing
3. ✅ Write test for user creation
4. ✅ Implement user creation
5. ✅ Continue with update, delete, etc.

**Remember**: "If tests don't exist, the feature doesn't exist"

---

## 🐛 **Troubleshooting**

### TypeScript Errors
**Issue**: Cannot find module '@/...'  
**Solution**: Run `npm install` - path aliases will work after dependencies are installed

### Tests Not Running
**Issue**: `vitest: command not found`  
**Solution**: Make sure you're in the `frontend/` directory and ran `npm install`

### Coverage Below 90%
**Issue**: Coverage reports show < 90%  
**Solution**: Add more test cases to cover edge cases and error scenarios

---

## ✅ **Verification Checklist**

Before starting Phase 8.2:

- [ ] `npm install` completed successfully
- [ ] `npm test` runs without errors
- [ ] Example tests pass (websocket.test.ts, LoginForm.test.tsx)
- [ ] `npm run dev` starts Vite dev server on port 3000
- [ ] Backend services running (`./test_services.sh quick`)
- [ ] Can access http://localhost:3000 with backend connection

---

**🎉 You're ready to start TDD development!**

Follow PHASE8-FRONTEND-PLAN.md section 8.2 (User Management CRUD) as your next step.

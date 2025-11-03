# Frontend Development vs Docker - Port Configuration

## 🎯 **Problem Solved**

Previously, both the Vite dev server (`npm run dev`) and Docker container tried to use port 3000, causing conflicts.

## ✅ **Solution**

### **Port Separation**

| Environment | Port | Command | Purpose |
|-------------|------|---------|---------|
| **Vite Dev Server** | 5173 | `npm run dev` | Local development with HMR |
| **Docker Container** | 3000 | `./test_services.sh quick` | Production-like environment |
| **Backend API** | 8000 | (via Docker) | Backend services |

---

## 🚀 **Development Workflow**

### **Option 1: Vite Dev Server (Recommended for Development)**

```bash
# Terminal 1: Start backend services
./test_services.sh quick

# Terminal 2: Start Vite dev server
cd frontend
npm run dev

# Access at: http://localhost:5173
```

**Benefits:**
- ✅ Hot Module Replacement (HMR) - instant updates
- ✅ Fast refresh - see changes immediately
- ✅ Better error messages
- ✅ Source maps for debugging
- ✅ No Docker rebuild needed

### **Option 2: Docker Container (For Production Testing)**

```bash
# Start all services including frontend
./test_services.sh quick

# Access at: http://localhost:3000
```

**Benefits:**
- ✅ Tests production build
- ✅ Tests proxy server configuration
- ✅ Validates Docker setup
- ✅ Closer to actual deployment

---

## 🧪 **E2E Testing with Cypress**

### **Test Against Vite Dev Server (Development)**

```bash
# Terminal 1: Start backend + Vite dev
./test_services.sh quick
cd frontend && npm run dev

# Terminal 2: Run Cypress against dev server
npm run cypress:dev         # Interactive mode
npm run test:e2e:dev        # Headless mode
```

### **Test Against Docker (Production)**

```bash
# Start all services including Docker frontend
./test_services.sh quick

# Run Cypress against Docker
cd frontend
npm run cypress             # Interactive mode (port 3000)
npm run test:e2e            # Headless mode (port 3000)
```

---

## 📝 **Configuration Files**

### **vite.config.ts**
```typescript
server: {
  port: 5173, // Vite dev server
  strictPort: false, // Allow fallback if port taken
}
```

### **cypress.config.mjs**
```javascript
e2e: {
  // Use env var or default to Docker
  baseUrl: process.env.CYPRESS_BASE_URL || 'http://localhost:3000',
}
```

### **.env.development**
```bash
VITE_API_URL=http://localhost:8000/api/v1
VITE_API_KEY=dev_api_key_not_for_production
```

---

## 🎯 **Quick Reference**

```bash
# Development (Vite - port 5173)
npm run dev                          # Start dev server
npm run cypress:dev                  # Test against dev server

# Production Testing (Docker - port 3000)
./test_services.sh quick             # Start Docker
npm run cypress                      # Test against Docker

# Unit Tests (no server needed)
npm test                             # Run once
npm run test:watch                   # Watch mode
```

---

## 💡 **Pro Tips**

1. **Use Vite dev server** for everyday development (faster, HMR, better DX)
2. **Use Docker** before committing to verify production build works
3. **Run E2E tests against both** to ensure compatibility
4. **If port 5173 is taken**, Vite will automatically try 5174, 5175, etc.

---

## 🐛 **Troubleshooting**

### Issue: Port 5173 already in use
**Solution**: Vite will auto-increment to next available port (5174, 5175, etc.)

### Issue: Can't access backend API from Vite dev
**Solution**: Backend must be running. Check with `./test_services.sh test dev`

### Issue: Cypress tests fail on port 5173
**Solution**: Make sure Vite dev server is running before starting Cypress

---

**Updated**: October 1, 2025

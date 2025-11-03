# Cypress Default Configuration Update ✅

**Date**: October 1, 2025  
**Change**: Cypress now defaults to testing Vite dev server (port 5173) instead of Docker (port 3000)

---

## 🎯 **What Changed**

### **Default Behavior**
- ✅ `npm run cypress` → Now tests against Vite dev server (5173)
- ✅ `npm run test:e2e` → Now tests against Vite dev server (5173)
- ✅ All Cypress commands default to development mode
- ✅ Interactive mode by default for better debugging

### **Why This Change?**
1. **Faster Development** - Test against dev server with HMR
2. **Better Debugging** - See changes instantly without rebuild
3. **More Common Use Case** - Developers test during development, not production
4. **Can Still Test Docker** - Use `:docker` suffix when needed

---

## 📝 **Updated Commands**

### **Testing Against Vite Dev Server (Default)**
```bash
npm run cypress              # Interactive mode (port 5173) ← DEFAULT
npm run cypress:headless     # Headless mode (port 5173)
npm run test:e2e             # Headless mode (port 5173)
npm run test:e2e:open        # Interactive mode (port 5173)
```

### **Testing Against Docker (When Needed)**
```bash
npm run cypress:docker       # Interactive mode (port 3000)
npm run test:e2e:docker      # Headless mode (port 3000)
```

---

## 🚀 **Typical Workflow**

### **Development (Most Common)**
```bash
# Terminal 1: Start backend
./test_services.sh quick

# Terminal 2: Start Vite dev server
cd frontend
npm run dev

# Terminal 3: Run Cypress (interactive)
npm run cypress

# Cypress opens → Select "E2E Testing" → Choose browser → Click "login.cy.ts"
# Watch tests run in real-time! 🎬
```

### **Pre-Deployment Validation**
```bash
# Test against Docker build before pushing
./test_services.sh quick
cd frontend
npm run cypress:docker
```

---

## 📊 **Script Reference**

| Command | Mode | Target | Use Case |
|---------|------|--------|----------|
| `npm run cypress` | Interactive | Vite (5173) | **Daily development** |
| `npm run cypress:headless` | Headless | Vite (5173) | CI/CD for dev |
| `npm run cypress:docker` | Interactive | Docker (3000) | Pre-deployment check |
| `npm run test:e2e` | Headless | Vite (5173) | Quick test run |
| `npm run test:e2e:docker` | Headless | Docker (3000) | CI/CD for prod |

---

## ✅ **Benefits**

1. **Faster Feedback Loop** - No Docker rebuild needed
2. **Better Error Messages** - Source maps available
3. **Hot Reload** - Fix code and re-run tests instantly
4. **Interactive by Default** - See what's happening
5. **Still Can Test Production** - Use `:docker` suffix

---

## 🎬 **What You'll See**

When you run `npm run cypress`:

1. **Cypress Launchpad Opens**
2. Click "E2E Testing"
3. Choose browser (Chrome recommended)
4. Click "login.cy.ts"
5. **Watch tests run in real browser!**
   - See form fields fill automatically
   - Watch navigation happen
   - See success/failure in real-time
   - Click commands to time-travel through test

---

## 💡 **Pro Tips**

- **During Development**: Always use default commands (test against Vite)
- **Before Committing**: Run `npm run cypress:docker` to validate production build
- **Debugging**: Interactive mode shows you exactly what Cypress is doing
- **Fast Iteration**: Change code → Save → Tests auto-reload in Cypress

---

## 🐛 **Troubleshooting**

### Issue: Tests fail on port 5173
**Solution**: Make sure Vite dev server is running: `npm run dev`

### Issue: CORS errors
**Solution**: Backend CORS now includes 5173: `ALLOWED_CORS=http://localhost:3000,http://localhost:5173,http://localhost:5174,http://localhost:8000`

### Issue: Want to test Docker
**Solution**: Use `npm run cypress:docker` instead

---

## 🎉 **Ready!**

Just run:
```bash
npm run cypress
```

And watch your tests run in a real browser! 🚀

---

**Updated**: October 1, 2025  
**Default Target**: Vite Dev Server (http://localhost:5173)

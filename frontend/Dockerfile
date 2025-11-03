# --- Stage 1: Build ---
ARG APP_VERSION=""

FROM node:20-alpine AS build
ARG APP_VERSION
ENV VITE_APP_VERSION=${APP_VERSION}

WORKDIR /app

# Copy package files first for caching
COPY package*.json ./
RUN npm install

# Copy application source
COPY . .

# Build React application
RUN npm run build

# --- Stage 2: Serve ---
FROM nginx:1.27-alpine-slim
ARG APP_VERSION
ENV SELFDB_BUILD_VERSION=${APP_VERSION}

# Copy built React app from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration template
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Expose port 80 (nginx default)
EXPOSE 80

# nginx will automatically substitute environment variables in .template files
# and start in the foreground
CMD ["nginx", "-g", "daemon off;"]
# --- Stage 1: Build ---
# Use an official Node.js runtime as the build environment
FROM node:slim AS build

# Set the working directory inside the build stage container
WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock)
# Copy these first to leverage Docker layer caching for dependencies
COPY package*.json ./

# Install dependencies using npm install
RUN npm install

# Copy the rest of the application source code
COPY . .

# Build the React application for production.
# This creates optimized static files in the /app/dist directory.
RUN npm run build

# --- Stage 2: Serve ---
# Use an official Nginx image based on Alpine Linux for a small footprint
FROM nginx:1.27-alpine-slim

# Copy the static build output from the 'build' stage to Nginx's web root directory
COPY --from=build /app/dist /usr/share/nginx/html

# Copy the custom Nginx configuration file tailored for production
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 (standard HTTP port Nginx listens on by default)
EXPOSE 80

# Command to start Nginx in the foreground
# Keeps the container running
CMD ["nginx", "-g", "daemon off;"]

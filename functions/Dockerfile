FROM denoland/deno:2.0.0

WORKDIR /app

# Copy the server file
COPY server.ts .

# Cache dependencies (if we had any)
# RUN deno cache server.ts

# Run the server (port from environment)
CMD ["run", "--allow-net", "--allow-env", "--allow-read", "server.ts"]
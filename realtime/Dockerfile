FROM elixir:1.17.1-alpine

WORKDIR /app

# Install curl for health checks
RUN apk add --no-cache curl

# Install Hex and Rebar
RUN mix local.hex --force && mix local.rebar --force

# Copy mix files
COPY mix.exs ./
RUN mix deps.get --only prod
RUN mix deps.compile

# Copy application
COPY . .

# Compile
RUN mix compile

# Expose port
EXPOSE 4000

CMD ["mix", "run", "--no-halt"]

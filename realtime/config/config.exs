import Config

config :realtime, Realtime.Endpoint,
  url: [host: "localhost"],
  http: [port: String.to_integer(System.get_env("PORT", "4000")), ip: {0, 0, 0, 0}],
  secret_key_base: System.get_env("SECRET_KEY_BASE"),
  render_errors: [view: Realtime.ErrorView, accepts: ~w(json)],
  pubsub_server: Realtime.PubSub

# Configure the HTTP server
config :realtime, Realtime.Endpoint,
  server: true

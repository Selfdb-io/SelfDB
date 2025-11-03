defmodule Realtime.Endpoint do
  use Phoenix.Endpoint, otp_app: :realtime

  socket "/socket", Realtime.UserSocket,
    websocket: true,
    longpoll: false

  plug Plug.RequestId
  plug Plug.Telemetry, event_prefix: [:phoenix, :endpoint]
  plug Plug.Parsers, parsers: [:json], json_decoder: Jason
  plug Realtime.Router
end

defmodule Realtime.Router do
  use Plug.Router

  plug Plug.Parsers, parsers: [:json], json_decoder: Jason
  plug :match
  plug :dispatch

  get "/health" do
    send_resp(conn, 200, Jason.encode!(%{status: "ok"}))
  end

  post "/api/broadcast" do
    # Receive from Python listener, broadcast to WebSocket clients
    IO.puts("Received body: #{inspect(conn.body_params)}")
    
    case conn.body_params do
      %{"channel" => channel, "payload" => payload} ->
        IO.puts("Broadcasting to channel: #{channel}")
        Phoenix.PubSub.broadcast(
          Realtime.PubSub,
          channel,
          {:broadcast, payload}
        )
        send_resp(conn, 200, "OK")
      _ ->
        IO.puts("Invalid request format")
        send_resp(conn, 400, Jason.encode!(%{error: "Invalid request format"}))
    end
  end

  match _ do
    send_resp(conn, 404, "Not found")
  end
end

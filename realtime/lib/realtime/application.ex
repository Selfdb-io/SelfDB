defmodule Realtime.Application do
  use Application

  def start(_type, _args) do
    children = [
      {Phoenix.PubSub, name: Realtime.PubSub},
      Realtime.Endpoint
    ]

    opts = [strategy: :one_for_one, name: Realtime.Supervisor]
    Supervisor.start_link(children, opts)
  end
end

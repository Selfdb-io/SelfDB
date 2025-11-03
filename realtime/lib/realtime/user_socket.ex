defmodule Realtime.UserSocket do
  use Phoenix.Socket

  # Define channels for all the topics the frontend subscribes to
  channel "users_events", Realtime.GenericChannel
  channel "tables_events", Realtime.GenericChannel
  channel "buckets_events", Realtime.GenericChannel
  channel "files_events", Realtime.GenericChannel
  channel "functions_events", Realtime.GenericChannel
  channel "webhooks_events", Realtime.GenericChannel
  channel "webhook_deliveries_events", Realtime.GenericChannel
  channel "user:*", Realtime.GenericChannel

  def connect(_params, socket, _connect_info) do
    {:ok, socket}
  end

  def id(_socket), do: nil
end

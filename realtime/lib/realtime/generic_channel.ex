defmodule Realtime.GenericChannel do
  use Phoenix.Channel

  def join(topic, _payload, socket) do
    IO.puts("Client joined channel: #{topic}")
    {:ok, socket}
  end

  def handle_in("ping", _payload, socket) do
    {:reply, {:ok, %{message: "pong"}}, socket}
  end

  def handle_in(_event, _payload, socket) do
    {:noreply, socket}
  end

  # Handle broadcasts from PubSub
  def handle_info({:broadcast, payload}, socket) do
    IO.puts("Broadcasting to client on #{socket.topic}: #{payload}")
    push(socket, "broadcast", %{payload: payload})
    {:noreply, socket}
  end

  def handle_info(_msg, socket) do
    {:noreply, socket}
  end
end

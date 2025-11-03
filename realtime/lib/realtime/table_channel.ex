defmodule Realtime.TableChannel do
  use Phoenix.Channel

  def join("table:" <> table_name, _payload, socket) do
    Phoenix.PubSub.subscribe(Realtime.PubSub, "#{table_name}_events")
    {:ok, socket}
  end

  def handle_info({:broadcast, payload}, socket) do
    push(socket, "change", Jason.decode!(payload))
    {:noreply, socket}
  end
end

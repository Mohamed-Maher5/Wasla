// This file renders the ticket list page for the Wasla frontend.
// It helps support users scan customer issues and choose what needs attention.

import { useEffect, useState } from "react";
import ChatPanel from "../components/ChatPanel";
import TicketCard from "../components/TicketCard";
import { getTickets } from "../api";
import "./TicketList.css";

function TicketList({ token, user, title = "Tickets", onTicketClick }) {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadTickets() {
      try {
        const data = await getTickets(token);
        setTickets(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadTickets();
  }, [token]);

  if (loading) {
    return <p>Loading tickets...</p>;
  }

  if (error) {
    return <p>Error: {error}</p>;
  }

  return (
    <div className={`ticket-list-page ${user?.role === "agent" ? "agent-workspace" : ""}`}>
      <div className="ticket-list-main">
        <h1 className="ticket-list-title">{title}</h1>

        <div className="ticket-list">
          {tickets.length === 0 && (
            <p>No tickets available for this role.</p>
          )}

          {tickets.map((ticket) => (
            <TicketCard
              key={ticket.id}
              ticket={ticket}
              onClick={() => onTicketClick(ticket.id)}
            />
          ))}
        </div>
      </div>

      {user?.role === "agent" && <ChatPanel />}
    </div>
  );
}

export default TicketList;

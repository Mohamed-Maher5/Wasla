// This file renders the ticket list page for the Wasla frontend.
// It helps support users scan customer issues and choose what needs attention.

import { useEffect, useState } from "react";
import TicketCard from "../components/TicketCard";
import { getTickets } from "../api";
import "./TicketList.css";

function TicketList({ onTicketClick }) {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadTickets() {
      try {
        const data = await getTickets();
        setTickets(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadTickets();
  }, []);

  if (loading) {
    return <p>Loading tickets...</p>;
  }

  if (error) {
    return <p>Error: {error}</p>;
  }

  return (
    <div className="ticket-list-page">
      <h1 className="ticket-list-title">Tickets</h1>
  
      <div className="ticket-list">
        {tickets.map((ticket) => (
          <TicketCard
            key={ticket.id}
            ticket={ticket}
            onClick={() => onTicketClick(ticket.id)}
          />
        ))}
      </div>
    </div>
  );}

export default TicketList;
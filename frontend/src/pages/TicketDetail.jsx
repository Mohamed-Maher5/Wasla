// This file renders the ticket detail page for the Wasla frontend.
// It gives support users the focused workspace for one customer issue.

import { useEffect, useState } from "react";
import { getTicket } from "../api";
import "./TicketDetail.css";

import CallButton from "../components/CallButton";
import ResolveButtons from "../components/ResolveButtons";
import ChatPanel from "../components/ChatPanel";

function TicketDetail({ ticketId, onBack }) {
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadTicket() {
      try {
        const data = await getTicket(ticketId);
        setTicket(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadTicket();
  }, [ticketId]);

  if (loading) {
    return <p>Loading ticket...</p>;
  }

  if (error) {
    return <p>Error: {error}</p>;
  }

  return (
    <div className="ticket-list-page">
      <button className="back-button" onClick={onBack}>
        Back to Tickets
      </button>

      <div className="detail-card">
        <h1>Ticket Details</h1>

        <div className="detail-row">
          <strong>Customer:</strong>
          <div>{ticket.customer_name}</div>
        </div>

        <div className="detail-row">
          <strong>Phone:</strong>
          <div>{ticket.customer_phone}</div>
        </div>

        <div className="detail-row">
          <strong>Problem:</strong>
          <div>{ticket.problem_description}</div>
        </div>

        <div className="detail-row">
          <strong>Status:</strong>
          <div>{ticket.status}</div>
        </div>

        <div className="detail-row">
          <strong>Department ID:</strong>
          <div>{ticket.department_id}</div>
        </div>

        <div className="detail-row">
          <strong>Assigned Agent ID:</strong>
          <div>{ticket.assigned_agent_id}</div>
        </div>

        <div className="detail-row">
          <strong>Created At:</strong>
          <div>{ticket.created_at}</div>
        </div>

        <CallButton ticketId={ticket.id} />

        <ResolveButtons
          ticketId={ticket.id}
          onStatusChange={(status) => {
            setTicket((currentTicket) => ({
              ...currentTicket,
              status,
            }));
          }}
        />

        <ChatPanel />
      </div>
    </div>
  );
}

export default TicketDetail;
// This file renders the ticket detail page for the Wasla frontend.
// It gives support users the focused workspace for one customer issue.

import { useEffect, useState } from "react";
import { getTicket } from "../api";
import "./TicketDetail.css";

import CallButton from "../components/CallButton";
import ResolveButtons from "../components/ResolveButtons";
import ChatPanel from "../components/ChatPanel";

function TicketDetail({ ticketId, token, user, onBack }) {
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadTicket() {
      try {
        const data = await getTicket(ticketId, token);
        setTicket(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadTicket();
  }, [ticketId, token]);

  if (loading) {
    return <p>Loading ticket...</p>;
  }

  if (error) {
    return <p>Error: {error}</p>;
  }

  return (
    <div className="ticket-list-page agent-detail-workspace">
      <div className="ticket-detail-main">
        <button className="back-button" onClick={onBack}>
          Back to Tickets
        </button>

        <div className="detail-card">
          <h1>Ticket Details</h1>

          <div className="detail-row">
            <strong>Customer:</strong>
            <div>{ticket.client_name}</div>
          </div>

          <div className="detail-row">
            <strong>Phone:</strong>
            <div>{ticket.client_phone_number}</div>
          </div>

          <div className="detail-row">
            <strong>Problem:</strong>
            <div>{ticket.description}</div>
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
            <strong>Assigned To:</strong>
            <div>{ticket.assigned_to}</div>
          </div>

          <div className="detail-row">
            <strong>Created At:</strong>
            <div>{ticket.created_at}</div>
          </div>

          <CallButton ticketId={ticket.id} token={token} />

          <ResolveButtons
            ticketId={ticket.id}
            token={token}
            onStatusChange={(status) => {
              setTicket((currentTicket) => ({
                ...currentTicket,
                status,
              }));
            }}
          />
        </div>
      </div>

      <ChatPanel />
    </div>
  );
}

export default TicketDetail;

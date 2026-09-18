import { useState } from "react";
import { resolveTicket, unresolveTicket } from "../api";
import CallButton from "./CallButton";
import "./TicketCard.css";

function TicketCard({ ticket, token, onStatusChange }) {
  const [status, setStatus] = useState(ticket.status);
  const [callCount, setCallCount] = useState(ticket.call_count ?? 0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(false);

  const isResolved = status === "resolved";

  async function handleStatusChange(nextStatus) {
    setLoading(true);
    setError("");

    try {
      const result =
        nextStatus === "resolved"
          ? await resolveTicket(ticket.id, token)
          : await unresolveTicket(ticket.id, token);

      setStatus(result.status);
      onStatusChange?.(ticket.id, result.status);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCallFinished(newStatus) {
    if (newStatus === status) return;

    setLoading(true);
    try {
      const result =
        newStatus === "resolved"
          ? await resolveTicket(ticket.id, token)
          : await unresolveTicket(ticket.id, token);

      setStatus(result.status);
      onStatusChange?.(ticket.id, result.status);
    } catch {
      // call result message explains the outcome
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className={`ticket-card ${expanded ? "is-expanded" : ""}`}
      onClick={() => setExpanded((prev) => !prev)}
    >
      {/* Call count badge — top left */}
      <div className="ticket-call-count-badge">
        <svg
          viewBox="0 0 24 24"
          width="24"
          height="24"
          fill="none"
          stroke="#228B22"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
        </svg>
        <span className="ticket-call-count-number">{callCount}</span>
      </div>

      {/* Ticket info — always visible */}
      <div className="ticket-card-fields">
        <p className="ticket-field">
          <span className="ticket-field-label">اسم العميل: </span>
          {ticket.client_name}
        </p>
        <p className="ticket-field">
          <span className="ticket-field-label">رقم العميل: </span>
          {ticket.client_phone_number}
        </p>
        <p className="ticket-field ticket-field-desc">
          <span className="ticket-field-label">وصف المشكلة: </span>
          {ticket.description}
        </p>
      </div>

      {/* Status buttons — after description */}
      <div
        className="ticket-status-actions"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          className={`ticket-status-btn resolved ${isResolved ? "is-active" : "is-inactive"}`}
          onClick={() => handleStatusChange("resolved")}
          disabled={loading}
        >
          محلولة
        </button>
        <button
          type="button"
          className={`ticket-status-btn unresolved ${isResolved ? "is-inactive" : "is-active"}`}
          onClick={() => handleStatusChange("unresolved")}
          disabled={loading}
        >
          غير محلولة
        </button>
      </div>

      {error && <p className="ticket-status-error">خطأ: {error}</p>}

      {/* Call button — expandable, only on click */}
      <div
        className="ticket-card-details"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="ticket-card-details-inner">
          <CallButton
            ticketId={ticket.id}
            token={token}
            disabled={isResolved}
            onCallFinished={handleCallFinished}
            initialCallCount={callCount}
            onCallCountChange={setCallCount}
          />
        </div>
      </div>
    </div>
  );
}

export default TicketCard;

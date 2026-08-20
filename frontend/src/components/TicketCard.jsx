// This file renders a ticket summary card for the agent ticket list.
// Clicking the card expands it in place to reveal the problem description
// and the call action, without leaving the page.

import { useState } from "react";
import { resolveTicket, unresolveTicket } from "../api";
import CallButton from "./CallButton";
import "./TicketCard.css";

function TicketCard({ ticket, token, onStatusChange }) {
  const [status, setStatus] = useState(ticket.status);
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
    if (newStatus === status) {
      return;
    }

    setLoading(true);

    try {
      const result =
        newStatus === "resolved"
          ? await resolveTicket(ticket.id, token)
          : await unresolveTicket(ticket.id, token);

      setStatus(result.status);
      onStatusChange?.(ticket.id, result.status);
    } catch {
      // status stays as it was; the call result message explains the outcome
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className={`ticket-card ${expanded ? "is-expanded" : ""}`}
      onClick={() => setExpanded((prev) => !prev)}
    >
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

      <div
        className="ticket-card-details"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="ticket-card-details-inner">
          <CallButton
            ticketId={ticket.id}
            token={token}
            onCallFinished={handleCallFinished}
          />
        </div>
      </div>

      <div
        className="ticket-status-actions"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          className={`ticket-status-btn resolved ${
            isResolved ? "is-active" : "is-inactive"
          }`}
          onClick={() => handleStatusChange("resolved")}
          disabled={loading}
        >
          محلولة
        </button>

        <button
          type="button"
          className={`ticket-status-btn unresolved ${
            isResolved ? "is-inactive" : "is-active"
          }`}
          onClick={() => handleStatusChange("unresolved")}
          disabled={loading}
        >
          غير محلولة
        </button>
      </div>

      {error && <p className="ticket-status-error">خطأ: {error}</p>}
    </div>
  );
}

export default TicketCard;
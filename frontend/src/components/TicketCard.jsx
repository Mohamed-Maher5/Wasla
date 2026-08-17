// This file renders a reusable ticket summary for the Wasla frontend.
// It helps ticket pages present customer issues in a compact, consistent way.

import "./TicketCard.css";
function TicketCard({ ticket, onClick }) {
  return (
    <div className="ticket-card" onClick={onClick}>
      <h2>{ticket.customer_name}</h2>

      <p className="ticket-problem">
        {ticket.problem_description}
      </p>

      <span
        className={`status ${
          ticket.status === "resolved"
            ? "status-resolved"
            : "status-unresolved"
        }`}
      >
        {ticket.status}
      </span>
    </div>
  );
}

export default TicketCard;
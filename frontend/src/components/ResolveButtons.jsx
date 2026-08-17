// This file renders ticket resolution controls for the Wasla frontend.
// It lets support users mark whether a customer issue is resolved or still open.


import { useState } from "react";
import { resolveTicket, unresolveTicket } from "../api";
import "./ResolveButtons.css";

function ResolveButtons({ ticketId, token, onStatusChange }) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function handleResolve() {
    setLoading(true);
    setMessage("");

    try {
      const result = await resolveTicket(ticketId, token);

      setMessage("تم تحديث حالة التذكرة إلى محلولة.");

      if (onStatusChange) {
        onStatusChange(result.status);
      }
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleUnresolve() {
    setLoading(true);
    setMessage("");

    try {
      const result = await unresolveTicket(ticketId, token);

      setMessage("تم تحديث حالة التذكرة إلى غير محلولة.");

      if (onStatusChange) {
        onStatusChange(result.status);
      }
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="resolve-section">
      <div className="resolve-buttons">
        <button
          className="resolve-button resolve"
          onClick={handleResolve}
          disabled={loading}
        >
          {loading ? "جاري التحديث..." : "Mark Resolved"}
        </button>

        <button
          className="resolve-button unresolve"
          onClick={handleUnresolve}
          disabled={loading}
        >
          {loading ? "جاري التحديث..." : "Mark Not Resolved"}
        </button>
      </div>

      {message && <p className="resolve-message">{message}</p>}
    </div>
  );
}

export default ResolveButtons;

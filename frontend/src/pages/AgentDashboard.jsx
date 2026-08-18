import { useEffect, useState } from "react";
import ChatPanel from "../components/ChatPanel";
import TicketCard from "../components/TicketCard";
import { getTickets } from "../api";
import "./AgentDashboard.css";

function AgentDashboard({ token, user, onTicketClick }) {
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

  return (
    <div className="agent-dashboard">
      <header className="dashboard-header">
        <div>
          <p className="dashboard-eyebrow">Wasla</p>
          <h1>لوحة تحكم الـAgent</h1>
          <p className="dashboard-subtitle">
            متابعة التذاكر المسندة إليك
          </p>
        </div>

        <div className="dashboard-role">
          Agent
        </div>
      </header>

      <div className="agent-workspace">
        <div className="agent-chat-column">
          <ChatPanel token={token} user={user} />
        </div>

        <div className="agent-tickets-column">
          <h2 className="ticket-list-title">التذاكر المسندة إليّ</h2>

          {loading && <p className="agent-loading-text">جاري تحميل التذاكر...</p>}
          {error && <p className="agent-error-text">خطأ: {error}</p>}

          {!loading && !error && tickets.length === 0 && (
            <p className="agent-empty-text">لا توجد تذاكر مسندة إليك.</p>
          )}

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
      </div>
    </div>
  );
}

export default AgentDashboard;

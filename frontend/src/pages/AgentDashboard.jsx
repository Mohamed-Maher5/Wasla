// This file renders the Agent dashboard for the Wasla frontend.
// The Agent manages their assigned tickets and chats with the Wasla assistant.

import { useEffect, useMemo, useState } from "react";
import ChatPanel from "../components/ChatPanel";
import TicketCard from "../components/TicketCard";
import DashboardHeader from "./DashboardHeader";
import { getDepartments, getTickets } from "../api";
import "./AgentDashboard.css";

function AgentDashboard({ token, user, onLogout }) {
  const [tickets, setTickets] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const department = useMemo(
    () => departments.find((d) => d.id === user?.department_id) || null,
    [departments, user?.department_id],
  );

  useEffect(() => {
    async function loadTickets() {
      try {
        const [ticketData, departmentData] = await Promise.all([
          getTickets(token),
          getDepartments(token),
        ]);
        setTickets(ticketData);
        setDepartments(departmentData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadTickets();
  }, [token]);

  function handleStatusChange(ticketId, newStatus) {
    setTickets((currentTickets) =>
      currentTickets.map((ticket) =>
        ticket.id === ticketId ? { ...ticket, status: newStatus } : ticket,
      ),
    );
  }

  return (
    <div className="agent-dashboard">
      <DashboardHeader
        user={user}
        onLogout={onLogout}
        subtitle={department ? `قسم الـ ${department.name}` : ""}
      />

      <div className="agent-workspace">
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
                token={token}
                onStatusChange={handleStatusChange}
              />
            ))}
          </div>
        </div>

        <div className="agent-chat-column">
          <ChatPanel token={token} user={user} fullWidth />
        </div>
      </div>
    </div>
  );
}

export default AgentDashboard;
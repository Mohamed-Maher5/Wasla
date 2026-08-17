// This file renders the Admin dashboard for the Wasla frontend.
// The Admin is responsible for one department and its support operations.

import { useEffect, useMemo, useState } from "react";
import {
  createTicket,
  createUser,
  getTickets,
  getUsers,
} from "../api";
import "./AdminDashboard.css";

const initialAgentForm = {
  name: "",
  email: "",
  password: "",
};

const initialTicketForm = {
  client_name: "",
  client_phone_number: "",
  description: "",
  assigned_to: "",
};

function AdminDashboard({ token, user, onNavigate, onTicketClick }) {
  const [agents, setAgents] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [agentForm, setAgentForm] = useState(initialAgentForm);
  const [ticketForm, setTicketForm] = useState(initialTicketForm);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const openCount = useMemo(
    () => tickets.filter((t) => t.status === "unresolved").length,
    [tickets],
  );
  const resolvedCount = useMemo(
    () => tickets.filter((t) => t.status === "resolved").length,
    [tickets],
  );

  useEffect(() => {
    async function loadData() {
      try {
        const [ticketData, userData] = await Promise.all([
          getTickets(token),
          getUsers(token),
        ]);
        setTickets(ticketData);
        setAgents(userData.filter((u) => u.role === "agent" && u.department_id === user?.department_id));
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [token, user?.department_id]);

  async function handleAgentSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    try {
      const created = await createUser(
        {
          ...agentForm,
          role: "agent",
          department_id: user.department_id,
        },
        token,
      );
      setAgents((prev) => [...prev, created]);
      setAgentForm(initialAgentForm);
      setMessage("Agent created.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleTicketSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    try {
      const ticket = await createTicket(
        {
          ...ticketForm,
          assigned_to: Number(ticketForm.assigned_to),
          department_id: user.department_id,
        },
        token,
      );
      setTickets((prev) => [ticket, ...prev]);
      setTicketForm(initialTicketForm);
      setMessage("Ticket created.");
    } catch (err) {
      setError(err.message);
    }
  }

  function updateAgentForm(field, value) {
    setAgentForm((prev) => ({ ...prev, [field]: value }));
  }

  function updateTicketForm(field, value) {
    setTicketForm((prev) => ({ ...prev, [field]: value }));
  }

  return (
    <div className="admin-dashboard">
      <header className="dashboard-header">
        <div>
          <p className="dashboard-eyebrow">Wasla</p>

          <h1>لوحة تحكم الـAdmin</h1>

          <p className="dashboard-subtitle">
            إدارة ومتابعة عمليات قسمك
          </p>
        </div>

        <div className="dashboard-role">
          Admin
        </div>
      </header>

      <section className="dashboard-stats">
        <div className="stat-card">
          <span className="stat-label">تذاكر القسم</span>
          <strong className="stat-value">{tickets.length}</strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">التذاكر المفتوحة</span>
          <strong className="stat-value">{openCount}</strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">التذاكر المحلولة</span>
          <strong className="stat-value">{resolvedCount}</strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">Agents القسم</span>
          <strong className="stat-value">{agents.length}</strong>
        </div>
      </section>

      {error && <p className="dashboard-alert error">{error}</p>}
      {message && <p className="dashboard-alert success">{message}</p>}

      <section className="management-grid">
        <section className="dashboard-section">
          <div className="section-heading">
            <h2>إنشاء Agent</h2>

            <p>
              إنشاء موظف دعم داخل قسمك فقط
            </p>
          </div>

          <form className="management-form" onSubmit={handleAgentSubmit}>
            <label>
              Name
              <input
                required
                value={agentForm.name}
                onChange={(event) => updateAgentForm("name", event.target.value)}
              />
            </label>

            <label>
              Email
              <input
                required
                type="email"
                value={agentForm.email}
                onChange={(event) => updateAgentForm("email", event.target.value)}
              />
            </label>

            <label>
              Password
              <input
                required
                type="password"
                value={agentForm.password}
                onChange={(event) => updateAgentForm("password", event.target.value)}
              />
            </label>

            <button type="submit">Create Agent</button>
          </form>

          <div className="management-list">
            {loading && <p>Loading agents...</p>}
            {!loading && agents.length === 0 && <p>No agents in your department yet.</p>}

            {agents.map((agent) => (
              <div className="management-row user-row" key={agent.id}>
                <strong>{agent.name}</strong>
                <span>{agent.email}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="dashboard-section tickets-section">
          <div className="section-heading">
            <h2>إنشاء Ticket</h2>

            <p>
              إنشاء تذكرة جديدة وإسنادها ل_agent في قسمك
            </p>
          </div>

          <form className="management-form ticket-form" onSubmit={handleTicketSubmit}>
            <label>
              Client Name
              <input
                required
                value={ticketForm.client_name}
                onChange={(event) =>
                  updateTicketForm("client_name", event.target.value)
                }
              />
            </label>

            <label>
              Client Phone Number
              <input
                required
                value={ticketForm.client_phone_number}
                onChange={(event) =>
                  updateTicketForm("client_phone_number", event.target.value)
                }
              />
            </label>

            <label>
              Description
              <textarea
                required
                value={ticketForm.description}
                onChange={(event) =>
                  updateTicketForm("description", event.target.value)
                }
              />
            </label>

            <label>
              Assigned Agent
              <select
                required
                value={ticketForm.assigned_to}
                onChange={(event) =>
                  updateTicketForm("assigned_to", event.target.value)
                }
              >
                <option value="">Select agent...</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
            </label>

            <button
              type="submit"
              disabled={agents.length === 0}
            >
              Create Ticket
            </button>
          </form>
        </section>
      </section>

      <section className="dashboard-section">
        <div className="section-heading">
          <h2>تذاكر القسم</h2>

          <p>
            جميع تذاكر قسمك — اضغط على تذكرة لفتح التفاصيل
          </p>
        </div>

        <div className="management-list ticket-list">
          {loading && <p>Loading tickets...</p>}
          {!loading && tickets.length === 0 && <p>No tickets in your department yet.</p>}

          {tickets.map((ticket) => (
            <div
              className="management-row ticket-row clickable"
              key={ticket.id}
              onClick={() => onTicketClick?.(ticket.id)}
            >
              <strong>{ticket.client_name}</strong>
              <span>{ticket.client_phone_number}</span>
              <span>{ticket.description}</span>
              <span>{ticket.status}</span>
              <span>
                {agents.find((a) => a.id === ticket.assigned_to)?.name ||
                  `Agent ${ticket.assigned_to}`}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="dashboard-bottom-actions">
        <button
          className="action-card"
          onClick={() => onNavigate?.("documents")}
        >
          <span className="action-icon">📄</span>
          <span className="action-title">Documents</span>
          <span className="action-description">
            رفع مستندات المعرفة لقسمك
          </span>
        </button>
      </section>
    </div>
  );
}

export default AdminDashboard;

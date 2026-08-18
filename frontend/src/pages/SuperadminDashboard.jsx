// This file renders the Superadmin dashboard for the Wasla frontend.
// The Superadmin has platform-wide access.

import { useEffect, useMemo, useRef, useState } from "react";
import {
  createDepartment,
  createTicket,
  createUser,
  getDepartments,
  getTickets,
  getUsers,
  uploadDocument,
} from "../api";
import ChatPanel from "../components/ChatPanel";
import "./SuperadminDashboard.css";

const initialDepartmentForm = {
  name: "",
  description: "",
};

const initialUserForm = {
  name: "",
  email: "",
  password: "",
  role: "admin",
  department_id: "",
};

const initialTicketForm = {
  client_name: "",
  client_phone_number: "",
  description: "",
  assigned_to: "",
  department_id: "",
};

function SuperadminDashboard({ token, user, onNavigate, onTicketClick }) {
  const fileInputRef = useRef(null);
  const [departments, setDepartments] = useState([]);
  const [users, setUsers] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [departmentForm, setDepartmentForm] = useState(initialDepartmentForm);
  const [userForm, setUserForm] = useState(initialUserForm);
  const [ticketForm, setTicketForm] = useState(initialTicketForm);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [ticketDeptFilter, setTicketDeptFilter] = useState("all");
  const [selectedDepartment, setSelectedDepartment] = useState(null);
  const [uploading, setUploading] = useState(false);

  const departmentById = useMemo(() => {
    return departments.reduce((currentMap, department) => {
      currentMap[department.id] = department;
      return currentMap;
    }, {});
  }, [departments]);

  const agents = users.filter((user) => user.role === "agent");
  const availableAgents = agents.filter((agent) => {
    return Number(ticketForm.department_id) === agent.department_id;
  });

  const filteredTickets = useMemo(() => {
    if (ticketDeptFilter === "all") return tickets;
    return tickets.filter(
      (t) => t.department_id === Number(ticketDeptFilter),
    );
  }, [tickets, ticketDeptFilter]);

  useEffect(() => {
    async function loadManagementData() {
      try {
        const [departmentData, userData, ticketData] = await Promise.all([
          getDepartments(token),
          getUsers(token),
          getTickets(token),
        ]);

        setDepartments(departmentData);
        setUsers(userData);
        setTickets(ticketData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadManagementData();
  }, [token]);

  async function handleDepartmentSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    try {
      const department = await createDepartment(
        {
          name: departmentForm.name,
          description: departmentForm.description || null,
        },
        token,
      );
      setDepartments((currentDepartments) => [...currentDepartments, department]);
      setDepartmentForm(initialDepartmentForm);
      setMessage("Department created.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleUserSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    try {
      const created = await createUser(
        {
          ...userForm,
          department_id: Number(userForm.department_id),
        },
        token,
      );
      setUsers((currentUsers) => [...currentUsers, created]);
      setUserForm({
        ...initialUserForm,
        department_id: departments[0]?.id ? String(departments[0].id) : "",
      });
      setMessage("User created.");
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
          department_id: Number(ticketForm.department_id),
        },
        token,
      );
      setTickets((currentTickets) => [ticket, ...currentTickets]);
      setTicketForm({
        ...initialTicketForm,
        department_id: departments[0]?.id ? String(departments[0].id) : "",
        assigned_to: "",
      });
      setMessage("Ticket created.");
    } catch (err) {
      setError(err.message);
    }
  }

  function updateDepartmentForm(field, value) {
    setDepartmentForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }));
  }

  function updateUserForm(field, value) {
    setUserForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }));
  }

  function updateTicketForm(field, value) {
    setTicketForm((currentForm) => ({
      ...currentForm,
      [field]: value,
      ...(field === "department_id" ? { assigned_to: "" } : {}),
    }));
  }

  async function handleDeptFileChange(event) {
    const file = event.target.files?.[0];
    if (!file || !selectedDepartment) return;

    setUploading(true);
    setError("");
    try {
      await uploadDocument(file, token, selectedDepartment.id);
      setMessage(`تم رفع "${file.name}" إلى قسم ${selectedDepartment.name}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  useEffect(() => {
    if (!userForm.department_id && departments.length > 0) {
      setUserForm((currentForm) => ({
        ...currentForm,
        department_id: String(departments[0].id),
      }));
    }
  }, [departments, userForm.department_id]);

  useEffect(() => {
    if (!ticketForm.department_id && departments.length > 0) {
      setTicketForm((currentForm) => ({
        ...currentForm,
        department_id: String(departments[0].id),
      }));
    }
  }, [departments, ticketForm.department_id]);

  useEffect(() => {
    if (!ticketForm.assigned_to && availableAgents.length > 0) {
      setTicketForm((currentForm) => ({
        ...currentForm,
        assigned_to: String(availableAgents[0].id),
      }));
    }
  }, [availableAgents, ticketForm.assigned_to]);

  return (
    <div className="superadmin-dashboard">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx"
        style={{ display: "none" }}
        onChange={handleDeptFileChange}
      />

      {selectedDepartment ? (
        <>
          <header className="dashboard-header">
            <div>
              <p className="dashboard-eyebrow">Wasla</p>
              <h1>{selectedDepartment.name}</h1>
              <p className="dashboard-subtitle">
                محادثة ورفع مستندات هذا القسم
              </p>
            </div>
            <button
              className="back-button"
              onClick={() => setSelectedDepartment(null)}
            >
              ← العودة
            </button>
          </header>

          {error && <p className="dashboard-alert error">{error}</p>}
          {message && <p className="dashboard-alert success">{message}</p>}

          <div className="dept-scoped-layout">
            <div className="dept-chat-col">
              <ChatPanel
                token={token}
                user={user}
                fullWidth
                departmentId={selectedDepartment.id}
              />
            </div>
            <div className="dept-upload-col">
              <div className="dashboard-section">
                <div className="section-heading">
                  <h2>رفع مستند</h2>
                  <p>رفع ملف إلى قسم {selectedDepartment.name}</p>
                </div>
                <button
                  className="upload-button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                >
                  {uploading ? "جاري الرفع..." : "+ اختر ملف"}
                </button>
                <p className="dept-upload-hint">
                  PDF أو DOCX فقط — سيتم المعالجة تلقائياً
                </p>
              </div>
            </div>
          </div>
        </>
      ) : (
        <>
          <header className="dashboard-header">
            <div>
              <p className="dashboard-eyebrow">Wasla</p>
              <h1>لوحة تحكم Superadmin</h1>
              <p className="dashboard-subtitle">
                إدارة ومتابعة المنصة بالكامل
              </p>
            </div>
            <div className="dashboard-role">Superadmin</div>
          </header>

      <section className="dashboard-stats">
        <div className="stat-card">
          <span className="stat-label">إجمالي التذاكر</span>
          <strong className="stat-value">{tickets.length}</strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">الأقسام</span>
          <strong className="stat-value">{departments.length}</strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">Admins</span>
          <strong className="stat-value">
            {users.filter((u) => u.role === "admin").length}
          </strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">Agents</span>
          <strong className="stat-value">
            {users.filter((u) => u.role === "agent").length}
          </strong>
        </div>
      </section>

      {error && <p className="dashboard-alert error">{error}</p>}
      {message && <p className="dashboard-alert success">{message}</p>}

      <section className="management-grid">
        <section className="dashboard-section">
          <div className="section-heading">
            <h2>إدارة الأقسام</h2>
          </div>

          <form className="management-form" onSubmit={handleDepartmentSubmit}>
            <label>
              Name
              <input
                required
                value={departmentForm.name}
                onChange={(event) => updateDepartmentForm("name", event.target.value)}
              />
            </label>

            <label>
              Description
              <textarea
                value={departmentForm.description}
                onChange={(event) =>
                  updateDepartmentForm("description", event.target.value)
                }
              />
            </label>

            <button type="submit">Create Department</button>
          </form>

          <div className="management-list">
            {loading && <p>Loading departments...</p>}
            {!loading && departments.length === 0 && <p>No departments yet.</p>}

            {departments.map((department) => (
              <div
                className="management-row dept-clickable"
                key={department.id}
                onClick={() => setSelectedDepartment(department)}
              >
                <strong>{department.name}</strong>
                <span>{department.description || "No description"}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="dashboard-section">
          <div className="section-heading">
            <h2>إدارة المستخدمين</h2>

            <p>superadmin ينشئ admins و agents في أي قسم</p>
          </div>

          <form className="management-form" onSubmit={handleUserSubmit}>
            <label>
              Name
              <input
                required
                value={userForm.name}
                onChange={(event) => updateUserForm("name", event.target.value)}
              />
            </label>

            <label>
              Email
              <input
                required
                type="email"
                value={userForm.email}
                onChange={(event) => updateUserForm("email", event.target.value)}
              />
            </label>

            <label>
              Password
              <input
                required
                type="password"
                value={userForm.password}
                onChange={(event) => updateUserForm("password", event.target.value)}
              />
            </label>

            <label>
              Role
              <select
                value={userForm.role}
                onChange={(event) => updateUserForm("role", event.target.value)}
              >
                <option value="admin">admin</option>
                <option value="agent">agent</option>
              </select>
            </label>

            <label>
              Department
              <select
                required
                value={userForm.department_id}
                onChange={(event) =>
                  updateUserForm("department_id", event.target.value)
                }
              >
                {departments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
            </label>

            <button type="submit" disabled={departments.length === 0}>
              Create User
            </button>
          </form>

          <div className="management-list">
            {loading && <p>Loading users...</p>}
            {!loading && users.length === 0 && <p>No users yet.</p>}

            {users.map((u) => (
              <div className="management-row user-row" key={u.id}>
                <strong>{u.name}</strong>
                <span>{u.email}</span>
                <span>{u.role}</span>
                <span>
                  {departmentById[u.department_id]?.name ||
                    `Department ${u.department_id || "-"}`}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="dashboard-section tickets-section">
          <div className="section-heading">
            <h2>إدارة التذاكر</h2>

            <p>superadmin ينشئ تذاكر في أي قسم</p>
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
              Department
              <select
                required
                value={ticketForm.department_id}
                onChange={(event) =>
                  updateTicketForm("department_id", event.target.value)
                }
              >
                {departments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
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
                {availableAgents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
            </label>

            <button
              type="submit"
              disabled={departments.length === 0 || availableAgents.length === 0}
            >
              Create Ticket
            </button>
          </form>

          <div className="ticket-list-toolbar">
            <label className="ticket-filter-label">
              Filter by department:
              <select
                value={ticketDeptFilter}
                onChange={(event) => setTicketDeptFilter(event.target.value)}
              >
                <option value="all">All departments</option>
                {departments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="management-list ticket-list">
            {loading && <p>Loading tickets...</p>}
            {!loading && filteredTickets.length === 0 && <p>No tickets found.</p>}

            {filteredTickets.map((ticket) => (
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
                  {departmentById[ticket.department_id]?.name ||
                    `Dept ${ticket.department_id}`}
                </span>
                <span>
                  {users.find((u) => u.id === ticket.assigned_to)?.name ||
                    `Agent ${ticket.assigned_to}`}
                </span>
              </div>
            ))}
          </div>
        </section>
      </section>

      <section className="dashboard-bottom-actions">
        <button
          className="action-card"
          onClick={() => onNavigate?.("chat")}
        >
          <span className="action-icon">💬</span>
          <span className="action-title">اسأل المساعد</span>
          <span className="action-description">
            سؤال المساعد الذكي عن أي موضوع
          </span>
        </button>

        <button
          className="action-card"
          onClick={() => onNavigate?.("documents")}
        >
          <span className="action-icon">📄</span>
          <span className="action-title">Documents</span>
          <span className="action-description">
            رفع مستندات المعرفة لأي قسم
          </span>
        </button>
      </section>
        </>
      )}
    </div>
  );
}

export default SuperadminDashboard;

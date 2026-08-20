// This file renders the Admin dashboard for the Wasla frontend.
// The Admin is responsible for one department and its support operations.

import { useEffect, useMemo, useRef, useState } from "react";
import {
  createTicket,
  createUser,
  getDepartments,
  getDocuments,
  getTickets,
  getUsers,
  uploadKnowledgeDocument,
} from "../api";
import DashboardHeader from "./DashboardHeader";
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

const STATUS_LABELS = {
  resolved: "محلولة",
  unresolved: "غير محلولة",
};

function AdminDashboard({ token, user, onLogout }) {
  const [activeSection, setActiveSection] = useState("agents");
  const [users, setUsers] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [agentForm, setAgentForm] = useState(initialAgentForm);
  const [ticketForm, setTicketForm] = useState(initialTicketForm);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const messageTimer = useRef(null);

  const department = useMemo(
    () => departments.find((d) => d.id === user?.department_id) || null,
    [departments, user?.department_id],
  );

  const agents = useMemo(
    () => users.filter((u) => u.role === "agent"),
    [users],
  );

  const userById = useMemo(() => {
    return users.reduce((currentMap, userEntry) => {
      currentMap[userEntry.id] = userEntry;
      return currentMap;
    }, {});
  }, [users]);

  const unresolvedCount = useMemo(
    () => tickets.filter((t) => t.status !== "resolved").length,
    [tickets],
  );

  const agentTicketCount = (agentId) =>
    tickets.filter((t) => t.assigned_to === agentId).length;

  function flashMessage(messageText, errorText = "") {
    if (messageTimer.current) {
      clearTimeout(messageTimer.current);
    }
    setMessage(messageText);
    setError(errorText);
    messageTimer.current = setTimeout(() => {
      setMessage("");
      setError("");
    }, 3000);
  }

  useEffect(() => {
    return () => {
      if (messageTimer.current) {
        clearTimeout(messageTimer.current);
      }
    };
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        const [ticketData, userData, documentData, departmentData] =
          await Promise.all([
            getTickets(token),
            getUsers(token),
            getDocuments(token),
            getDepartments(token),
          ]);
        setTickets(ticketData);
        setUsers(userData);
        setDocuments(documentData);
        setDepartments(departmentData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [token]);

  async function handleAgentSubmit(event) {
    event.preventDefault();
    flashMessage("");

    try {
      const created = await createUser(
        {
          ...agentForm,
          role: "agent",
          department_id: user.department_id,
        },
        token,
      );
      setUsers((prev) => [...prev, created]);
      setAgentForm(initialAgentForm);
      flashMessage("تم انشاء وكيل");
    } catch (err) {
      flashMessage("", "فشل في انشاء وكيل");
    }
  }

  async function handleTicketSubmit(event) {
    event.preventDefault();
    flashMessage("");

    try {
      const ticket = await createTicket(
        {
          ...ticketForm,
          assigned_to: Number(ticketForm.assigned_to),
          department_id: user.department_id,
        },
        token,
      );
      setTickets((prev) => [...prev, ticket]);
      setTicketForm(initialTicketForm);
      flashMessage("تم انشاء تذكره");
    } catch (err) {
      flashMessage("", "فشل في انشاء تذكره");
    }
  }

  async function handleUploadSubmit(event) {
    event.preventDefault();
    if (!uploadFile) {
      return;
    }

    flashMessage("");
    setUploading(true);

    try {
      const doc = await uploadKnowledgeDocument(
        uploadFile,
        token,
        user.department_id,
      );
      setDocuments((prev) => [...prev, doc]);
      setUploadFile(null);
      flashMessage("تم رفع الملف");
    } catch (err) {
      flashMessage("", "فشل في رفع الملف");
    } finally {
      setUploading(false);
    }
  }

  function updateAgentForm(field, value) {
    setAgentForm((prev) => ({ ...prev, [field]: value }));
  }

  function updateTicketForm(field, value) {
    setTicketForm((prev) => ({ ...prev, [field]: value }));
  }

  return (
    <div className="admin-dashboard" dir="rtl">
      <DashboardHeader
        user={user}
        onLogout={onLogout}
        subtitle={department ? `قسم الـ ${department.name}` : ""}
      />

      <section className="sa-stats">
        <div className="sa-stat-card">
          <span>الوكلاء</span>
          <strong>{agents.length}</strong>
        </div>

        <div className="sa-stat-card">
          <span>التذاكر</span>
          <strong>{tickets.length}</strong>
        </div>

        <div className="sa-stat-card">
          <span>تذاكر غير محلولة</span>
          <strong>{unresolvedCount}</strong>
        </div>

        <div className="sa-stat-card">
          <span>المستندات</span>
          <strong>{documents.length}</strong>
        </div>
      </section>

      {error && <p className="dashboard-alert error">{error}</p>}
      {message && <p className="dashboard-alert success">{message}</p>}

      <section className="sa-workspace">
        <nav className="sa-tabs">
          <button
            className={activeSection === "agents" ? "sa-tab active" : "sa-tab"}
            onClick={() => setActiveSection("agents")}
          >
            إنشاء وكيل
          </button>

          <button
            className={
              activeSection === "tickets" ? "sa-tab active" : "sa-tab"
            }
            onClick={() => setActiveSection("tickets")}
          >
            إنشاء تذكرة
          </button>

          <button
            className={
              activeSection === "upload" ? "sa-tab active" : "sa-tab"
            }
            onClick={() => setActiveSection("upload")}
          >
            رفع ملف
          </button>
        </nav>

        <div className="sa-create-box">
          {activeSection === "agents" && (
            <form className="management-form" onSubmit={handleAgentSubmit}>
              <label>
                الاسم
                <input
                  required
                  value={agentForm.name}
                  onChange={(event) =>
                    updateAgentForm("name", event.target.value)
                  }
                />
              </label>

              <label>
                البريد الإلكتروني
                <input
                  required
                  type="email"
                  value={agentForm.email}
                  onChange={(event) =>
                    updateAgentForm("email", event.target.value)
                  }
                />
              </label>

              <label>
                كلمة المرور
                <input
                  required
                  type="password"
                  value={agentForm.password}
                  onChange={(event) =>
                    updateAgentForm("password", event.target.value)
                  }
                />
              </label>

              <button type="submit">إنشاء وكيل</button>
            </form>
          )}

          {activeSection === "tickets" && (
            <form className="management-form" onSubmit={handleTicketSubmit}>
              <label>
                اسم العميل
                <input
                  required
                  value={ticketForm.client_name}
                  onChange={(event) =>
                    updateTicketForm("client_name", event.target.value)
                  }
                />
              </label>

              <label>
                رقم هاتف العميل
                <input
                  required
                  value={ticketForm.client_phone_number}
                  onChange={(event) =>
                    updateTicketForm("client_phone_number", event.target.value)
                  }
                />
              </label>

              <label>
                الوصف
                <textarea
                  required
                  value={ticketForm.description}
                  onChange={(event) =>
                    updateTicketForm("description", event.target.value)
                  }
                />
              </label>

              <label>
                الوكيل المسند
                <select
                  required
                  value={ticketForm.assigned_to}
                  onChange={(event) =>
                    updateTicketForm("assigned_to", event.target.value)
                  }
                >
                  <option value="">اختر وكيل...</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
              </label>

              <button type="submit" disabled={agents.length === 0}>
                إنشاء تذكرة
              </button>
            </form>
          )}

          {activeSection === "upload" && (
            <form className="management-form" onSubmit={handleUploadSubmit}>
              <label>
                ملف المستند
                <input
                  required
                  type="file"
                  accept=".pdf,.docx"
                  onChange={(event) =>
                    setUploadFile(event.target.files?.[0] || null)
                  }
                />
              </label>

              <button type="submit" disabled={uploading || !uploadFile}>
                {uploading ? "جاري الرفع..." : "رفع الملف"}
              </button>
            </form>
          )}
        </div>

        <div className="sa-main">
          {activeSection === "agents" && (
            <>
              <h2 className="sa-section-title">اداره الوكلاء</h2>

              <div className="sa-info-grid">
                {loading && <p>Loading agents...</p>}
              {!loading && agents.length === 0 && (
                <p>لا يوجد وكلاء في قسمك بعد.</p>
              )}

              {agents.map((agent) => (
                <div className="sa-info-card" key={agent.id}>
                  <strong className="sa-card-name">
                    الاسم: {agent.name}
                  </strong>
                  <span className="sa-card-stat">
                    البريد الإلكتروني: {agent.email}
                  </span>
                  <span className="sa-card-stat">
                    التذاكر المسندة: {agentTicketCount(agent.id)}
                  </span>
                  <span className="sa-card-stat">
                    المنشئ:{" "}
                    {userById[agent.created_by]?.name ||
                      (agent.created_by ? `User ${agent.created_by}` : "—")}
                  </span>
                </div>
              ))}
            </div>
            </>
          )}

          {activeSection === "tickets" && (
            <>
              <h2 className="sa-section-title">اداره التذاكر</h2>

              <div className="sa-info-grid">
                {loading && <p>Loading tickets...</p>}
              {!loading && tickets.length === 0 && (
                <p>لا توجد تذاكر في قسمك بعد.</p>
              )}

              {tickets.map((ticket) => (
                <div className="sa-info-card" key={ticket.id}>
                  <strong className="sa-card-name">
                    اسم العميل: {ticket.client_name}
                  </strong>
                  <span className="sa-card-stat">
                    رقم التذكرة: {ticket.id}
                  </span>
                  <span className="sa-card-stat">
                    الوكيل:{" "}
                    {userById[ticket.assigned_to]?.name ||
                      `Agent ${ticket.assigned_to}`}
                  </span>
                  <span className="sa-card-stat">
                    الحالة: {STATUS_LABELS[ticket.status] || ticket.status}
                  </span>
                  <span className="sa-card-stat">
                    المنشئ:{" "}
                    {userById[ticket.created_by]?.name ||
                      (ticket.created_by ? `User ${ticket.created_by}` : "—")}
                  </span>
                  <span className="sa-card-stat sa-card-desc">
                    {ticket.description}
                  </span>
                </div>
              ))}
            </div>
            </>
          )}

          {activeSection === "upload" && (
            <>
              <h2 className="sa-section-title">اداره الملفات</h2>

              <div className="sa-info-grid">
                {loading && <p>Loading documents...</p>}
              {!loading && documents.length === 0 && (
                <p>لا توجد مستندات في قسمك بعد.</p>
              )}

              {documents.map((doc) => (
                <div className="sa-info-card sa-doc-card" key={doc.id}>
                  <strong className="sa-card-name">{doc.filename}</strong>
                  <span className="sa-card-stat">
                    المنشئ:{" "}
                    {userById[doc.uploaded_by]?.name ||
                      (doc.uploaded_by ? `User ${doc.uploaded_by}` : "—")}
                  </span>
                </div>
              ))}
            </div>
            </>
          )}
        </div>
      </section>
    </div>
  );
}

export default AdminDashboard;
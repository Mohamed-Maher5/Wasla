// This file renders the Superadmin dashboard for the Wasla frontend.
// The Superadmin manages departments and admins platform-wide.

import { useEffect, useMemo, useRef, useState } from "react";
import {
  createDepartment,
  createUser,
  getDepartments,
  getTickets,
  getUsers,
} from "../api";
import waslaLogo from "../assets/wasla-logo-arabic.png";
import "./SuperadminDashboard.css";

const initialDepartmentForm = {
  name: "",
  description: "",
};

const initialUserForm = {
  name: "",
  email: "",
  password: "",
  department_id: "",
};

const ROLE_LABELS = {
  superadmin: "المسؤل الأعلى",
  admin: "المسؤل",
  agent: "الوكيل",
};

function SuperadminDashboard({ token, user, onLogout }) {
  const [departments, setDepartments] = useState([]);
  const [users, setUsers] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [activeSection, setActiveSection] = useState("departments");
  const [departmentForm, setDepartmentForm] = useState(initialDepartmentForm);
  const [userForm, setUserForm] = useState(initialUserForm);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const messageTimer = useRef(null);

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

  const departmentById = useMemo(() => {
    return departments.reduce((currentMap, department) => {
      currentMap[department.id] = department;
      return currentMap;
    }, {});
  }, [departments]);

  const admins = useMemo(() => users.filter((u) => u.role === "admin"), [users]);
  const agents = useMemo(() => users.filter((u) => u.role === "agent"), [users]);

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

  const departmentAdminCount = (departmentId) =>
    admins.filter((a) => a.department_id === departmentId).length;

  const departmentAgentCount = (departmentId) =>
    agents.filter((a) => a.department_id === departmentId).length;

  const departmentUnresolvedTicketCount = (departmentId) =>
    tickets.filter(
      (t) => t.department_id === departmentId && t.status !== "resolved",
    ).length;

  const adminCreatedTicketCount = (adminId) =>
    tickets.filter((t) => t.created_by === adminId).length;

  const adminCreatedAgentCount = (adminId) =>
    agents.filter((a) => a.created_by === adminId).length;

  async function handleDepartmentSubmit(event) {
    event.preventDefault();
    flashMessage("");

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
      flashMessage("تم انشاء قسم");
    } catch (err) {
      flashMessage("", "فشل في انشاء قسم");
    }
  }

  async function handleUserSubmit(event) {
    event.preventDefault();
    flashMessage("");

    try {
      const created = await createUser(
        {
          ...userForm,
          role: "admin",
          department_id: Number(userForm.department_id),
        },
        token,
      );
      setUsers((currentUsers) => [...currentUsers, created]);
      setUserForm(initialUserForm);
      flashMessage("تم انشاء مسؤل");
    } catch (err) {
      flashMessage("", "فشل في انشاء مسؤل");
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

  return (
    <div className="superadmin-dashboard" dir="rtl">
      <header className="sa-header">
        <div className="sa-header-brand">
          <img className="sa-logo" src={waslaLogo} alt="Wasla" />
          <span className="sa-header-title">
            لوحة تحكم <strong>{ROLE_LABELS[user?.role] || user?.role}</strong>
          </span>
        </div>

        <button className="sa-logout" onClick={onLogout}>
          تسجيل خروج
        </button>
      </header>

      <section className="sa-stats">
        <div className="sa-stat-card">
          <span>الأقسام</span>
          <strong>{departments.length}</strong>
        </div>

        <div className="sa-stat-card">
          <span>المسؤلين</span>
          <strong>{admins.length}</strong>
        </div>

        <div className="sa-stat-card">
          <span>الوكلاء</span>
          <strong>{agents.length}</strong>
        </div>

        <div className="sa-stat-card">
          <span>التذاكر</span>
          <strong>{tickets.length}</strong>
        </div>
      </section>

      {error && <p className="dashboard-alert error">{error}</p>}
      {message && <p className="dashboard-alert success">{message}</p>}

      <div className="sa-workspace">
        <aside className="sa-tabs">
          <button
            className={
              activeSection === "departments" ? "sa-tab active" : "sa-tab"
            }
            onClick={() => setActiveSection("departments")}
          >
            الأقسام
          </button>

          <button
            className={activeSection === "admins" ? "sa-tab active" : "sa-tab"}
            onClick={() => setActiveSection("admins")}
          >
            إدارة المسؤلين
          </button>
        </aside>

        {activeSection === "departments" ? (
          <>
            <section className="sa-create-box">
              <h3>إنشاء قسم</h3>

              <form className="management-form" onSubmit={handleDepartmentSubmit}>
                <label>
                  الاسم
                  <input
                    required
                    value={departmentForm.name}
                    onChange={(event) =>
                      updateDepartmentForm("name", event.target.value)
                    }
                  />
                </label>

                <label>
                  الوصف
                  <textarea
                    value={departmentForm.description}
                    onChange={(event) =>
                      updateDepartmentForm("description", event.target.value)
                    }
                  />
                </label>

                <button type="submit">إنشاء قسم</button>
              </form>
            </section>

            <section className="sa-main">
              <h2 className="sa-section-title">إدارة الأقسام</h2>

              <div className="sa-info-grid">
                {loading && <p>Loading departments...</p>}
                {!loading && departments.length === 0 && (
                  <p>لا توجد أقسام بعد.</p>
                )}

                {departments.map((department) => (
                  <div className="sa-info-card" key={department.id}>
                    <strong className="sa-card-name">
                      قسم : {department.name}
                    </strong>
                    <span className="sa-card-stat">
                      عدد المسؤلين: {departmentAdminCount(department.id)}
                    </span>
                    <span className="sa-card-stat">
                      عدد الوكلاء: {departmentAgentCount(department.id)}
                    </span>
                    <span className="sa-card-stat">
                      التذاكر غير المحلولة:{" "}
                      {departmentUnresolvedTicketCount(department.id)}
                    </span>
                    <p className="sa-card-desc">
                      {department.description || "لا يوجد وصف"}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          </>
        ) : (
          <>
            <section className="sa-create-box">
              <h3>إنشاء مسؤل</h3>

              <form className="management-form" onSubmit={handleUserSubmit}>
                <label>
                  الاسم
                  <input
                    required
                    value={userForm.name}
                    onChange={(event) => updateUserForm("name", event.target.value)}
                  />
                </label>

                <label>
                  البريد الإلكتروني
                  <input
                    required
                    type="email"
                    value={userForm.email}
                    onChange={(event) => updateUserForm("email", event.target.value)}
                  />
                </label>

                <label>
                  كلمة المرور
                  <input
                    required
                    type="password"
                    value={userForm.password}
                    onChange={(event) => updateUserForm("password", event.target.value)}
                  />
                </label>

                <label>
                  القسم
                  <select
                    required
                    value={userForm.department_id}
                      onChange={(event) =>
                        updateUserForm("department_id", event.target.value)
                      }
                    >
                      <option value="" disabled hidden>
                        اختر
                      </option>
                      {departments.map((department) => (
                      <option key={department.id} value={department.id}>
                        {department.name}
                      </option>
                    ))}
                  </select>
                </label>

                <button type="submit" disabled={departments.length === 0}>
                  إنشاء مسؤل
                </button>
              </form>
            </section>

            <section className="sa-main">
              <h2 className="sa-section-title">اداره المسؤلين</h2>

              <div className="sa-info-grid">
                {loading && <p>Loading admins...</p>}
                {!loading && admins.length === 0 && (
                  <p>لا يوجد مسؤلين بعد.</p>
                )}

                {admins.map((admin) => (
                  <div className="sa-info-card" key={admin.id}>
                    <strong className="sa-card-name">
                      الاسم: {admin.name}
                    </strong>
                    <span className="sa-card-stat">
                      البريد الإلكتروني: {admin.email}
                    </span>
                    <span className="sa-card-stat">
                      القسم:{" "}
                      {departmentById[admin.department_id]?.name ||
                        `Department ${admin.department_id || "-"}`}
                    </span>
                    <span className="sa-card-stat">
                      التذاكر التي أنشأها: {adminCreatedTicketCount(admin.id)}
                    </span>
                    <span className="sa-card-stat">
                      الوكلاء الذين أنشأهم: {adminCreatedAgentCount(admin.id)}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}

export default SuperadminDashboard;
// This file renders the shared dashboard header for the Wasla frontend.
// It shows the brand, a role label, and a logout button. Reused by dashboards.

import waslaLogo from "../assets/wasla-logo-arabic.png";
import "./DashboardHeader.css";

const ROLE_LABELS = {
  superadmin: "المسؤل الأعلى",
  admin: "المسؤل",
  agent: "الوكيل",
};

function DashboardHeader({ user, onLogout, subtitle }) {
  return (
    <header className="sa-header">
      <div className="sa-header-brand">
        <img className="sa-logo" src={waslaLogo} alt="Wasla" />
        <div className="sa-header-text">
          <span className="sa-header-title">
            لوحة تحكم{" "}
            <strong>{ROLE_LABELS[user?.role] || user?.role}</strong>{" "}
            <span className="sa-header-name">{user?.name || ""}</span>
          </span>
          {subtitle && <span className="sa-header-subtitle">{subtitle}</span>}
        </div>
      </div>

      <button className="sa-logout" onClick={onLogout}>
        تسجيل خروج
      </button>
    </header>
  );
}

export default DashboardHeader;
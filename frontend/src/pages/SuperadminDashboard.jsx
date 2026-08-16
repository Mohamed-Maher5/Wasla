// This file renders the Superadmin dashboard for the Wasla frontend.
// The Superadmin has platform-wide access.

import "./SuperadminDashboard.css";

function SuperadminDashboard() {
  return (
    <div className="superadmin-dashboard">
      <header className="dashboard-header">
        <div>
          <p className="dashboard-eyebrow">Wasla</p>

          <h1>لوحة تحكم Superadmin</h1>

          <p className="dashboard-subtitle">
            إدارة ومتابعة المنصة بالكامل
          </p>
        </div>

        <div className="dashboard-role">
          Superadmin
        </div>
      </header>

      <section className="dashboard-stats">
        <div className="stat-card">
          <span className="stat-label">إجمالي التذاكر</span>
          <strong className="stat-value">--</strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">الأقسام</span>
          <strong className="stat-value">--</strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">Admins</span>
          <strong className="stat-value">--</strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">Agents</span>
          <strong className="stat-value">--</strong>
        </div>
      </section>

      <section className="dashboard-section">
        <div className="section-heading">
          <h2>إدارة المنصة</h2>

          <p>
            الوظائف الخاصة بإدارة المنصة بالكامل
          </p>
        </div>

        <div className="action-grid">
          <button className="action-card">
            <span className="action-icon">🏢</span>

            <span className="action-title">
              إدارة الأقسام
            </span>

            <span className="action-description">
              إنشاء ومتابعة أقسام المنصة
            </span>
          </button>

          <button className="action-card">
            <span className="action-icon">👤</span>

            <span className="action-title">
              إدارة الـAdmins
            </span>

            <span className="action-description">
              إدارة مسؤولي الأقسام
            </span>
          </button>

          <button className="action-card">
            <span className="action-icon">🎫</span>

            <span className="action-title">
              جميع التذاكر
            </span>

            <span className="action-description">
              متابعة جميع Tickets الموجودة على المنصة
            </span>
          </button>

          <button className="action-card">
            <span className="action-icon">➕</span>

            <span className="action-title">
              إنشاء Ticket
            </span>

            <span className="action-description">
              إنشاء تذكرة جديدة
            </span>
          </button>
        </div>
      </section>

      <section className="dashboard-overview">
        <div className="overview-card">
          <div className="overview-header">
            <h2>آخر التذاكر</h2>

            <button className="text-button">
              عرض الكل
            </button>
          </div>

          <div className="empty-state">
            <span className="empty-icon">🎫</span>

            <p>
              سيتم عرض جميع تذاكر المنصة هنا بعد ربط البيانات.
            </p>
          </div>
        </div>

        <div className="overview-card">
          <div className="overview-header">
            <h2>ملخص المنصة</h2>
          </div>

          <div className="empty-state">
            <span className="empty-icon">📊</span>

            <p>
              سيتم عرض إحصائيات الأقسام والـAdmins والـAgents هنا.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default SuperadminDashboard;
// This file renders the Admin dashboard for the Wasla frontend.
// The Admin is responsible for one department and its support operations.

import "./AdminDashboard.css";

function AdminDashboard() {
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
          <strong className="stat-value">--</strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">التذاكر المفتوحة</span>
          <strong className="stat-value">--</strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">التذاكر المحلولة</span>
          <strong className="stat-value">--</strong>
        </div>

        <div className="stat-card">
          <span className="stat-label">Agents القسم</span>
          <strong className="stat-value">--</strong>
        </div>
      </section>

      <section className="dashboard-section">
        <div className="section-heading">
          <h2>إدارة القسم</h2>

          <p>
            الوظائف المتاحة لمسؤول القسم
          </p>
        </div>

        <div className="action-grid">
          <button className="action-card">
            <span className="action-icon">👥</span>

            <span className="action-title">
              إدارة الـAgents
            </span>

            <span className="action-description">
              إنشاء وإدارة موظفي الدعم داخل قسمك
            </span>
          </button>

          <button className="action-card">
            <span className="action-icon">🎫</span>

            <span className="action-title">
              تذاكر القسم
            </span>

            <span className="action-description">
              عرض ومتابعة جميع تذاكر قسمك
            </span>
          </button>

          <button className="action-card">
            <span className="action-icon">➕</span>

            <span className="action-title">
              إنشاء Ticket
            </span>

            <span className="action-description">
              إنشاء تذكرة جديدة لعميل داخل القسم
            </span>
          </button>

          <button className="action-card">
            <span className="action-icon">📄</span>

            <span className="action-title">
              Documents
            </span>

            <span className="action-description">
              رفع مستندات المعرفة الخاصة بالقسم
            </span>
          </button>
        </div>
      </section>

      <section className="dashboard-overview">
        <div className="overview-card">
          <div className="overview-header">
            <h2>تذاكر القسم</h2>

            <button className="text-button">
              عرض الكل
            </button>
          </div>

          <div className="empty-state">
            <span className="empty-icon">🎫</span>

            <p>
              سيتم عرض تذاكر القسم هنا بعد ربط البيانات الحقيقية.
            </p>
          </div>
        </div>

        <div className="overview-card">
          <div className="overview-header">
            <h2>Agents القسم</h2>
          </div>

          <div className="empty-state">
            <span className="empty-icon">👥</span>

            <p>
              سيتم عرض Agents التابعين للقسم هنا.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default AdminDashboard;
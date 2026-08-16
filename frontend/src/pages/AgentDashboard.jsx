import "./AgentDashboard.css";

function AgentDashboard() {
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

      <section className="dashboard-stats">
        <div className="stat-card">
          <span className="stat-label">التذاكر المسندة إليّ</span>
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
      </section>

      <section className="dashboard-section">
        <div className="section-heading">
          <h2>التذاكر الخاصة بي</h2>

          <p>
            التذاكر التي تم إسنادها إليك
          </p>
        </div>

        <div className="agent-actions">
          <button className="action-card">
            <span className="action-icon">🎫</span>

            <span className="action-title">
              التذاكر المسندة إليّ
            </span>

            <span className="action-description">
              عرض ومتابعة التذاكر الخاصة بك
            </span>
          </button>

          <button className="action-card">
            <span className="action-icon">📞</span>

            <span className="action-title">
              الاتصال بالعميل
            </span>

            <span className="action-description">
              الاتصال بالعميل من خلال التذكرة
            </span>
          </button>

          <button className="action-card">
            <span className="action-icon">💬</span>

            <span className="action-title">
              مساعد Wasla
            </span>

            <span className="action-description">
              استخدام المساعد أثناء التعامل مع التذكرة
            </span>
          </button>

          <button className="action-card">
            <span className="action-icon">✓</span>

            <span className="action-title">
              تحديث حالة Ticket
            </span>

            <span className="action-description">
              حل التذكرة أو إبقاؤها غير محلولة
            </span>
          </button>
        </div>
      </section>

      <section className="dashboard-overview">
        <div className="overview-card">
          <div className="overview-header">
            <h2>تذاكري</h2>

            <button className="text-button">
              عرض الكل
            </button>
          </div>

          <div className="empty-state">
            <span className="empty-icon">🎫</span>

            <p>
              سيتم عرض التذاكر المسندة إليك هنا بعد ربط البيانات.
            </p>
          </div>
        </div>

        <div className="overview-card">
          <div className="overview-header">
            <h2>الحالة الحالية</h2>
          </div>

          <div className="status-summary">
            <div className="status-item">
              <span>مفتوحة</span>
              <strong>--</strong>
            </div>

            <div className="status-item">
              <span>محلولة</span>
              <strong>--</strong>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default AgentDashboard;
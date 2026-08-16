// This file renders the Documents page for Wasla.
// The page is currently a frontend UI placeholder.


// Backend document upload/search integration will be connected later.

import "./Documents.css";

function Documents() {
  return (
    <div className="documents-page">
      <header className="documents-header">
        <div>
          <p className="documents-eyebrow">Wasla</p>

          <h1>Documents</h1>

          <p className="documents-subtitle">
            إدارة المستندات الخاصة بالقسم
          </p>
        </div>

        <button className="upload-button">
          + رفع مستند
        </button>
      </header>

      <section className="documents-summary">
        <div className="summary-card">
          <span>إجمالي المستندات</span>
          <strong>--</strong>
        </div>

        <div className="summary-card">
          <span>المستندات النشطة</span>
          <strong>--</strong>
        </div>

        <div className="summary-card">
          <span>آخر تحديث</span>
          <strong>--</strong>
        </div>
      </section>

      <section className="documents-container">
        <div className="documents-toolbar">
          <div>
            <h2>المستندات</h2>

            <p>
              المستندات المستخدمة داخل نظام Wasla
            </p>
          </div>

          <input
            className="documents-search"
            type="text"
            placeholder="ابحث عن مستند..."
          />
        </div>

        <div className="documents-empty">
          <div className="documents-empty-icon">
            📄
          </div>

          <h3>لا توجد مستندات حالياً</h3>

          <p>
            سيتم عرض المستندات التي يتم رفعها هنا بعد ربط الصفحة بالـBackend.
          </p>

          <button className="upload-button secondary">
            رفع أول مستند
          </button>
        </div>
      </section>
    </div>
  );
}

export default Documents;
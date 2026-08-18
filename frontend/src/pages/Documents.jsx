// This file renders the Documents page for Wasla.
// It lets admins upload and browse department knowledge files.

import { useEffect, useRef, useState } from "react";
import { getDepartments, getDocuments, uploadDocument } from "../api";
import "./Documents.css";

function Documents({ token, user, onBack, initialDeptId }) {
  const fileInputRef = useRef(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [departments, setDepartments] = useState([]);
  const [selectedDeptId, setSelectedDeptId] = useState(initialDeptId ?? null);

  const isSuperadmin = user?.role === "superadmin";
  const isLockedDept = initialDeptId != null;

  useEffect(() => {
    async function loadDocuments() {
      try {
        const data = await getDocuments(token);
        setDocuments(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadDocuments();
  }, [token]);

  useEffect(() => {
    if (!isSuperadmin) return;
    async function loadDepartments() {
      try {
        const data = await getDepartments(token);
        setDepartments(data);
        if (initialDeptId != null) {
          setSelectedDeptId(initialDeptId);
        } else if (!selectedDeptId && data.length > 0) {
          setSelectedDeptId(data[0].id);
        }
      } catch (err) {
        setError(err.message);
      }
    }

    loadDepartments();
  }, [token, isSuperadmin]);

  function handleUploadClick() {
    fileInputRef.current?.click();
  }

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    if (isSuperadmin && !selectedDeptId) {
      setError("Please select a department first");
      return;
    }

    const deptId = isSuperadmin ? selectedDeptId : user.department_id;

    setUploading(true);
    setError("");

    try {
      const doc = await uploadDocument(file, token, deptId);
      setDocuments((prev) => [doc, ...prev]);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  const filtered = documents.filter((doc) => {
    const matchesSearch = doc.filename.toLowerCase().includes(search.toLowerCase());
    const matchesDept = !isSuperadmin || !selectedDeptId || doc.department_id === selectedDeptId;
    return matchesSearch && matchesDept;
  });

  const lastUpload = documents.length > 0 ? documents[0].uploaded_at : null;

  return (
    <div className="documents-page">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx"
        style={{ display: "none" }}
        onChange={handleFileChange}
      />

      <header className="documents-header">
        <div>
          <p className="documents-eyebrow">Wasla</p>

          <h1>Documents</h1>

          <p className="documents-subtitle">
            {isLockedDept
              ? `مستندات قسم: ${departments.find((d) => d.id === initialDeptId)?.name || ""}`
              : isSuperadmin
                ? "إدارة مستندات المعرفة لجميع الأقسام"
                : "إدارة المستندات الخاصة بقسمك"}
          </p>
        </div>

        <div className="documents-header-actions">
          {isSuperadmin && departments.length > 0 && (
            <select
              className="documents-dept-select"
              value={selectedDeptId ?? ""}
              onChange={(e) => setSelectedDeptId(Number(e.target.value))}
              disabled={isLockedDept}
            >
              {departments.map((dept) => (
                <option key={dept.id} value={dept.id}>
                  {dept.name}
                </option>
              ))}
            </select>
          )}

          <button className="back-button" onClick={onBack}>
            ← العودة
          </button>

          <button
            className="upload-button"
            onClick={handleUploadClick}
            disabled={uploading}
          >
            {uploading ? "جاري الرفع..." : "+ رفع مستند"}
          </button>
        </div>
      </header>

      {error && <p className="documents-error">{error}</p>}

      <section className="documents-summary">
        <div className="summary-card">
          <span>إجمالي المستندات</span>
          <strong>{documents.length}</strong>
        </div>

        <div className="summary-card">
          <span>المستندات النشطة</span>
          <strong>{documents.length}</strong>
        </div>

        <div className="summary-card">
          <span>آخر تحديث</span>
          <strong>
            {lastUpload
              ? new Date(lastUpload).toLocaleDateString("ar-EG")
              : "--"}
          </strong>
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
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        {loading && <p>Loading documents...</p>}

        {!loading && filtered.length === 0 && (
          <div className="documents-empty">
            <div className="documents-empty-icon">
              📄
            </div>

            <h3>لا توجد مستندات حالياً</h3>

            <p>
              اضغط على "رفع مستند" لإضافة أول ملف.
            </p>

            <button className="upload-button secondary" onClick={handleUploadClick}>
              رفع أول مستند
            </button>
          </div>
        )}

        {!loading && filtered.length > 0 && (
          <div className="documents-list">
            {filtered.map((doc) => (
              <div className="document-row" key={doc.id}>
                <span className="document-icon">📄</span>

                <div className="document-info">
                  <strong>{doc.filename}</strong>
                  <span>
                    {isSuperadmin && departments.length > 0
                      ? departments.find((d) => d.id === doc.department_id)?.name || `Dept #${doc.department_id}`
                      : new Date(doc.uploaded_at).toLocaleDateString("ar-EG")}
                  </span>
                  {isSuperadmin && (
                    <span>{new Date(doc.uploaded_at).toLocaleDateString("ar-EG")}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default Documents;

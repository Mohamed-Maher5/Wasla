// This file renders the Agent dashboard for the Wasla frontend.
// The Agent manages their assigned tickets and chats with the Wasla assistant.

import { useEffect, useMemo, useState } from "react";
import ChatPanel from "../components/ChatPanel";
import TicketCard from "../components/TicketCard";
import DashboardHeader from "./DashboardHeader";
import { getDepartments, getTickets, uploadDocument } from "../api";
import "./AgentDashboard.css";

function AgentDashboard({ token, user, onLogout }) {
  const [tickets, setTickets] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");

  const department = useMemo(
    () => departments.find((d) => d.id === user?.department_id) || null,
    [departments, user?.department_id],
  );

  useEffect(() => {
    async function loadTickets() {
      try {
        const [ticketData, departmentData] = await Promise.all([
          getTickets(token),
          getDepartments(token),
        ]);
        setTickets(ticketData);
        setDepartments(departmentData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadTickets();
  }, [token]);

  function handleStatusChange(ticketId, newStatus) {
    setTickets((currentTickets) =>
      currentTickets.map((ticket) =>
        ticket.id === ticketId ? { ...ticket, status: newStatus } : ticket,
      ),
    );
  }

  async function handleDocumentUpload(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || uploading) return;

    setUploading(true);
    setUploadMessage("");
    try {
      await uploadDocument(file, token, user.department_id);
      setUploadMessage("تم رفع الملف وإضافته إلى معرفة القسم.");
    } catch (err) {
      setUploadMessage(err.message || "فشل في رفع الملف.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="agent-dashboard">
      <DashboardHeader
        user={user}
        onLogout={onLogout}
        subtitle={department ? `قسم الـ ${department.name}` : ""}
      />

      <div className="agent-workspace">
        <div className="agent-tickets-column">
          <h2 className="ticket-list-title">التذاكر المسندة إليّ</h2>

          {loading && <p className="agent-loading-text">جاري تحميل التذاكر...</p>}
          {error && <p className="agent-error-text">خطأ: {error}</p>}

          {!loading && !error && tickets.length === 0 && (
            <p className="agent-empty-text">لا توجد تذاكر مسندة إليك.</p>
          )}

          <div className="ticket-list">
            {tickets.map((ticket) => (
              <TicketCard
                key={ticket.id}
                ticket={ticket}
                token={token}
                onStatusChange={handleStatusChange}
              />
            ))}
          </div>
        </div>

        <div className="agent-chat-column">
          <div className="agent-upload-box">
            <label className="agent-upload-label">
              {uploading ? "جاري رفع الملف..." : "رفع ملف معرفة للقسم"}
              <input
                type="file"
                accept=".txt,.pdf,.docx,.png,.jpg,.jpeg,.bmp,.tiff,.tif,.webp"
                onChange={handleDocumentUpload}
                disabled={uploading}
              />
            </label>
            <span>TXT، PDF، DOCX أو صورة</span>
            {uploadMessage && <p>{uploadMessage}</p>}
          </div>
          <ChatPanel token={token} user={user} fullWidth />
        </div>
      </div>
    </div>
  );
}

export default AgentDashboard;

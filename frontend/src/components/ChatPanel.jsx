import { useState, useRef, useEffect } from "react";
import {
  chatQuery,
  chatFeedback,
  getConversations,
  getConversationDetail,
  deleteConversation,
} from "../api";
import "./ChatPanel.css";

const GREETING = {
  type: "assistant",
  text: "جاهز أساعدك في ترتيب ملاحظات التذكرة.",
};

function ChatPanel({ token, user, fullWidth, departmentId }) {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState([GREETING]);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function refreshConversations() {
    try {
      const list = await getConversations(token, departmentId);
      setConversations(list);
    } catch {
      // sidebar list is non-critical — fail silently
    }
  }

  useEffect(() => {
    refreshConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, departmentId]);

  async function openConversation(id) {
    setError("");
    try {
      const detail = await getConversationDetail(id, token);
      const restored = detail.messages.flatMap((item) => [
        { type: "user", text: item.question },
        {
          type: "assistant",
          text: item.answer,
          logId: item.log_id,
          feedbackSent: item.feedback || undefined,
        },
      ]);
      setMessages(restored.length ? restored : [GREETING]);
      setConversationId(detail.id);
    } catch (err) {
      setError(err.message);
    }
  }

  function startNewConversation() {
    setMessages([GREETING]);
    setConversationId(null);
    setError("");
  }

  async function handleDeleteConversation(id, event) {
    event.stopPropagation();
    try {
      await deleteConversation(id, token);
      if (id === conversationId) {
        startNewConversation();
      }
      refreshConversations();
    } catch (err) {
      setError(err.message);
    }
  }

  // Recent turns of the CURRENT conversation, sent so the model keeps context.
  function buildHistoryPayload(allMessages) {
    return allMessages
      .filter((m) => m.text && m !== GREETING)
      .slice(-8)
      .map((m) => ({
        role: m.type === "user" ? "user" : "assistant",
        content: m.text,
      }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const text = draft.trim();
    if (!text || loading) return;

    setDraft("");
    setError("");
    const historyPayload = buildHistoryPayload(messages);
    setMessages((prev) => [...prev, { type: "user", text }]);
    setLoading(true);

    try {
      const data = await chatQuery(text, token, departmentId, historyPayload, conversationId);
      setMessages((prev) => [
        ...prev,
        {
          type: "assistant",
          text: data.answer,
          sources: data.sources,
          logId: data.log_id,
        },
      ]);
      if (data.conversation_id !== conversationId) {
        setConversationId(data.conversation_id);
      }
      refreshConversations();
    } catch (err) {
      setError(err.message);
      setMessages((prev) => [
        ...prev,
        { type: "assistant", text: "حدث خطأ أثناء المعالجة. حاول مرة أخرى." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleFeedback(logId, feedback) {
    try {
      await chatFeedback({ log_id: logId, feedback }, token);
      setMessages((prev) =>
        prev.map((m) =>
          m.logId === logId ? { ...m, feedbackSent: feedback } : m
        )
      );
    } catch {
      // silently ignore
    }
  }

  const panelClass = fullWidth ? "chat-panel chat-panel--full" : "chat-panel";

  return (
    <div className={`chat-panel-layout ${sidebarOpen ? "" : "chat-panel-layout--collapsed"}`}>
      <div className="chat-sidebar">
        <div className="chat-sidebar-header">
          <button className="chat-sidebar-toggle" onClick={() => setSidebarOpen((v) => !v)}>
            {sidebarOpen ? "«" : "»"}
          </button>
          {sidebarOpen && (
            <button className="chat-new-btn" onClick={startNewConversation}>
              + محادثة جديدة
            </button>
          )}
        </div>

        {sidebarOpen && (
          <div className="chat-conversation-list">
            {conversations.length === 0 && (
              <p className="chat-conversation-empty">لا توجد محادثات سابقة</p>
            )}
            {conversations.map((c) => (
              <div
                key={c.id}
                className={`chat-conversation-item ${c.id === conversationId ? "active" : ""}`}
                onClick={() => openConversation(c.id)}
              >
                <span className="chat-conversation-title">{c.title}</span>
                <button
                  className="chat-conversation-delete"
                  onClick={(e) => handleDeleteConversation(c.id, e)}
                  title="حذف المحادثة"
                >
                  🗑
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <aside className={panelClass} aria-label="Agent chat panel">
        <div className="chat-panel-header">
          <h2>مساعد Wasla</h2>
        </div>

        <div className="chat-messages">
          {messages.map((message, index) => (
            <div key={index} className={`chat-message ${message.type}`}>
              <div className="chat-message-text">{message.text}</div>

              {message.sources && message.sources.length > 0 && (
                <div className="chat-sources">
                  <span className="chat-sources-label">المصادر:</span>
                  {message.sources.map((src) => (
                    <span key={src.chunk_id} className="chat-source-chip">
                      {src.filename}
                      {src.page_number ? ` (ص. ${src.page_number})` : ""}
                    </span>
                  ))}
                </div>
              )}

              {message.type === "assistant" && message.logId && (
                <div className="chat-feedback">
                  {message.feedbackSent ? (
                    <span className="chat-feedback-sent">
                      {message.feedbackSent === "up" ? "شكرًا" : "تم التقييم"}
                    </span>
                  ) : (
                    <>
                      <button
                        className="chat-feedback-btn"
                        onClick={() => handleFeedback(message.logId, "up")}
                        title="إجابة مفيدة"
                      >
                        👍
                      </button>
                      <button
                        className="chat-feedback-btn"
                        onClick={() => handleFeedback(message.logId, "down")}
                        title="إجابة غير مفيدة"
                      >
                        👎
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="chat-message assistant chat-loading">
              <span className="chat-loading-dots">
                <span>.</span><span>.</span><span>.</span>
              </span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {error && <div className="chat-error">{error}</div>}

        <form className="chat-form" onSubmit={handleSubmit}>
          <input
            type="text"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="اكتب سؤالك هنا..."
            disabled={loading}
          />
          <button type="submit" disabled={!draft.trim() || loading}>
            {loading ? "جاري..." : "إرسال"}
          </button>
        </form>
      </aside>
    </div>
  );
}

export default ChatPanel;
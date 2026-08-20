import { useState, useRef, useEffect } from "react";
import { chatQuery, chatFeedback } from "../api";
import "./ChatPanel.css";

function ChatPanel({ token, user, fullWidth, departmentId }) {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState([
    {
      type: "assistant",
      text: "جاهز أساعدك في ترتيب ملاحظات التذكرة.",
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(event) {
    event.preventDefault();

    const text = draft.trim();
    if (!text || loading) return;

    setDraft("");
    setError("");
    setMessages((prev) => [...prev, { type: "user", text }]);
    setLoading(true);

    try {
      const data = await chatQuery(text, token, departmentId);
      setMessages((prev) => [
        ...prev,
        {
          type: "assistant",
          text: data.answer,
          sources: data.sources,
          logId: data.log_id,
        },
      ]);
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
    <aside className={panelClass} aria-label="Agent chat panel">
      <div className="chat-panel-header">
        <h2>مساعد ( وَصْلَة )</h2>
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
  );
}

export default ChatPanel;

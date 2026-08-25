import { useState, useRef, useEffect } from "react";
import {
  chatQuery,
  chatFeedback,
  chatWebSearch,
  getConversations,
  getConversationDetail,
  deleteConversation,
  getPersonas,
  transcribeVoice,
  speakText,
  executeSqlQuery,
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
  const [personas, setPersonas] = useState([]);
  const [persona, setPersona] = useState("general");
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [speakingIndex, setSpeakingIndex] = useState(null);
  const messagesEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioPlayerRef = useRef(null);

  useEffect(() => {
    getPersonas(token)
      .then(setPersonas)
      .catch(() => {
        // dropdown just falls back to "general" if this fails
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

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
      if (detail.persona) {
        setPersona(detail.persona);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  function startNewConversation() {
    setMessages([GREETING]);
    setConversationId(null);
    setPersona("general");
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
      const data = await chatQuery(text, token, departmentId, historyPayload, conversationId, persona);
      setMessages((prev) => [
        ...prev,
        {
          type: "assistant",
          text: data.answer,
          sources: data.sources,
          logId: data.log_id,
          offerWebSearch: data.offer_web_search,
          pendingQuestion: text,
          pendingHistory: historyPayload,
          sqlQuery: data.sql_query || null,
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

  async function handleWebSearchConfirm(index) {
    const target = messages[index];
    if (!target) return;

    setMessages((prev) =>
      prev.map((m, i) => (i === index ? { ...m, offerWebSearch: false } : m)),
    );
    setLoading(true);
    setError("");

    try {
      const data = await chatWebSearch(
        target.pendingQuestion,
        token,
        departmentId,
        target.pendingHistory || [],
        conversationId,
      );
      setMessages((prev) => [
        ...prev,
        {
          type: "assistant",
          text: data.answer,
          sources: data.sources,
          logId: data.log_id,
        },
      ]);
      refreshConversations();
    } catch (err) {
      setError(err.message);
      setMessages((prev) => [
        ...prev,
        { type: "assistant", text: "تعذر البحث في الإنترنت. حاول مرة أخرى." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleRunSql(index) {
    const target = messages[index];
    if (!target?.sqlQuery || target.sqlQuery.executed) return;

    setMessages((prev) =>
      prev.map((m, i) =>
        i === index ? { ...m, sqlQuery: { ...m.sqlQuery, running: true } } : m,
      ),
    );
    setError("");

    try {
      const data = await executeSqlQuery(
        target.sqlQuery.pending_id,
        token,
        conversationId,
      );
      setMessages((prev) => [
        ...prev.map((m, i) =>
          i === index
            ? { ...m, sqlQuery: { ...m.sqlQuery, executed: true, running: false } }
            : m,
        ),
        {
          type: "assistant",
          sqlResult: data,
          logId: data.log_id,
        },
      ]);
      refreshConversations();
    } catch (err) {
      setError(err.message);
      setMessages((prev) =>
        prev.map((m, i) =>
          i === index ? { ...m, sqlQuery: { ...m.sqlQuery, running: false } } : m,
        ),
      );
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

  // --- Voice input (mic -> record -> transcribe -> fill the draft) ---
  async function startRecording() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      recorder.onstop = async () => {
        // Release the mic regardless of what happens next.
        stream.getTracks().forEach((track) => track.stop());

        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        setTranscribing(true);
        try {
          const { text } = await transcribeVoice(audioBlob, token);
          setDraft((prev) => (prev ? `${prev} ${text}` : text));
        } catch (err) {
          setError(err.message);
        } finally {
          setTranscribing(false);
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setError("تعذر الوصول إلى الميكروفون");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  }

  function toggleRecording() {
    if (recording) {
      stopRecording();
    } else {
      startRecording();
    }
  }

  // --- Voice output (speaker button -> fetch narrated audio -> play it) ---
  async function handleSpeak(index, text) {
    // Toggle off if this message is already playing.
    if (speakingIndex === index) {
      audioPlayerRef.current?.pause();
      setSpeakingIndex(null);
      return;
    }

    setError("");
    try {
      const audioUrl = await speakText(text, token);
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
      }
      const player = new Audio(audioUrl);
      audioPlayerRef.current = player;
      setSpeakingIndex(index);
      player.onended = () => setSpeakingIndex(null);
      player.onerror = () => setSpeakingIndex(null);
      await player.play();
    } catch (err) {
      setError(err.message);
      setSpeakingIndex(null);
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
          <select
            className="chat-persona-select"
            value={persona}
            disabled={conversationId != null}
            onChange={(event) => setPersona(event.target.value)}
            title={
              conversationId != null
                ? "الشخصية ثابتة لهذه المحادثة — ابدأ محادثة جديدة لتغييرها"
                : "اختر شخصية المساعد"
            }
          >
            {(personas.length ? personas : [{ id: "general", label: "عام (افتراضي)" }]).map(
              (p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ),
            )}
          </select>
        </div>

        <div className="chat-messages">
          {messages.map((message, index) => (
            <div key={index} className={`chat-message ${message.type}`}>
              <div className="chat-message-text">
                {message.sqlResult ? (
                  <div className="chat-sql-result">
                    <div className="chat-sql-result-meta">
                      {message.sqlResult.row_count} صف
                    </div>
                    <table className="chat-sql-result-table">
                      <thead>
                        <tr>
                          {message.sqlResult.columns.map((c) => (
                            <th key={c}>{c}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {message.sqlResult.rows.map((row, ri) => (
                          <tr key={ri}>
                            {row.map((v, ci) => (
                              <td key={ci}>{String(v)}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  message.text
                )}
                {message.type === "assistant" && message.text && (
                  <button
                    type="button"
                    className="chat-speak-btn"
                    onClick={() => handleSpeak(index, message.text)}
                    title="استمع للإجابة"
                  >
                    {speakingIndex === index ? "⏸" : "🔊"}
                  </button>
                )}
              </div>

              {message.sources && message.sources.length > 0 && (
                <div className="chat-sources">
                  <span className="chat-sources-label">المصادر:</span>
                  {message.sources.map((src, i) =>
                    src.source_type === "web" ? (
                      <a
                        key={src.url || i}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="chat-source-chip chat-source-chip--web"
                      >
                        🌐 {src.title || src.url}
                      </a>
                    ) : (
                      <span key={src.chunk_id} className="chat-source-chip">
                        {src.filename}
                        {src.page_number ? ` (ص. ${src.page_number})` : ""}
                      </span>
                    ),
                  )}
                </div>
              )}

              {message.sqlQuery && !message.sqlQuery.executed && (
                <div className="chat-web-search-offer">
                  <button
                    type="button"
                    className="chat-web-search-btn"
                    disabled={loading || message.sqlQuery.running}
                    onClick={() => handleRunSql(index)}
                  >
                    {message.sqlQuery.running ? "جاري التنفيذ..." : "تنفيذ الاستعلام"}
                  </button>
                </div>
              )}

              {message.offerWebSearch && (
                <div className="chat-web-search-offer">
                  <span>لم أجد إجابة في المستندات. هل تريد البحث في الإنترنت؟</span>
                  <button
                    type="button"
                    className="chat-web-search-btn"
                    disabled={loading}
                    onClick={() => handleWebSearchConfirm(index)}
                  >
                    ابحث في الإنترنت
                  </button>
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
            placeholder={transcribing ? "جاري تحويل الصوت إلى نص..." : "اكتب سؤالك هنا..."}
            disabled={loading || transcribing}
          />
          <button
            type="button"
            className={`chat-mic-btn ${recording ? "chat-mic-btn--recording" : ""}`}
            onClick={toggleRecording}
            disabled={loading || transcribing}
            title={recording ? "إيقاف التسجيل" : "تسجيل رسالة صوتية"}
          >
            {recording ? "⏹" : "🎤"}
          </button>
          <button type="submit" disabled={!draft.trim() || loading || transcribing}>
            {loading ? "جاري..." : "إرسال"}
          </button>
        </form>
      </aside>
    </div>
  );
}

export default ChatPanel;
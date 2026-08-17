// This file renders the agent chatbot panel for the Wasla frontend.
// It gives support users a place to ask department-specific knowledge questions.


import { useState } from "react";
import "./ChatPanel.css";

function ChatPanel() {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState([
    {
      type: "assistant",
      text: "جاهز أساعدك في ترتيب ملاحظات التذكرة.",
    },
  ]);

  function handleSubmit(event) {
    event.preventDefault();

    const text = draft.trim();
    if (!text) {
      return;
    }

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        type: "user",
        text,
      },
      {
        type: "assistant",
        text: "تمت إضافة رسالتك محليًا. سيتم توصيل المساعد الحقيقي لاحقًا.",
      },
    ]);
    setDraft("");
  }

  return (
    <aside className="chat-panel" aria-label="Agent chat panel">
      <div className="chat-panel-header">
        <h2>مساعد Wasla</h2>
      </div>

      <div className="chat-messages">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`chat-message ${message.type}`}
          >
            {message.text}
          </div>
        ))}
      </div>

      <form className="chat-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="اكتب رسالة..."
        />

        <button type="submit" disabled={!draft.trim()}>
          إرسال
        </button>
      </form>
    </aside>
  );
}

export default ChatPanel;

// This file renders the agent chatbot panel for the Wasla frontend.
// It gives support users a place to ask department-specific knowledge questions.


import { useState } from "react";
import { askChatbot } from "../api";
import "./ChatPanel.css";

function ChatPanel() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();

    if (!question.trim() || loading) {
      return;
    }

    const currentQuestion = question.trim();

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        type: "user",
        text: currentQuestion,
      },
    ]);

    setQuestion("");
    setLoading(true);

    try {
      const response = await askChatbot(currentQuestion);

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          type: "bot",
          text: response.answer,
        },
      ]);
    } catch (error) {
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          type: "bot",
          text: error.message,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chat-panel">
      <h2>مساعد Wasla</h2>

      <div className="chat-messages">
        {messages.length === 0 && (
          <p className="chat-empty">
            اكتب سؤالك للمساعد.
          </p>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={`chat-message ${message.type}`}
          >
            {message.text}
          </div>
        ))}

        {loading && (
          <div className="chat-message bot">
            جاري التفكير...
          </div>
        )}
      </div>

      <form className="chat-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="اكتب سؤالك..."
          disabled={loading}
        />

        <button type="submit" disabled={loading || !question.trim()}>
          إرسال
        </button>
      </form>
    </div>
  );
}

export default ChatPanel;
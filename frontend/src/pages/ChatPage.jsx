import { useState } from "react";
import ChatPanel from "../components/ChatPanel";
import "./ChatPage.css";

function ChatPage({ token, user, onBack }) {
  return (
    <div className="chat-page">
      <div className="chat-page-header">
        <button className="back-button" onClick={onBack}>
          → العودة
        </button>
        <h1>مساعد Wasla</h1>
      </div>

      <div className="chat-page-body">
        <ChatPanel token={token} user={user} fullWidth />
      </div>
    </div>
  );
}

export default ChatPage;

import { useState } from "react";

import Login from "./pages/Login";
import AdminDashboard from "./pages/AdminDashboard";
import AgentDashboard from "./pages/AgentDashboard";
import ChatPage from "./pages/ChatPage";
import Documents from "./pages/Documents";
import SuperadminDashboard from "./pages/SuperadminDashboard";
import TicketDetail from "./pages/TicketDetail";

function App() {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [selectedTicketId, setSelectedTicketId] = useState(null);
  const [view, setView] = useState("dashboard");

  function handleLogin(accessToken, currentUser) {
    setToken(accessToken);
    setUser(currentUser);
  }

  function handleTicketClick(ticketId) {
    setSelectedTicketId(ticketId);
  }

  function handleBack() {
    setSelectedTicketId(null);
  }

  if (!token) {
    return <Login onLogin={handleLogin} />;
  }

  if (selectedTicketId !== null) {
    return (
      <TicketDetail
        ticketId={selectedTicketId}
        token={token}
        user={user}
        onBack={handleBack}
      />
    );
  }

  if (user?.role === "agent") {
    return (
      <AgentDashboard
        token={token}
        user={user}
        onTicketClick={handleTicketClick}
      />
    );
  }

  if (view === "documents") {
    return (
      <Documents
        token={token}
        user={user}
        onBack={() => setView("dashboard")}
      />
    );
  }

  if (view === "chat") {
    return (
      <ChatPage
        token={token}
        user={user}
        onBack={() => setView("dashboard")}
      />
    );
  }

  if (user?.role === "admin") {
    return (
      <AdminDashboard
        token={token}
        user={user}
        onNavigate={setView}
        onTicketClick={handleTicketClick}
      />
    );
  }

  if (user?.role === "superadmin") {
    return (
      <SuperadminDashboard
        token={token}
        user={user}
        onNavigate={setView}
        onTicketClick={handleTicketClick}
      />
    );
  }

  return <Login onLogin={handleLogin} />;
}

export default App;

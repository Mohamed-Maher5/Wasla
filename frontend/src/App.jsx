import { useState } from "react";

import Login from "./pages/Login";
import AdminDashboard from "./pages/AdminDashboard";
import AgentDashboard from "./pages/AgentDashboard";
import Documents from "./pages/Documents";
import SuperadminDashboard from "./pages/SuperadminDashboard";

function App() {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [view, setView] = useState("dashboard");

  function handleLogin(accessToken, currentUser) {
    setToken(accessToken);
    setUser(currentUser);
  }

  function handleLogout() {
    setToken(null);
    setUser(null);
    setView("dashboard");
  }

  if (!token) {
    return <Login onLogin={handleLogin} />;
  }

  if (user?.role === "agent") {
    return (
      <AgentDashboard token={token} user={user} onLogout={handleLogout} />
    );
  }

  // Superadmin no longer has access to the chat query or document upload
  // views — redirect them to their own dashboard instead of the removed pages.
  if (user?.role === "superadmin") {
    return (
      <SuperadminDashboard
        token={token}
        user={user}
        onLogout={handleLogout}
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

  if (user?.role === "admin") {
    return (
      <AdminDashboard
        token={token}
        user={user}
        onLogout={handleLogout}
      />
    );
  }

  return <Login onLogin={handleLogin} />;
}

export default App;
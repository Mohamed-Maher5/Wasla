// This file is the root of the Wasla frontend application.
// It controls the logged-in / logged-out flow and ticket navigation.

import { useState } from "react";

import Login from "./pages/Login";
import TicketList from "./pages/TicketList";
import TicketDetail from "./pages/TicketDetail";

function App() {
  const [token, setToken] = useState(null);
  const [selectedTicketId, setSelectedTicketId] = useState(null);

  function handleLogin(accessToken) {
    setToken(accessToken);
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
        onBack={handleBack}
      />
    );
  }

  return <TicketList onTicketClick={handleTicketClick} />;
}

export default App;
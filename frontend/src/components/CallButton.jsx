// This file renders the customer call action for the Wasla frontend.
// It gives support users a clear way to trigger resolution verification outreach.


import { useState } from "react";
import { callCustomer } from "../api";
import "./CallButton.css";

function CallButton({ ticketId }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState("");

  async function handleCall() {
    setLoading(true);
    setResult("");

    try {
      const response = await callCustomer(ticketId);
      setResult(response.outcome);
    } catch (error) {
      setResult(error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="call-section">
      <button
        className="call-button"
        onClick={handleCall}
        disabled={loading}
      >
        {loading ? "جاري الاتصال..." : "الاتصال بالعميل"}
      </button>

      {result && <p className="call-result">{result}</p>}
    </div>
  );
}

export default CallButton;
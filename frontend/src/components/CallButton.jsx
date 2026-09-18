import { useEffect, useRef, useState } from "react";
import { callCustomer, cancelCall, getCallStatus, getTicket } from "../api";
import "./CallButton.css";

const POLL_INTERVAL_MS = 3000;
const MAX_WAIT_MS = 90000;

function CallButton({ ticketId, token, disabled, onCallFinished, initialCallCount = 0, onCallCountChange }) {
  const [calling, setCalling] = useState(false);
  const pollTimer = useRef(null);
  const timeoutTimer = useRef(null);
  const callIdRef = useRef(null);

  useEffect(() => {
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
      if (timeoutTimer.current) clearTimeout(timeoutTimer.current);
    };
  }, []);

  async function refreshCallCount() {
    try {
      const ticket = await getTicket(ticketId, token);
      onCallCountChange?.(ticket.call_count ?? 0);
    } catch {
      // keep whatever count we already have
    }
  }

  async function pollUntilFinished(callId) {
    callIdRef.current = callId;
    pollTimer.current = setInterval(async () => {
      try {
        const attempt = await getCallStatus(callId, token);
        if (attempt.outcome) {
          clearInterval(pollTimer.current);
          clearTimeout(timeoutTimer.current);
          finishCall(attempt.outcome);
        }
      } catch {
        // keep polling
      }
    }, POLL_INTERVAL_MS);

    timeoutTimer.current = setTimeout(() => {
      clearInterval(pollTimer.current);
      setCalling(false);
      refreshCallCount();
    }, MAX_WAIT_MS);
  }

  async function finishCall(outcome) {
    if (outcome === "cancelled") {
      setCalling(false);
      refreshCallCount();
      return;
    }
    if (outcome === "resolved") {
      onCallFinished?.("resolved");
    } else if (outcome === "not_resolved") {
      onCallFinished?.("unresolved");
    }
    setCalling(false);
    refreshCallCount();
  }

  async function handleCancel() {
    if (pollTimer.current) clearInterval(pollTimer.current);
    if (timeoutTimer.current) clearTimeout(timeoutTimer.current);
    const callId = callIdRef.current;

    if (callId) {
      try {
        await cancelCall(callId, token);
      } catch {
        // even if hangup fails, stop the UI polling
      }
    }

    setCalling(false);
    refreshCallCount();
  }

  async function handleCall() {
    setCalling(true);

    try {
      const response = await callCustomer(ticketId, token);
      refreshCallCount();
      pollUntilFinished(response.id);
    } catch (error) {
      setCalling(false);
      refreshCallCount();
    }
  }

  return (
    <div className="call-section">
      {calling ? (
        <div className="call-in-progress">
          <button className="call-button calling" disabled>
            جاري الاتصال بالعميل...
          </button>
          <button className="call-cancel-btn" onClick={handleCancel} title="إلغاء الاتصال">
            ✕
          </button>
        </div>
      ) : (
        <button
          className="call-button"
          onClick={handleCall}
          disabled={disabled}
        >
          الاتصال بالعميل
        </button>
      )}
    </div>
  );
}

export default CallButton;
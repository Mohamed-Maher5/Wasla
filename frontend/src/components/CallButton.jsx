// This file renders the customer call action for the Wasla frontend.
// It triggers the verification call and keeps the button locked until the
// call finishes, then reports the new ticket state to the parent card.

import { useEffect, useRef, useState } from "react";
import { callCustomer, getCallStatus } from "../api";
import "./CallButton.css";

const POLL_INTERVAL_MS = 3000;
const MAX_WAIT_MS = 90000;

function CallButton({ ticketId, token, onCallFinished }) {
  const [calling, setCalling] = useState(false);
  const [result, setResult] = useState("");
  const pollTimer = useRef(null);
  const timeoutTimer = useRef(null);

  useEffect(() => {
    return () => {
      if (pollTimer.current) {
        clearInterval(pollTimer.current);
      }
      if (timeoutTimer.current) {
        clearTimeout(timeoutTimer.current);
      }
    };
  }, []);

  async function pollUntilFinished(callId) {
    pollTimer.current = setInterval(async () => {
      try {
        const attempt = await getCallStatus(callId, token);
        if (attempt.outcome) {
          clearInterval(pollTimer.current);
          clearTimeout(timeoutTimer.current);
          finishCall(attempt.outcome);
        }
      } catch {
        // keep polling; the call may still be in progress
      }
    }, POLL_INTERVAL_MS);

    timeoutTimer.current = setTimeout(() => {
      clearInterval(pollTimer.current);
      setCalling(false);
      setResult("لم يتم تأكيد انتهاء الاتصال");
    }, MAX_WAIT_MS);
  }

  async function finishCall(outcome) {
    if (outcome === "resolved") {
      setResult("انتهى الاتصال: تم حل المشكلة");
      onCallFinished?.("resolved");
    } else if (outcome === "not_resolved") {
      setResult("انتهى الاتصال: لم يتم حل المشكلة");
      onCallFinished?.("unresolved");
    } else {
      setResult("انتهى الاتصال: غير واضح");
    }
    setCalling(false);
  }

  async function handleCall() {
    setCalling(true);
    setResult("");

    try {
      const response = await callCustomer(ticketId, token);
      pollUntilFinished(response.id);
    } catch (error) {
      setCalling(false);
      setResult(error.message);
    }
  }

  return (
    <div className="call-section">
      <button
        className="call-button"
        onClick={handleCall}
        disabled={calling}
      >
        {calling ? "يتم بدأ التصال" : "الاتصال بالعميل"}
      </button>

      {result && <p className="call-result">{result}</p>}
    </div>
  );
}

export default CallButton;
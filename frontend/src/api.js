// This file is the single bridge between the Wasla frontend and backend data layer.
// Every screen uses it to request platform data instead of reaching into transport details.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
      ...options.headers,
    },
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw new Error(data?.detail || "Request failed");
  }

  return data;
}

export async function login(credentials) {
  const token = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
  const user = await request("/auth/me", { token: token.access_token });

  return {
    ...token,
    user,
  };
}

export async function getTickets(token) {
  return request("/tickets", { token });
}

export async function getTicket(id, token) {
  return request(`/tickets/${id}`, { token });
}

export async function createTicket(data, token) {
  return request("/tickets", {
    method: "POST",
    token,
    body: JSON.stringify(data),
  });
}

export async function callCustomer(ticketId, token) {
  const ticket = await getTicket(ticketId, token);
  return request("/telephony/trigger", {
    method: "POST",
    token,
    body: JSON.stringify({ phone_number: ticket.client_phone_number }),
  });
}

export async function getCallStatus(callId, token) {
  return request(`/telephony/status/${callId}`, { token });
}

export async function resolveTicket(ticketId, token) {
  return updateTicketStatus(ticketId, "resolved", token);
}

export async function unresolveTicket(ticketId, token) {
  return updateTicketStatus(ticketId, "unresolved", token);
}

export async function getDepartments(token) {
  return request("/departments", { token });
}

export async function createDepartment(data, token) {
  return request("/departments", {
    method: "POST",
    token,
    body: JSON.stringify(data),
  });
}

export async function getUsers(token) {
  return request("/users", { token });
}

export async function createUser(data, token) {
  return request("/users", {
    method: "POST",
    token,
    body: JSON.stringify(data),
  });
}

export async function uploadDocument(file, token, departmentId) {
  const formData = new FormData();
  formData.append("file", file);
  // Only send department_id if one is provided (superadmin chooses, admin doesn't).
  if (departmentId != null) {
    formData.append("department_id", departmentId);
  }

  const response = await fetch(`${API_BASE_URL}/chat/documents`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw new Error(data?.detail || "Upload failed");
  }

  return data;
}

export async function getDocuments(token, departmentId) {
  const query = departmentId != null ? `?department_id=${departmentId}` : "";
  return request(`/chat/documents${query}`, { token });
}

export async function getConversations(token, departmentId) {
  const query = departmentId != null ? `?department_id=${departmentId}` : "";
  return request(`/chat/conversations${query}`, { token });
}

export async function getConversationDetail(conversationId, token) {
  return request(`/chat/conversations/${conversationId}`, { token });
}

export async function deleteConversation(conversationId, token) {
  return request(`/chat/conversations/${conversationId}`, {
    method: "DELETE",
    token,
  });
}

export async function chatQuery(question, token, departmentId, history = [], conversationId = null, persona = "general") {
  const body = { question, history, conversation_id: conversationId, persona };
  if (departmentId != null) {
    body.department_id = departmentId;
  }
  return request("/chat/query", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function getPersonas(token) {
  return request("/chat/personas", { token });
}

export async function generateSqlQuery(question, token, departmentId) {
  const body = { question };
  if (departmentId != null) {
    body.department_id = departmentId;
  }
  return request("/chat/sql/generate", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

export async function executeSqlQuery(pendingId, token, conversationId = null) {
  return request("/chat/sql/execute", {
    method: "POST",
    token,
    body: JSON.stringify({ pending_id: pendingId, conversation_id: conversationId }),
  });
}

export async function chatFeedback(data, token) {
  return request("/chat/feedback", {
    method: "POST",
    token,
    body: JSON.stringify(data),
  });
}

export async function chatWebSearch(question, token, departmentId, history = [], conversationId) {
  const body = { question, history, conversation_id: conversationId };
  if (departmentId != null) {
    body.department_id = departmentId;
  }
  return request("/chat/web-search", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
}

// Uploads a recorded voice message (Blob from MediaRecorder) and returns
// { text } with the transcription, to drop into the chat input.
export async function transcribeVoice(audioBlob, token) {
  const formData = new FormData();
  formData.append("file", audioBlob, "voice-message.webm");

  const response = await fetch(`${API_BASE_URL}/chat/voice/transcribe`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw new Error(data?.detail || "Transcription failed");
  }

  return data;
}

// Requests narrated audio for a piece of text and returns a playable
// object URL. Caller is responsible for revoking it when done.
export async function speakText(text, token) {
  const response = await fetch(`${API_BASE_URL}/chat/voice/speak`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    let detail = "Speech synthesis failed";
    try {
      const data = await response.json();
      detail = data?.detail || detail;
    } catch {
      // response wasn't JSON — keep default message
    }
    throw new Error(detail);
  }

  const audioBlob = await response.blob();
  return URL.createObjectURL(audioBlob);
}

function updateTicketStatus(ticketId, status, token) {
  return request(`/tickets/${ticketId}/status`, {
    method: "PATCH",
    token,
    body: JSON.stringify({ status }),
  });
}
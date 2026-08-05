import React, { useState, useEffect } from "react";

const API_BASE = "http://localhost:8000/api";

export default function PlainEmailDashboard() {
  const [threads, setThreads] = useState([]);
  const [selectedThreadId, setSelectedThreadId] = useState(null);
  const [threadDetails, setThreadDetails] = useState(null);
  const [customerHistory, setCustomerHistory] = useState(null);

  // 1. Load Unfinished Threads
  const fetchUnfinishedThreads = async () => {
    try {
      const res = await fetch(`${API_BASE}/threads/unfinished`);
      const data = await res.json();
      setThreads(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchUnfinishedThreads();
  }, []);

  // 2. Load Single Thread & Customer Profile
  const loadThread = async (threadId) => {
    setSelectedThreadId(threadId);
    try {
      const res = await fetch(`${API_BASE}/threads/${threadId}`);
      const data = await res.json();
      setThreadDetails(data);

      if (data.customer?.email) {
        fetchCustomerHistory(data.customer.email);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // 3. Load Customer History
  const fetchCustomerHistory = async (email) => {
    try {
      const res = await fetch(`${API_BASE}/customers/${email}/history`);
      const data = await res.json();
      setCustomerHistory(data);
    } catch (err) {
      console.error(err);
    }
  };

  // 4. Toggle Finished Status
  const toggleThreadStatus = async () => {
    if (!selectedThreadId || !threadDetails) return;

    try {
      await fetch(`${API_BASE}/threads/${selectedThreadId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_finished: !threadDetails.is_finished }),
      });

      fetchUnfinishedThreads();
      loadThread(selectedThreadId);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ display: "flex", gap: "20px" }}>
      {/* Column 1: Action Queue */}
      <div>
        <h3>Action Queue ({threads.length})</h3>
        <button onClick={fetchUnfinishedThreads}>Refresh</button>
        <ul>
          {threads.map((t) => (
            <li key={t.provider_thread_id} style={{ marginBottom: "10px" }}>
              <strong>{t.customer_name || "Unknown"}</strong> ({t.customer_email})
              <br />
              <button onClick={() => loadThread(t.provider_thread_id)}>
                View Thread
              </button>
            </li>
          ))}
        </ul>
      </div>

      <hr />

      {/* Column 2: Thread Messages */}
      <div>
        <h3>Conversation</h3>
        {threadDetails ? (
          <div>
            <p>
              <strong>Thread ID:</strong> {threadDetails.provider_thread_id}
            </p>
            <button onClick={toggleThreadStatus}>
              {threadDetails.is_finished ? "Reopen Thread" : "Mark as Finished"}
            </button>
            <div>
              {threadDetails.messages.map((m, idx) => (
                <div key={idx} style={{ border: "1px solid black", padding: "10px", margin: "10px 0" }}>
                  <p><strong>From:</strong> {m.sender}</p>
                  <p><strong>Subject:</strong> {m.subject}</p>
                  <p>{m.body}</p>
                  <small>{new Date(m.sent_at).toLocaleString()}</small>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p>Select a thread from the left.</p>
        )}
      </div>

      <hr />

      {/* Column 3: Customer History Sidebar */}
      <div>
        <h3>Customer History</h3>
        {customerHistory ? (
          <div>
            <p><strong>Name:</strong> {customerHistory.customer?.name}</p>
            <p><strong>Email:</strong> {customerHistory.customer?.email}</p>
            <h4>Logs</h4>
            <ul>
              {customerHistory.history.map((h, idx) => (
                <li key={idx}>
                  <strong>Category:</strong> {h.category}
                  {h.event_date && <div>Event: {new Date(h.event_date).toLocaleDateString()}</div>}
                  <div>Logged: {new Date(h.created_at).toLocaleDateString()}</div>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p>No customer selected.</p>
        )}
      </div>
    </div>
  );
}
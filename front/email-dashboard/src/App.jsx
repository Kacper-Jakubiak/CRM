import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

// Helper component to display an email message with an expandable body, manual toggle, and reply functionality
function DisplayEmail({ msg, customerEmail, onMessageUpdate }) {
  const [replyBody, setReplyBody] = useState('');
  const [isReplying, setIsReplying] = useState(false);
  const [sending, setSending] = useState(false);
  const [togglingStatus, setTogglingStatus] = useState(false);
  const [needsResponse, setNeedsResponse] = useState(msg.needs_response);

  // Sync state if prop updates externally
  useEffect(() => {
    setNeedsResponse(msg.needs_response);
  }, [msg.needs_response]);

  const emailAddress = customerEmail || msg.customer_email || 'Unknown';

  const handleToggleNeedsResponse = async () => {
    const newStatus = !needsResponse;
    setTogglingStatus(true);

    try {
      const statusRes = await fetch(
        `${API_BASE_URL}/api/messages/${msg.provider_message_id}/status?needs_response=${newStatus}`,
        { method: 'PATCH' }
      );

      if (!statusRes.ok) {
        throw new Error('Failed to update message status');
      }

      const freshMsgRes = await fetch(`${API_BASE_URL}/api/messages/${msg.provider_message_id}`);
      if (freshMsgRes.ok) {
        const freshData = await freshMsgRes.json();
        const updatedMessage = freshData.message;

        setNeedsResponse(updatedMessage.needs_response);

        if (onMessageUpdate) {
          onMessageUpdate({ ...msg, ...updatedMessage });
        }
      }
    } catch (err) {
      console.error('Error toggling status:', err);
      alert('Failed to update status.');
    } finally {
      setTogglingStatus(false);
    }
  };

  const handleSendReply = async () => {
    if (!replyBody.trim()) return;
    setSending(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          recipient_email: emailAddress,
          subject: `Re: ${msg.subject || 'No Subject'}`,
          body: replyBody,
          reply_message_id: msg.provider_message_id,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send email');
      }

      // Update message status needs_response to false after successful send
      const statusRes = await fetch(
        `${API_BASE_URL}/api/messages/${msg.provider_message_id}/status?needs_response=false`,
        { method: 'PATCH' }
      );

      if (!statusRes.ok) {
        throw new Error('Failed to update message status');
      }

      // Fetch the fresh message state
      const freshMsgRes = await fetch(`${API_BASE_URL}/api/messages/${msg.provider_message_id}`);
      if (freshMsgRes.ok) {
        const freshData = await freshMsgRes.json();
        const updatedMessage = freshData.message;

        setNeedsResponse(updatedMessage.needs_response);

        if (onMessageUpdate) {
          onMessageUpdate({ ...msg, ...updatedMessage });
        }
      }

      alert('Reply sent successfully!');
      setReplyBody('');
      setIsReplying(false);
    } catch (err) {
      console.error('Error sending reply:', err);
      alert('Failed to send reply.');
    } finally {
      setSending(false);
    }
  };

  return (
    <li
      key={msg.provider_message_id}
      style={{
        marginBottom: '15px',
        borderBottom: '1px solid #ddd',
        paddingBottom: '10px',
        listStyle: 'none',
      }}
    >
      <strong>Subject:</strong> {msg.subject} <br />
      <strong>Email:</strong> {emailAddress} <br />
      <strong>Date:</strong> {msg.sent_at ? new Date(msg.sent_at).toLocaleString() : ''} <br />
      <strong>Needs Response:</strong>{' '}
      <span style={{ color: needsResponse ? 'red' : 'green', fontWeight: 'bold' }}>
        {needsResponse ? 'Yes' : 'No'}
      </span>
      <button
        onClick={handleToggleNeedsResponse}
        disabled={togglingStatus}
        style={{
          marginLeft: '10px',
          padding: '2px 8px',
          fontSize: '12px',
          cursor: 'pointer',
          borderRadius: '4px',
          border: '1px solid #ccc',
          background: '#f0f0f0',
        }}
      >
        {togglingStatus ? 'Updating...' : needsResponse ? 'Resolve' : 'Reopen'}
      </button>
      <br />
      <details style={{ marginTop: '8px', border: '1px solid #ccc', borderRadius: '4px', background: '#fff' }}>
        <summary style={{ padding: '8px 12px', cursor: 'pointer', background: '#f1f1f1', fontWeight: 'bold' }}>
          View Email Body
        </summary>
        <div
          dangerouslySetInnerHTML={{ __html: msg.body }}
          style={{ padding: '10px', maxHeight: '300px', overflowY: 'auto' }}
        />
      </details>
      <div style={{ marginTop: '8px' }}>
        {!isReplying ? (
          <button
            onClick={() => setIsReplying(true)}
            style={{
              padding: '4px 10px',
              background: '#007bff',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Answer
          </button>
        ) : (
          <div
            style={{
              marginTop: '8px',
              padding: '10px',
              background: '#f9f9f9',
              border: '1px solid #ddd',
              borderRadius: '4px',
            }}
          >
            <textarea
              rows="3"
              value={replyBody}
              onChange={(e) => setReplyBody(e.target.value)}
              placeholder="Type your reply here..."
              style={{ width: '100%', padding: '6px', marginBottom: '6px', boxSizing: 'border-box' }}
            />
            <div>
              <button
                onClick={handleSendReply}
                disabled={sending}
                style={{
                  padding: '4px 10px',
                  background: '#28a745',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  marginRight: '6px',
                }}
              >
                {sending ? 'Sending...' : 'Send Reply'}
              </button>
              <button
                onClick={() => setIsReplying(false)}
                style={{
                  padding: '4px 10px',
                  background: '#6c757d',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </li>
  );
}

// Component to handle thread rendering and merging logic per thread
function ThreadCard({ threadId, messages, onMessageUpdate, onThreadMoved }) {
  const [targetThreadId, setTargetThreadId] = useState('');
  const [moving, setMoving] = useState(false);

  const representativeMsg = messages[0];

  const handleMoveThread = async () => {
    if (!targetThreadId.trim()) {
      alert('Please enter a target Thread ID to merge into.');
      return;
    }

    if (parseInt(targetThreadId, 10) === threadId) {
      alert('Cannot move a thread into itself.');
      return;
    }

    setMoving(true);
    try {
      const providerMsgId = representativeMsg.provider_message_id;
      const res = await fetch(
        `${API_BASE_URL}/api/messages/${providerMsgId}/move?new_thread_id=${encodeURIComponent(
          targetThreadId
        )}`,
        { method: 'PATCH' }
      );

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to move thread');
      }

      const data = await res.json();
      alert(data.detail || 'Thread merged successfully!');
      setTargetThreadId('');

      if (onThreadMoved) {
        onThreadMoved();
      }
    } catch (err) {
      console.error('Error merging thread:', err);
      alert(`Error: ${err.message}`);
    } finally {
      setMoving(false);
    }
  };

  return (
    <div
      style={{
        border: '1px solid #bce8f1',
        borderRadius: '6px',
        backgroundColor: '#f4fbfd',
        marginBottom: '20px',
        padding: '15px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justify: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #d9edf7',
          paddingBottom: '10px',
          marginBottom: '10px',
        }}
      >
        <h4 style={{ margin: 0, color: '#31708f' }}>
          Thread #{threadId !== undefined && threadId !== null ? threadId : 'Unassigned'} ({messages.length}{' '}
          {messages.length === 1 ? 'message' : 'messages'})
        </h4>

        {/* Merge Thread Form */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <input
            type="number"
            placeholder="Target Thread ID"
            value={targetThreadId}
            onChange={(e) => setTargetThreadId(e.target.value)}
            style={{ width: '130px', padding: '4px 6px', fontSize: '12px', borderRadius: '4px', border: '1px solid #ccc' }}
          />
          <button
            onClick={handleMoveThread}
            disabled={moving}
            style={{
              padding: '4px 10px',
              fontSize: '12px',
              backgroundColor: '#17a2b8',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            {moving ? 'Merging...' : 'Merge Thread'}
          </button>
        </div>
      </div>

      <ul style={{ paddingLeft: 0, margin: 0 }}>
        {messages.map((msg) => (
          <DisplayEmail
            key={msg.provider_message_id}
            msg={msg}
            customerEmail={msg.customer_email}
            onMessageUpdate={onMessageUpdate}
          />
        ))}
      </ul>
    </div>
  );
}

// Helper component for rendering messages grouped by thread_id
function MessageThreadList({ messages, messageFilter, onMessageUpdate, onThreadMoved }) {
  const filteredMessages = messages.filter((msg) => {
    if (messageFilter === 'true') return msg.needs_response === true;
    if (messageFilter === 'false') return msg.needs_response === false;
    return true;
  });

  if (filteredMessages.length === 0) {
    return <p style={{ marginTop: '10px' }}>No messages found matching the filter.</p>;
  }

  // 1. Group messages by thread_id using Map to preserve data integrity
  const groupedMap = filteredMessages.reduce((acc, msg) => {
    const threadId = msg.thread_id ?? 'unassigned';
    if (!acc.has(threadId)) {
      acc.set(threadId, []);
    }
    acc.get(threadId).push(msg);
    return acc;
  }, new Map());

  // 2. Format threads into an array & sort messages inside each thread (Newest top -> Oldest bottom)
  const sortedThreads = Array.from(groupedMap.entries()).map(([tId, msgs]) => {
    // Sort messages inside thread: Newest first
    const sortedMsgs = [...msgs].sort((a, b) => new Date(b.sent_at) - new Date(a.sent_at));
    
    // Index 0 is the newest message after sorting
    const latestTimestamp = new Date(sortedMsgs[0].sent_at).getTime();

    return {
      threadId: tId,
      messages: sortedMsgs,
      latestTimestamp,
    };
  });

  // 3. Sort threads by most recent activity (Newest threads on top)
  sortedThreads.sort((a, b) => b.latestTimestamp - a.latestTimestamp);

  return (
    <div style={{ marginTop: '15px' }}>
      {sortedThreads.map(({ threadId, messages: threadMsgs }) => (
        <ThreadCard
          key={threadId}
          threadId={threadId === 'unassigned' ? 'Unassigned' : parseInt(threadId, 10)}
          messages={threadMsgs}
          onMessageUpdate={onMessageUpdate}
          onThreadMoved={onThreadMoved}
        />
      ))}
    </div>
  );
}

function App() {
  const [courses, setCourses] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [showAllCustomers, setShowAllCustomers] = useState(false);
  const [allCustomersData, setAllCustomersData] = useState({ messages: [], course_entries: [] });

  const [courseData, setCourseData] = useState({ entries: [], messages: [] });
  const [customerHistory, setCustomerHistory] = useState({ customer: null, messages: [], course_entries: [] });
  const [loading, setLoading] = useState(false);

  // Filter state for messages ('all', 'true', 'false')
  const [messageFilter, setMessageFilter] = useState('all');

  // Fetch initial courses and customers on mount
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/courses`)
      .then((res) => res.json())
      .then((data) => setCourses(data.courses || []))
      .catch((err) => console.error('Error fetching courses:', err));

    fetch(`${API_BASE_URL}/api/customers`)
      .then((res) => res.json())
      .then((data) => setCustomers(data.customers || []))
      .catch((err) => console.error('Error fetching customers:', err));
  }, []);

  // Handle Course Click
  const handleCourseClick = async (courseName) => {
    setSelectedCourse(courseName);
    setSelectedCustomer(null);
    setShowAllCustomers(false);
    setMessageFilter('all');
    setLoading(true);

    try {
      const [entriesRes, messagesRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/courses/${encodeURIComponent(courseName)}/entries`),
        fetch(`${API_BASE_URL}/api/courses/${encodeURIComponent(courseName)}/messages`),
      ]);

      const entriesData = await entriesRes.json();
      const messagesData = await messagesRes.json();

      setCourseData({
        entries: entriesData.course_entries || [],
        messages: messagesData.messages || [],
      });
    } catch (err) {
      console.error('Error fetching course details:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle Customer Click
  const handleCustomerClick = async (email) => {
    setSelectedCustomer(email);
    setSelectedCourse(null);
    setShowAllCustomers(false);
    setMessageFilter('all');
    setLoading(true);

    try {
      const [entriesRes, messagesRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/customers/${encodeURIComponent(email)}/entries`),
        fetch(`${API_BASE_URL}/api/customers/${encodeURIComponent(email)}/messages`),
      ]);

      const entriesData = await entriesRes.json();
      const messagesData = await messagesRes.json();

      setCustomerHistory({
        customer: messagesData.customer || entriesData.customer || { email },
        messages: messagesData.messages || [],
        course_entries: entriesData.course_entries || [],
      });
    } catch (err) {
      console.error('Error fetching customer history:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle "All" Customers Click
  const handleAllCustomersClick = async () => {
    setShowAllCustomers(true);
    setSelectedCustomer(null);
    setSelectedCourse(null);
    setMessageFilter('all');
    setLoading(true);

    try {
      const historyPromises = customers.map(async (c) => {
        try {
          const [entriesRes, messagesRes] = await Promise.all([
            fetch(`${API_BASE_URL}/api/customers/${encodeURIComponent(c.customer_email)}/entries`),
            fetch(`${API_BASE_URL}/api/customers/${encodeURIComponent(c.customer_email)}/messages`),
          ]);
          const entriesData = await entriesRes.json();
          const messagesData = await messagesRes.json();
          return {
            customer: messagesData.customer || entriesData.customer || c,
            messages: messagesData.messages || [],
            course_entries: entriesData.course_entries || [],
          };
        } catch {
          return { customer: c, messages: [], course_entries: [] };
        }
      });

      const results = await Promise.all(historyPromises);

      const allMsgsMap = new Map();
      const allEntriesMap = new Map();

      results.forEach((res) => {
        const customerEmail = res.customer?.email;
        (res.messages || []).forEach((m) => {
          allMsgsMap.set(m.provider_message_id, { ...m, customer_email: customerEmail || m.customer_email });
        });
        (res.course_entries || []).forEach((e) => {
          allEntriesMap.set(e.course_entry_id, { ...e, customer_email: customerEmail || e.customer_email });
        });
      });

      setAllCustomersData({
        messages: Array.from(allMsgsMap.values()),
        course_entries: Array.from(allEntriesMap.values()),
      });
    } catch (err) {
      console.error('Error fetching all customers history:', err);
    } finally {
      setLoading(false);
    }
  };

  // Refetch currently active view after merging threads
  const refreshActiveView = () => {
    if (selectedCourse) {
      handleCourseClick(selectedCourse);
    } else if (selectedCustomer) {
      handleCustomerClick(selectedCustomer);
    } else if (showAllCustomers) {
      handleAllCustomersClick();
    }
  };

  // Handle updating a single message in state dynamically across views
  const handleMessageUpdate = (updatedMsg) => {
    setCourseData((prev) => ({
      ...prev,
      messages: prev.messages.map((m) =>
        m.provider_message_id === updatedMsg.provider_message_id ? { ...m, ...updatedMsg } : m
      ),
    }));

    setCustomerHistory((prev) => ({
      ...prev,
      messages: prev.messages.map((m) =>
        m.provider_message_id === updatedMsg.provider_message_id ? { ...m, ...updatedMsg } : m
      ),
    }));

    setAllCustomersData((prev) => ({
      ...prev,
      messages: prev.messages.map((m) =>
        m.provider_message_id === updatedMsg.provider_message_id ? { ...m, ...updatedMsg } : m
      ),
    }));
  };

  return (
    <div className="app-container" style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>Email CRM Dashboard</h1>

      <div className="dashboard-grid" style={{ display: 'flex', gap: '40px' }}>
        {/* Left Column: Lists */}
        <div className="lists-column" style={{ flex: '1' }}>
          <section style={{ marginBottom: '30px' }}>
            <h2>Courses</h2>
            <ul style={{ listStyleType: 'none', padding: 0 }}>
              {courses.map((course) => (
                <li key={course.course_id} style={{ marginBottom: '8px' }}>
                  <button
                    onClick={() => handleCourseClick(course.course_name)}
                    style={{
                      padding: '8px 12px',
                      width: '100%',
                      textAlign: 'left',
                      backgroundColor: selectedCourse === course.course_name ? '#007bff' : '#f8f9fa',
                      color: selectedCourse === course.course_name ? '#fff' : '#000',
                      border: '1px solid #ccc',
                      borderRadius: '4px',
                      cursor: 'pointer',
                    }}
                  >
                    {course.course_name}
                  </button>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h2 style={{ margin: 0 }}>Customers</h2>
              <button
                onClick={handleAllCustomersClick}
                style={{
                  padding: '4px 10px',
                  backgroundColor: showAllCustomers ? '#17a2b8' : '#f8f9fa',
                  color: showAllCustomers ? '#fff' : '#000',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  fontSize: '14px',
                }}
              >
                All
              </button>
            </div>
            <ul style={{ listStyleType: 'none', padding: 0 }}>
              {customers.map((customer) => (
                <li key={customer.customer_id} style={{ marginBottom: '8px' }}>
                  <button
                    onClick={() => handleCustomerClick(customer.customer_email)}
                    style={{
                      padding: '8px 12px',
                      width: '100%',
                      textAlign: 'left',
                      backgroundColor: selectedCustomer === customer.customer_email ? '#28a745' : '#f8f9fa',
                      color: selectedCustomer === customer.customer_email ? '#fff' : '#000',
                      border: '1px solid #ccc',
                      borderRadius: '4px',
                      cursor: 'pointer',
                    }}
                  >
                    {customer.customer_email}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </div>

        {/* Right Column: Details View */}
        <div
          className="details-column"
          style={{ flex: '2', background: '#fdfdfd', padding: '20px', border: '1px solid #eee', borderRadius: '6px' }}
        >
          {loading && <p>Loading details...</p>}

          {!loading && !selectedCourse && !selectedCustomer && !showAllCustomers && (
            <p style={{ color: '#666' }}>Select a course, a customer, or "All" customers from the left to view details.</p>
          )}

          {/* Course Details View */}
          {!loading && selectedCourse && (
            <div>
              <h2>Course Details: {selectedCourse}</h2>

              <h3>Entries</h3>
              {courseData.entries.length === 0 ? (
                <p>No entries found for this course.</p>
              ) : (
                <ul>
                  {courseData.entries.map((entry) => (
                    <li key={entry.course_entry_id} style={{ marginBottom: '10px' }}>
                      <strong>Email:</strong> {entry.customer_email} <br />
                      <strong>Course Date:</strong> {new Date(entry.course_date).toLocaleDateString()}
                    </li>
                  ))}
                </ul>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px' }}>
                <h3 style={{ margin: 0 }}>Related Messages (By Thread)</h3>
                <div>
                  <label style={{ fontSize: '14px', marginRight: '6px' }}>Filter:</label>
                  <select
                    value={messageFilter}
                    onChange={(e) => setMessageFilter(e.target.value)}
                    style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #ccc' }}
                  >
                    <option value="all">All</option>
                    <option value="true">Needs Response: True</option>
                    <option value="false">Needs Response: False</option>
                  </select>
                </div>
              </div>

              <MessageThreadList
                messages={courseData.messages}
                messageFilter={messageFilter}
                onMessageUpdate={handleMessageUpdate}
                onThreadMoved={refreshActiveView}
              />
            </div>
          )}

          {/* Customer Details View */}
          {!loading && selectedCustomer && (
            <div>
              <h2>Customer History: {selectedCustomer}</h2>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px' }}>
                <h3 style={{ margin: 0 }}>Messages (By Thread)</h3>
                <div>
                  <label style={{ fontSize: '14px', marginRight: '6px' }}>Filter:</label>
                  <select
                    value={messageFilter}
                    onChange={(e) => setMessageFilter(e.target.value)}
                    style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #ccc' }}
                  >
                    <option value="all">All</option>
                    <option value="true">Needs Response: True</option>
                    <option value="false">Needs Response: False</option>
                  </select>
                </div>
              </div>

              <MessageThreadList
                messages={customerHistory.messages}
                messageFilter={messageFilter}
                onMessageUpdate={handleMessageUpdate}
                onThreadMoved={refreshActiveView}
              />

              <h3 style={{ marginTop: '20px' }}>Course Entries</h3>
              {customerHistory.course_entries.length === 0 ? (
                <p>No course entries found for this customer.</p>
              ) : (
                <ul>
                  {customerHistory.course_entries.map((entry) => (
                    <li key={entry.course_entry_id} style={{ marginBottom: '10px' }}>
                      <strong>Course:</strong> {entry.course_name} <br />
                      <strong>Date:</strong> {new Date(entry.course_date).toLocaleDateString()}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* All Customers View */}
          {!loading && showAllCustomers && (
            <div>
              <h2>All Customers History</h2>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px' }}>
                <h3 style={{ margin: 0 }}>All Messages (By Thread)</h3>
                <div>
                  <label style={{ fontSize: '14px', marginRight: '6px' }}>Filter:</label>
                  <select
                    value={messageFilter}
                    onChange={(e) => setMessageFilter(e.target.value)}
                    style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #ccc' }}
                  >
                    <option value="all">All</option>
                    <option value="true">Needs Response: True</option>
                    <option value="false">Needs Response: False</option>
                  </select>
                </div>
              </div>

              <MessageThreadList
                messages={allCustomersData.messages}
                messageFilter={messageFilter}
                onMessageUpdate={handleMessageUpdate}
                onThreadMoved={refreshActiveView}
              />

              <h3 style={{ marginTop: '20px' }}>All Course Entries</h3>
              {allCustomersData.course_entries.length === 0 ? (
                <p>No course entries found.</p>
              ) : (
                <ul>
                  {allCustomersData.course_entries.map((entry) => (
                    <li key={entry.course_entry_id} style={{ marginBottom: '10px' }}>
                      <strong>Email:</strong> {entry.customer_email} <br />
                      <strong>Course:</strong> {entry.course_name} <br />
                      <strong>Date:</strong> {new Date(entry.course_date).toLocaleDateString()}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
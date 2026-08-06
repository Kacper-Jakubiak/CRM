import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

// Compact Helper component to display an email message
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
        marginBottom: '8px',
        border: '1px solid #e2e8f0',
        borderRadius: '5px',
        padding: '8px 10px',
        listStyle: 'none',
        backgroundColor: '#fff',
        fontSize: '13px',
      }}
    >
      {/* Subject Line (Left-Aligned) & Timestamp (Right) */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', marginBottom: '6px' }}>
        <strong style={{ fontSize: '13px', color: '#1a202c', wordBreak: 'break-word', flex: 1, textAlign: 'left' }}>
          {msg.subject || '(No Subject)'}
        </strong>
        <span style={{ fontSize: '11px', color: '#718096', whiteSpace: 'nowrap' }}>
          {msg.sent_at ? new Date(msg.sent_at).toLocaleString() : ''}
        </span>
      </div>

      {/* From & Status Bar (Right-Aligned) */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: '#4a5568', textAlign: 'right' }}>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          <strong>From:</strong> {emailAddress}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0, justifyContent: 'flex-end' }}>
          <span>
            Status:{' '}
            <span style={{ color: needsResponse ? '#e53e3e' : '#38a169', fontWeight: 'bold' }}>
              {needsResponse ? 'Needs Response' : 'Resolved'}
            </span>
          </span>
          <button
            onClick={handleToggleNeedsResponse}
            disabled={togglingStatus}
            style={{
              padding: '2px 6px',
              fontSize: '11px',
              cursor: 'pointer',
              borderRadius: '3px',
              border: '1px solid #cbd5e0',
              background: '#edf2f7',
            }}
          >
            {togglingStatus ? '...' : needsResponse ? 'Resolve' : 'Reopen'}
          </button>
        </div>
      </div>

      {/* View Body Details & Reply Toggle */}
      <div style={{ display: 'flex', gap: '8px', marginTop: '6px', justifyContent: 'flex-end' }}>
        <details style={{ flex: 1, border: '1px solid #edf2f7', borderRadius: '4px', background: '#f7fafc', textAlign: 'right' }}>
          <summary style={{ padding: '3px 8px', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold', color: '#4a5568', textAlign: 'right' }}>
            View Body
          </summary>
          <div
            dangerouslySetInnerHTML={{ __html: msg.body }}
            style={{ padding: '8px', maxHeight: '200px', overflowY: 'auto', fontSize: '12px', backgroundColor: '#fff', textAlign: 'left' }}
          />
        </details>

        {!isReplying && (
          <button
            onClick={() => setIsReplying(true)}
            style={{
              padding: '3px 10px',
              background: '#3182ce',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '11px',
              height: 'fit-content',
              alignSelf: 'flex-start',
            }}
          >
            Reply
          </button>
        )}
      </div>

      {/* Reply Form */}
      {isReplying && (
        <div
          style={{
            marginTop: '8px',
            padding: '8px',
            background: '#f7fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '4px',
            textAlign: 'right',
          }}
        >
          <textarea
            rows="2"
            value={replyBody}
            onChange={(e) => setReplyBody(e.target.value)}
            placeholder="Type your reply here..."
            style={{ width: '100%', padding: '6px', marginBottom: '6px', boxSizing: 'border-box', fontSize: '12px', textAlign: 'left' }}
          />
          <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
            <button
              onClick={handleSendReply}
              disabled={sending}
              style={{
                padding: '3px 8px',
                background: '#38a169',
                color: '#fff',
                border: 'none',
                borderRadius: '3px',
                cursor: 'pointer',
                fontSize: '11px',
              }}
            >
              {sending ? 'Sending...' : 'Send'}
            </button>
            <button
              onClick={() => setIsReplying(false)}
              style={{
                padding: '3px 8px',
                background: '#e2e8f0',
                color: '#4a5568',
                border: '1px solid #cbd5e0',
                borderRadius: '3px',
                cursor: 'pointer',
                fontSize: '11px',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </li>
  );
}

// Component to handle thread rendering with default collapsed state, expanding, and merging
function ThreadCard({ threadId, messages, onMessageUpdate, onThreadMoved }) {
  const [targetThreadId, setTargetThreadId] = useState('');
  const [moving, setMoving] = useState(false);
  const [collapsed, setCollapsed] = useState(true);

  const representativeMsg = messages[0];
  const displayedMessages = collapsed ? messages.slice(0, 1) : messages;

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
        border: '1px solid #cbd5e0',
        borderRadius: '6px',
        backgroundColor: '#ebf8ff',
        marginBottom: '10px',
        padding: '8px 10px',
        textAlign: 'right',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: collapsed ? 'none' : '1px solid #bee3f8',
          paddingBottom: collapsed ? '0' : '6px',
          marginBottom: collapsed ? '6px' : '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setCollapsed(!collapsed)}
            style={{
              padding: '2px 6px',
              fontSize: '11px',
              backgroundColor: '#ffffff',
              color: '#2b6cb0',
              border: '1px solid #bee3f8',
              borderRadius: '3px',
              cursor: 'pointer',
              fontWeight: 'bold',
            }}
          >
            {collapsed ? '▶ Expand' : '▼ Collapse'}
          </button>
          <h4 style={{ margin: 0, color: '#2b6cb0', fontSize: '13px' }}>
            Thread #{threadId !== undefined && threadId !== null ? threadId : 'Unassigned'}{' '}
            <span style={{ fontSize: '11px', color: '#718096', fontWeight: 'normal' }}>
              ({messages.length} {messages.length === 1 ? 'msg' : 'msgs'})
            </span>
          </h4>
        </div>

        {/* Merge Thread Form */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <input
            type="number"
            placeholder="Target ID"
            value={targetThreadId}
            onChange={(e) => setTargetThreadId(e.target.value)}
            style={{ width: '80px', padding: '2px 4px', fontSize: '11px', borderRadius: '3px', border: '1px solid #cbd5e0', textAlign: 'right' }}
          />
          <button
            onClick={handleMoveThread}
            disabled={moving}
            style={{
              padding: '2px 6px',
              fontSize: '11px',
              backgroundColor: '#319795',
              color: '#fff',
              border: 'none',
              borderRadius: '3px',
              cursor: 'pointer',
            }}
          >
            {moving ? '...' : 'Merge'}
          </button>
        </div>
      </div>

      <ul style={{ paddingLeft: 0, margin: 0 }}>
        {displayedMessages.map((msg) => (
          <DisplayEmail
            key={msg.provider_message_id}
            msg={msg}
            customerEmail={msg.customer_email}
            onMessageUpdate={onMessageUpdate}
          />
        ))}
      </ul>
      {collapsed && messages.length > 1 && (
        <p style={{ margin: '2px 0 0 0', fontSize: '11px', color: '#718096', fontStyle: 'italic', textAlign: 'right' }}>
          + {messages.length - 1} older message(s) hidden.
        </p>
      )}
    </div>
  );
}

// Helper component for rendering messages grouped by thread_id inside a scrollable box
function MessageThreadList({ messages, messageFilter, onMessageUpdate, onThreadMoved }) {
  const filteredMessages = messages.filter((msg) => {
    if (messageFilter === 'true') return msg.needs_response === true;
    if (messageFilter === 'false') return msg.needs_response === false;
    return true;
  });

  if (filteredMessages.length === 0) {
    return <p style={{ marginTop: '10px', fontSize: '13px', color: '#718096', textAlign: 'right' }}>No messages found matching the filter.</p>;
  }

  const groupedMap = filteredMessages.reduce((acc, msg) => {
    const threadId = msg.thread_id ?? 'unassigned';
    if (!acc.has(threadId)) {
      acc.set(threadId, []);
    }
    acc.get(threadId).push(msg);
    return acc;
  }, new Map());

  const sortedThreads = Array.from(groupedMap.entries()).map(([tId, msgs]) => {
    const sortedMsgs = [...msgs].sort((a, b) => new Date(b.sent_at) - new Date(a.sent_at));
    const latestTimestamp = new Date(sortedMsgs[0].sent_at).getTime();

    return {
      threadId: tId,
      messages: sortedMsgs,
      latestTimestamp,
    };
  });

  sortedThreads.sort((a, b) => b.latestTimestamp - a.latestTimestamp);

  return (
    <div
      style={{
        marginTop: '10px',
        maxHeight: '450px',
        overflowY: 'auto',
        paddingRight: '6px',
        border: '1px solid #e2e8f0',
        borderRadius: '6px',
        padding: '8px',
        backgroundColor: '#f7fafc',
      }}
    >
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

  const [messageFilter, setMessageFilter] = useState('all');

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

  const refreshActiveView = () => {
    if (selectedCourse) {
      handleCourseClick(selectedCourse);
    } else if (selectedCustomer) {
      handleCustomerClick(selectedCustomer);
    } else if (showAllCustomers) {
      handleAllCustomersClick();
    }
  };

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
      <h1 style={{ fontSize: '24px', marginBottom: '20px', textAlign: 'right' }}>Email CRM Dashboard</h1>

      <div className="dashboard-grid" style={{ display: 'flex', gap: '30px' }}>
        {/* Left Column: Scrollable Lists */}
        <div className="lists-column" style={{ flex: '1', minWidth: '220px', maxWidth: '300px' }}>
          {/* Courses Section */}
          <section style={{ marginBottom: '20px' }}>
            <h2 style={{ fontSize: '18px', marginBottom: '8px', textAlign: 'right' }}>Courses</h2>
            <div
              style={{
                maxHeight: '220px',
                overflowY: 'auto',
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
                padding: '6px',
                backgroundColor: '#fafafa',
              }}
            >
              <ul style={{ listStyleType: 'none', padding: 0, margin: 0 }}>
                {courses.map((course) => (
                  <li key={course.course_id} style={{ marginBottom: '6px' }}>
                    <button
                      onClick={() => handleCourseClick(course.course_name)}
                      style={{
                        padding: '6px 10px',
                        width: '100%',
                        textAlign: 'right',
                        backgroundColor: selectedCourse === course.course_name ? '#3182ce' : '#fff',
                        color: selectedCourse === course.course_name ? '#fff' : '#2d3748',
                        border: '1px solid #cbd5e0',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '13px',
                      }}
                    >
                      {course.course_name}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          {/* Customers Section */}
          <section>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <button
                onClick={handleAllCustomersClick}
                style={{
                  padding: '3px 8px',
                  backgroundColor: showAllCustomers ? '#319795' : '#edf2f7',
                  color: showAllCustomers ? '#fff' : '#2d3748',
                  border: '1px solid #cbd5e0',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  fontSize: '12px',
                }}
              >
                All
              </button>
              <h2 style={{ margin: 0, fontSize: '18px', textAlign: 'right' }}>Customers</h2>
            </div>
            <div
              style={{
                maxHeight: '320px',
                overflowY: 'auto',
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
                padding: '6px',
                backgroundColor: '#fafafa',
              }}
            >
              <ul style={{ listStyleType: 'none', padding: 0, margin: 0 }}>
                {customers.map((customer) => (
                  <li key={customer.customer_id} style={{ marginBottom: '6px' }}>
                    <button
                      onClick={() => handleCustomerClick(customer.customer_email)}
                      style={{
                        padding: '6px 10px',
                        width: '100%',
                        textAlign: 'right',
                        backgroundColor: selectedCustomer === customer.customer_email ? '#38a169' : '#fff',
                        color: selectedCustomer === customer.customer_email ? '#fff' : '#2d3748',
                        border: '1px solid #cbd5e0',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {customer.customer_email}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        </div>

        {/* Right Column: Scrollable Details View */}
        <div
          className="details-column"
          style={{
            flex: '2',
            background: '#ffffff',
            padding: '16px',
            border: '1px solid #e2e8f0',
            borderRadius: '6px',
            maxHeight: '80vh',
            overflowY: 'auto',
            textAlign: 'right',
          }}
        >
          {loading && <p style={{ fontSize: '14px', color: '#718096', textAlign: 'right' }}>Loading details...</p>}

          {!loading && !selectedCourse && !selectedCustomer && !showAllCustomers && (
            <p style={{ color: '#718096', fontSize: '14px', textAlign: 'right' }}>
              Select a course, a customer, or "All" customers from the left to view details.
            </p>
          )}

          {/* Course Details View */}
          {!loading && selectedCourse && (
            <div>
              <h2 style={{ fontSize: '20px', marginBottom: '16px', textAlign: 'right' }}>Course Details: {selectedCourse}</h2>

              <h3 style={{ fontSize: '15px', marginBottom: '6px', textAlign: 'right' }}>Entries</h3>
              <div
                style={{
                  maxHeight: '160px',
                  overflowY: 'auto',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  padding: '8px',
                  backgroundColor: '#f7fafc',
                  fontSize: '13px',
                  textAlign: 'right',
                }}
              >
                {courseData.entries.length === 0 ? (
                  <p style={{ margin: 0, color: '#718096' }}>No entries found for this course.</p>
                ) : (
                  <ul style={{ margin: 0, paddingRight: '18px', listStylePosition: 'inside' }}>
                    {courseData.entries.map((entry) => (
                      <li key={entry.course_entry_id} style={{ marginBottom: '4px' }}>
                        <strong>Email:</strong> {entry.customer_email} | <strong>Course Date:</strong>{' '}
                        {new Date(entry.course_date).toLocaleDateString()}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px' }}>
                <div>
                  <label style={{ fontSize: '12px', marginRight: '6px' }}>Filter:</label>
                  <select
                    value={messageFilter}
                    onChange={(e) => setMessageFilter(e.target.value)}
                    style={{ padding: '3px 6px', borderRadius: '4px', border: '1px solid #cbd5e0', fontSize: '12px' }}
                  >
                    <option value="all">All</option>
                    <option value="true">Needs Response: True</option>
                    <option value="false">Needs Response: False</option>
                  </select>
                </div>
                <h3 style={{ margin: 0, fontSize: '15px', textAlign: 'right' }}>Related Messages (By Thread)</h3>
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
              <h2 style={{ fontSize: '20px', marginBottom: '16px', textAlign: 'right' }}>Customer History: {selectedCustomer}</h2>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <label style={{ fontSize: '12px', marginRight: '6px' }}>Filter:</label>
                  <select
                    value={messageFilter}
                    onChange={(e) => setMessageFilter(e.target.value)}
                    style={{ padding: '3px 6px', borderRadius: '4px', border: '1px solid #cbd5e0', fontSize: '12px' }}
                  >
                    <option value="all">All</option>
                    <option value="true">Needs Response: True</option>
                    <option value="false">Needs Response: False</option>
                  </select>
                </div>
                <h3 style={{ margin: 0, fontSize: '15px', textAlign: 'right' }}>Messages (By Thread)</h3>
              </div>

              <MessageThreadList
                messages={customerHistory.messages}
                messageFilter={messageFilter}
                onMessageUpdate={handleMessageUpdate}
                onThreadMoved={refreshActiveView}
              />

              <h3 style={{ marginTop: '16px', fontSize: '15px', marginBottom: '6px', textAlign: 'right' }}>Course Entries</h3>
              <div
                style={{
                  maxHeight: '160px',
                  overflowY: 'auto',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  padding: '8px',
                  backgroundColor: '#f7fafc',
                  fontSize: '13px',
                  textAlign: 'right',
                }}
              >
                {customerHistory.course_entries.length === 0 ? (
                  <p style={{ margin: 0, color: '#718096' }}>No course entries found for this customer.</p>
                ) : (
                  <ul style={{ margin: 0, paddingRight: '18px', listStylePosition: 'inside' }}>
                    {customerHistory.course_entries.map((entry) => (
                      <li key={entry.course_entry_id} style={{ marginBottom: '4px' }}>
                        <strong>Course:</strong> {entry.course_name} | <strong>Date:</strong>{' '}
                        {new Date(entry.course_date).toLocaleDateString()}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}

          {/* All Customers View */}
          {!loading && showAllCustomers && (
            <div>
              <h2 style={{ fontSize: '20px', marginBottom: '16px', textAlign: 'right' }}>All Customers History</h2>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <label style={{ fontSize: '12px', marginRight: '6px' }}>Filter:</label>
                  <select
                    value={messageFilter}
                    onChange={(e) => setMessageFilter(e.target.value)}
                    style={{ padding: '3px 6px', borderRadius: '4px', border: '1px solid #cbd5e0', fontSize: '12px' }}
                  >
                    <option value="all">All</option>
                    <option value="true">Needs Response: True</option>
                    <option value="false">Needs Response: False</option>
                  </select>
                </div>
                <h3 style={{ margin: 0, fontSize: '15px', textAlign: 'right' }}>All Messages (By Thread)</h3>
              </div>

              <MessageThreadList
                messages={allCustomersData.messages}
                messageFilter={messageFilter}
                onMessageUpdate={handleMessageUpdate}
                onThreadMoved={refreshActiveView}
              />

              <h3 style={{ marginTop: '16px', fontSize: '15px', marginBottom: '6px', textAlign: 'right' }}>All Course Entries</h3>
              <div
                style={{
                  maxHeight: '160px',
                  overflowY: 'auto',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  padding: '8px',
                  backgroundColor: '#f7fafc',
                  fontSize: '13px',
                  textAlign: 'right',
                }}
              >
                {allCustomersData.course_entries.length === 0 ? (
                  <p style={{ margin: 0, color: '#718096' }}>No course entries found.</p>
                ) : (
                  <ul style={{ margin: 0, paddingRight: '18px', listStylePosition: 'inside' }}>
                    {allCustomersData.course_entries.map((entry) => (
                      <li key={entry.course_entry_id} style={{ marginBottom: '4px' }}>
                        <strong>Email:</strong> {entry.customer_email} | <strong>Course:</strong> {entry.course_name}{' '}
                        | <strong>Date:</strong> {new Date(entry.course_date).toLocaleDateString()}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
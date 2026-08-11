import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

const normalizeEmailMessage = (message = {}) => ({
  ...message,
  provider_message_id: message.provider_message_id ?? message.id ?? message.providerId ?? '',
  customer_email: message.customer_email ?? message.email ?? message.customerEmail ?? message.sender ?? message.from_address ?? message.fromAddress ?? message.recipient_email ?? message.recipientEmail ?? '',
  subject: message.subject ?? '',
  body: message.body ?? '',
  needs_response: message.needs_response ?? message.needsResponse ?? false,
  thread_id: message.thread_id ?? message.threadId ?? null,
  sent_at: message.sent_at ?? message.sentAt ?? message.timestamp ?? null,
});

const normalizeEmailMessages = (payload) => {
  const rawMessages = Array.isArray(payload)
    ? payload
    : payload?.messages || payload?.email_messages || payload?.emailMessages || (payload?.message || payload?.email_message ? [payload.message || payload.email_message] : []);

  return rawMessages.map(normalizeEmailMessage);
};

const normalizeCollection = (payload, key) => {
  if (Array.isArray(payload)) {
    return payload;
  }

  if (payload && typeof payload === 'object') {
    const candidates = [payload[key], payload.data, payload.items, payload.results];
    for (const candidate of candidates) {
      if (Array.isArray(candidate)) {
        return candidate;
      }
    }
  }

  return [];
};

const normalizeCourseEntry = (entry = {}, fallbackCourseName = '', courseLookup = {}, customerLookup = {}) => ({
  ...entry,
  course_entry_id: entry.course_entry_id ?? entry.entry_id ?? entry.id ?? entry.courseEntryId ?? '',
  customer_email:
    entry.customer_email ??
    entry.customerEmail ??
    entry.email ??
    entry.customer?.email ??
    entry.customer?.customer_email ??
    customerLookup[entry.customer_id]?.customer_email ??
    customerLookup[entry.customer_id]?.email ??
    customerLookup[entry.customer?.id]?.customer_email ??
    customerLookup[entry.customer?.id]?.email ??
    '',
  course_name: entry.course_name ?? entry.courseName ?? entry.name ?? courseLookup[entry.course_id]?.course_name ?? courseLookup[entry.course_id]?.name ?? fallbackCourseName ?? '',
  course_date: entry.course_date ?? entry.courseDate ?? entry.date ?? entry.sent_at ?? entry.sentAt ?? null,
});

const normalizeCourseEntries = (payload, fallbackCourseName = '', courseLookup = {}, customerLookup = {}) => {
  const rawEntries = Array.isArray(payload)
    ? payload
    : payload?.course_entries || payload?.entries || payload?.courseEntries || [];

  return rawEntries.map((entry) => normalizeCourseEntry(entry, fallbackCourseName, courseLookup, customerLookup));
};

function DisplayEmail({ msg, customerEmail, onMessageUpdate, onThreadMoved }) {
  const [replyBody, setReplyBody] = useState('');
  const [isReplying, setIsReplying] = useState(false);
  const [sending, setSending] = useState(false);
  const [togglingStatus, setTogglingStatus] = useState(false);
  const [needsResponse, setNeedsResponse] = useState(msg.needs_response);

  const [targetThreadId, setTargetThreadId] = useState('');
  const [movingMsg, setMovingMsg] = useState(false);

  useEffect(() => {
    setNeedsResponse(msg.needs_response);
  }, [msg.needs_response]);

  const emailAddress = customerEmail || msg.customer_email || 'Unknown';

  const handleToggleNeedsResponse = async () => {
    const newStatus = !needsResponse;
    setTogglingStatus(true);

    try {
      const statusRes = await fetch(
        `${API_BASE_URL}/api/emails/${msg.provider_message_id}/status?needs_response=${newStatus}`,
        { method: 'PATCH' }
      );

      if (!statusRes.ok) {
        throw new Error('Failed to update message status');
      }

      const freshMsgRes = await fetch(`${API_BASE_URL}/api/emails/${msg.provider_message_id}`);
      if (freshMsgRes.ok) {
        const freshData = await freshMsgRes.json();
        const updatedMessage = normalizeEmailMessage(freshData.message ?? freshData.email_message ?? freshData);

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

      const statusRes = await fetch(
        `${API_BASE_URL}/api/emails/${msg.provider_message_id}/status?needs_response=false`,
        { method: 'PATCH' }
      );

      if (!statusRes.ok) {
        throw new Error('Failed to update message status');
      }

      const freshMsgRes = await fetch(`${API_BASE_URL}/api/emails/${msg.provider_message_id}`);
      if (freshMsgRes.ok) {
        const freshData = await freshMsgRes.json();
        const updatedMessage = normalizeEmailMessage(freshData.message ?? freshData.email_message ?? freshData);

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

  const handleMoveMessage = async () => {
    if (!targetThreadId.trim()) {
      alert('Please enter a target Thread ID.');
      return;
    }

    setMovingMsg(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/emails/${msg.provider_message_id}/move?new_thread_id=${encodeURIComponent(
          targetThreadId
        )}`,
        { method: 'PATCH' }
      );

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to move message');
      }

      alert('Message moved successfully!');
      setTargetThreadId('');

      if (onThreadMoved) {
        onThreadMoved();
      }
    } catch (err) {
      console.error('Error moving message:', err);
      alert(`Error: ${err.message}`);
    } finally {
      setMovingMsg(false);
    }
  };

  return (
    <li className="email-item">
      <div className="email-header">
        <strong className="email-subject">
          {msg.subject || '(No Subject)'}
        </strong>
        <span className="email-timestamp">
          {msg.sent_at ? new Date(msg.sent_at).toLocaleString() : ''}
        </span>
      </div>

      <div className="email-meta">
        <span className="email-sender">
          <strong>From:</strong> {emailAddress}
        </span>
        <div className="email-status-group">
          <span>
            Status:{' '}
            <span className={needsResponse ? 'status-needs-response' : 'status-resolved'}>
              {needsResponse ? 'Needs Response' : 'Resolved'}
            </span>
          </span>
          <button
            onClick={handleToggleNeedsResponse}
            disabled={togglingStatus}
            className="btn-toggle-status"
          >
            {togglingStatus ? '...' : needsResponse ? 'Resolve' : 'Reopen'}
          </button>
        </div>
      </div>

      <div className="email-body-group">
        <details className="email-details">
          <summary className="email-summary">
            View Body
          </summary>
          <div
            className="email-content"
            dangerouslySetInnerHTML={{ __html: msg.body }}
          />
        </details>
        
        <div className="email-actions-group">
          {!isReplying && (
            <button onClick={() => setIsReplying(true)} className="btn-reply">
              Reply
            </button>
          )}

          <div className="move-message-group">
            <input
              type="number"
              placeholder="New Thread ID"
              value={targetThreadId}
              onChange={(e) => setTargetThreadId(e.target.value)}
              className="input-target-id input-move-msg"
            />
            <button
              onClick={handleMoveMessage}
              disabled={movingMsg}
              className="btn-merge"
            >
              {movingMsg ? 'Moving...' : 'Move Msg'}
            </button>
          </div>
        </div>
      </div>

      {isReplying && (
        <div className="reply-form">
          <textarea
            rows="2"
            value={replyBody}
            onChange={(e) => setReplyBody(e.target.value)}
            placeholder="Type your reply here..."
            className="reply-textarea"
          />
          <div className="reply-actions">
            <button
              onClick={handleSendReply}
              disabled={sending}
              className="btn-send"
            >
              {sending ? 'Sending...' : 'Send'}
            </button>
            <button
              onClick={() => setIsReplying(false)}
              className="btn-cancel"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </li>
  );
}

function ThreadCard({ threadId, messages, onMessageUpdate, onThreadMoved }) {
  const [targetThreadId, setTargetThreadId] = useState('');
  const [merging, setMerging] = useState(false);
  const [collapsed, setCollapsed] = useState(true);

  const [threadMessages, setThreadMessages] = useState(messages);
  const [loadingThread, setLoadingThread] = useState(false);
  const [hasFetchedFullThread, setHasFetchedFullThread] = useState(false);

  useEffect(() => {
    if (!hasFetchedFullThread) {
      setThreadMessages(messages);
    }
  }, [messages, hasFetchedFullThread]);

  const fetchFullThreadMessages = async () => {
    if (threadId === 'Unassigned') return;

    setLoadingThread(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/emails/threads/${threadId}`);
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch thread emails');
      }

      const data = await res.json();
      const normalizedMsgs = normalizeEmailMessages(data);
      
      setThreadMessages(normalizedMsgs);
      setHasFetchedFullThread(true);
    } catch (err) {
      console.error(`Error fetching thread #${threadId}:`, err);
      alert(`Error loading thread #${threadId}: ${err.message}`);
    } finally {
      setLoadingThread(false);
    }
  };

  const handleToggleCollapse = () => {
    const willExpand = collapsed;
    setCollapsed(!collapsed);

    // Auto-fetch complete thread via /api/messages/threads/{thread_id} when expanding for the first time
    if (willExpand && threadId !== 'Unassigned' && !hasFetchedFullThread) {
      fetchFullThreadMessages();
    }
  };

  const handleMergeThreads = async () => {
    if (!targetThreadId.trim()) {
      alert('Please enter a target Thread ID to merge into.');
      return;
    }

    if (parseInt(targetThreadId, 10) === threadId) {
      alert('Cannot merge a thread into itself.');
      return;
    }

    setMerging(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/emails/threads/merge?old_thread_id=${threadId}&new_thread_id=${encodeURIComponent(
          targetThreadId
        )}`,
        { method: 'PATCH' }
      );

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to merge threads');
      }

      alert('Thread merged successfully!');
      setTargetThreadId('');

      if (onThreadMoved) {
        onThreadMoved();
      }
    } catch (err) {
      console.error('Error merging threads:', err);
      alert(`Error: ${err.message}`);
    } finally {
      setMerging(false);
    }
  };

  const handleLocalMessageUpdate = (updatedMsg) => {
    setThreadMessages((prev) =>
      prev.map((m) =>
        m.provider_message_id === updatedMsg.provider_message_id ? { ...m, ...updatedMsg } : m
      )
    );
    if (onMessageUpdate) {
      onMessageUpdate(updatedMsg);
    }
  };

  const displayedMessages = collapsed ? threadMessages.slice(0, 1) : threadMessages;

  return (
    <div className="thread-card">
      <div className={`thread-header ${collapsed ? 'collapsed' : 'expanded'}`}>
        <div className="thread-title-group">
          <button onClick={handleToggleCollapse} className="btn-collapse">
            {collapsed ? '▶ Expand' : '▼ Collapse'}
          </button>
          <h4 className="thread-title">
            Thread #{threadId !== 'Unassigned' ? threadId : 'Unassigned'}{' '}
            <span className="thread-count">
              ({threadMessages.length} {threadMessages.length === 1 ? 'msg' : 'msgs'})
            </span>
          </h4>

          {threadId !== 'Unassigned' && (
            <button
              onClick={fetchFullThreadMessages}
              disabled={loadingThread}
              className="btn-fetch-thread"
              title="Fetch all messages in this thread from /api/messages/threads/{thread_id}"
            >
              {loadingThread ? 'Loading...' : hasFetchedFullThread ? '✓ Synced' : '↻ Fetch Full Thread'}
            </button>
          )}
        </div>

        <div className="thread-merge-group">
          {threadId !== 'Unassigned' ? (
            <>
              <input
                type="number"
                placeholder="Merge to ID"
                value={targetThreadId}
                onChange={(e) => setTargetThreadId(e.target.value)}
                className="input-target-id"
              />
              <button
                onClick={handleMergeThreads}
                disabled={merging}
                className="btn-merge"
              >
                {merging ? 'Merging...' : 'Merge Thread'}
              </button>
            </>
          ) : (
            <span className="unassigned-notice">Cannot merge unassigned</span>
          )}
        </div>
      </div>

      <ul className="thread-messages-list">
        {displayedMessages.map((msg) => (
          <DisplayEmail
            key={msg.provider_message_id}
            msg={msg}
            customerEmail={msg.customer_email}
            onMessageUpdate={handleLocalMessageUpdate}
            onThreadMoved={onThreadMoved}
          />
        ))}
      </ul>
      {collapsed && threadMessages.length > 1 && (
        <p className="hidden-msg-text">
          + {threadMessages.length - 1} older message(s) hidden.
        </p>
      )}
    </div>
  );
}

function MessageThreadList({ messages, messageFilter, onMessageUpdate, onThreadMoved }) {
  const filteredMessages = messages.filter((msg) => {
    if (messageFilter === 'true') return msg.needs_response === true;
    if (messageFilter === 'false') return msg.needs_response === false;
    return true;
  });

  if (filteredMessages.length === 0) {
    return <p className="status-text-info mt-10">No messages found matching the filter.</p>;
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
    <div className="thread-list-container">
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
  const [isSyncing, setIsSyncing] = useState(false);

  const [messageFilter, setMessageFilter] = useState('all');

  const fetchCoursesAndCustomers = () => {
    fetch(`${API_BASE_URL}/api/courses`)
      .then((res) => res.json())
      .then((data) => setCourses(normalizeCollection(data, 'courses')))
      .catch((err) => console.error('Error fetching courses:', err));

    fetch(`${API_BASE_URL}/api/customers`)
      .then((res) => res.json())
      .then((data) => setCustomers(normalizeCollection(data, 'customers')))
      .catch((err) => console.error('Error fetching customers:', err));
  };

  useEffect(() => {
    fetchCoursesAndCustomers();
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
        fetch(`${API_BASE_URL}/api/courses/${encodeURIComponent(courseName)}/emails`),
      ]);

      const entriesData = await entriesRes.json();
      const messagesData = await messagesRes.json();
      const courseLookup = Object.fromEntries((courses || []).map((course) => [course.course_id, course]));
      const customerLookup = Object.fromEntries((customers || []).map((customer) => [customer.customer_id, customer]));

      setCourseData({
        entries: normalizeCourseEntries(entriesData, courseName, courseLookup, customerLookup),
        messages: normalizeEmailMessages(messagesData),
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
        fetch(`${API_BASE_URL}/api/customers/${encodeURIComponent(email)}/emails`),
      ]);

      const entriesData = await entriesRes.json();
      const messagesData = await messagesRes.json();
      const customerLookup = Object.fromEntries((customers || []).map((customer) => [customer.customer_id, customer]));

      setCustomerHistory({
        customer: messagesData.customer || entriesData.customer || { email },
        messages: normalizeEmailMessages(messagesData),
        course_entries: normalizeCourseEntries(entriesData, '', {}, customerLookup),
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
      const [emailsRes, entriesRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/emails`),
        fetch(`${API_BASE_URL}/api/courses/entries`),
      ]);

      if (!emailsRes.ok || !entriesRes.ok) {
        throw new Error('Failed to fetch all customers data');
      }

      const [messagesData, entriesData] = await Promise.all([
        emailsRes.json(),
        entriesRes.json(),
      ]);

      const allMessages = normalizeEmailMessages(messagesData);
      const customerLookup = Object.fromEntries((customers || []).map((customer) => [customer.customer_id, customer]));
      const allEntries = normalizeCourseEntries(entriesData, '', {}, customerLookup);

      setAllCustomersData({
        messages: allMessages,
        course_entries: allEntries,
      });
    } catch (err) {
      console.error('Error fetching all customers history:', err);
      setAllCustomersData({ messages: [], course_entries: [] });
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

  const handleSyncData = async () => {
    setIsSyncing(true);
    try {
      // Step 1: Import courses FIRST
      const coursesRes = await fetch(`${API_BASE_URL}/api/courses/import`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!coursesRes.ok) {
        const errorData = await coursesRes.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to import courses');
      }

      // Step 2: Pull emails ONLY AFTER course import completes
      const emailsRes = await fetch(`${API_BASE_URL}/api/integrations/emails/pull`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!emailsRes.ok) {
        const errorData = await emailsRes.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to pull emails');
      }

      // Step 3: Re-fetch sidebar list and active panel content
      fetchCoursesAndCustomers();
      refreshActiveView();
    } catch (err) {
      console.error('Error during sync:', err);
      alert(`Sync error: ${err.message}`);
    } finally {
      setIsSyncing(false);
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
    <div className="app-container">
      <header className="app-header">
        <h1 className="app-title">Email CRM Dashboard</h1>
        <button
          onClick={handleSyncData}
          disabled={isSyncing}
          className="btn-refresh"
        >
          {isSyncing ? '↻ Syncing Data...' : '↻ Sync Data'}
        </button>
      </header>

      <div className="dashboard-grid">
        <div className="lists-column">
          {/* Courses Section */}
          <section className="courses-section">
            <h2 className="section-title">Courses</h2>
            <div className="list-container courses-list-container">
              <ul className="list">
                {courses.map((course) => (
                  <li key={course.course_id} className="list-item">
                    <button
                      onClick={() => handleCourseClick(course.course_name)}
                      className={`btn-list-item ${selectedCourse === course.course_name ? 'active-course' : ''}`}
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
            <div className="all-customers-header">
              <h2 className="section-title no-margin">Customers</h2>
              <button
                onClick={handleAllCustomersClick}
                className={`btn-all-customers ${showAllCustomers ? 'active' : ''}`}
              >
                All
              </button>
            </div>
            <div className="list-container customers-list-container">
              <ul className="list">
                {customers.map((customer) => (
                  <li key={customer.customer_id} className="list-item">
                    <button
                      onClick={() => handleCustomerClick(customer.customer_email)}
                      className={`btn-list-item ${selectedCustomer === customer.customer_email ? 'active-customer' : ''}`}
                    >
                      {customer.customer_email}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        </div>

        <div className="details-column">
          {loading && <p className="status-text-info">Loading details...</p>}

          {!loading && !selectedCourse && !selectedCustomer && !showAllCustomers && (
            <p className="status-text-info">
              Select a course, a customer, or "All" customers from the left to view details.
            </p>
          )}

          {/* Course Details View */}
          {!loading && selectedCourse && (
            <div>
              <h2 className="details-title">Course Details: {selectedCourse}</h2>

              <h3 className="details-subtitle no-margin-top">Entries</h3>
              <div className="entries-container">
                {courseData.entries.length === 0 ? (
                  <p className="empty-text">No entries found for this course.</p>
                ) : (
                  <ul className="entries-list">
                    {courseData.entries.map((entry) => (
                      <li key={entry.course_entry_id} className="entry-item">
                        <strong>Email:</strong> {entry.customer_email || 'Unknown'} | <strong>Course Date:</strong>{' '}
                        {entry.course_date ? new Date(entry.course_date).toLocaleDateString() : '—'}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="filter-header mt-10">
                <div>
                  <label className="filter-label">Filter:</label>
                  <select
                    value={messageFilter}
                    onChange={(e) => setMessageFilter(e.target.value)}
                    className="filter-select"
                  >
                    <option value="all">All</option>
                    <option value="true">Needs Response: True</option>
                    <option value="false">Needs Response: False</option>
                  </select>
                </div>
                <h3 className="details-subtitle no-margin">Related Messages (By Thread)</h3>
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
              <h2 className="details-title">Customer History: {selectedCustomer}</h2>

              <div className="filter-header-no-margin">
                <div>
                  <label className="filter-label">Filter:</label>
                  <select
                    value={messageFilter}
                    onChange={(e) => setMessageFilter(e.target.value)}
                    className="filter-select"
                  >
                    <option value="all">All</option>
                    <option value="true">Needs Response: True</option>
                    <option value="false">Needs Response: False</option>
                  </select>
                </div>
                <h3 className="details-subtitle no-margin">Messages (By Thread)</h3>
              </div>

              <MessageThreadList
                messages={customerHistory.messages}
                messageFilter={messageFilter}
                onMessageUpdate={handleMessageUpdate}
                onThreadMoved={refreshActiveView}
              />

              <h3 className="details-subtitle">Course Entries</h3>
              <div className="entries-container">
                {customerHistory.course_entries.length === 0 ? (
                  <p className="empty-text">No course entries found for this customer.</p>
                ) : (
                  <ul className="entries-list">
                    {customerHistory.course_entries.map((entry) => (
                      <li key={entry.course_entry_id} className="entry-item">
                        <strong>Course:</strong> {entry.course_name} | <strong>Date:</strong>{' '}
                        {entry.course_date ? new Date(entry.course_date).toLocaleDateString() : '—'}
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
              <h2 className="details-title">All Customers History</h2>

              <div className="filter-header-no-margin">
                <div>
                  <label className="filter-label">Filter:</label>
                  <select
                    value={messageFilter}
                    onChange={(e) => setMessageFilter(e.target.value)}
                    className="filter-select"
                  >
                    <option value="all">All</option>
                    <option value="true">Needs Response: True</option>
                    <option value="false">Needs Response: False</option>
                  </select>
                </div>
                <h3 className="details-subtitle no-margin">All Messages (By Thread)</h3>
              </div>

              <MessageThreadList
                messages={allCustomersData.messages}
                messageFilter={messageFilter}
                onMessageUpdate={handleMessageUpdate}
                onThreadMoved={refreshActiveView}
              />

              <h3 className="details-subtitle">All Course Entries</h3>
              <div className="entries-container">
                {allCustomersData.course_entries.length === 0 ? (
                  <p className="empty-text">No course entries found.</p>
                ) : (
                  <ul className="entries-list">
                    {allCustomersData.course_entries.map((entry) => (
                      <li key={entry.course_entry_id} className="entry-item">
                        <strong>Email:</strong> {entry.customer_email || 'Unknown'} | <strong>Course:</strong> {entry.course_name}{' '}
                        | <strong>Date:</strong> {entry.course_date ? new Date(entry.course_date).toLocaleDateString() : '—'}
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
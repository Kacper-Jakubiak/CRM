import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

const sortEntriesNewestFirst = (entries) => {
  return [...entries].sort((a, b) => {
    const dateA = a.course_date ? new Date(a.course_date).getTime() : 0;
    const dateB = b.course_date ? new Date(b.course_date).getTime() : 0;
    return dateB - dateA;
  });
};

function DisplayEmail({ msg, customerEmail, onSelectMessage }) {
  const emailAddress = customerEmail || msg.sender || 'Unknown';

  return (
    <li className="email-item" onClick={() => onSelectMessage && onSelectMessage(msg)}>
      <div className="email-header">
        <strong className="email-subject">{msg.subject || '(No Subject)'}</strong>
        <span className="email-timestamp">{msg.sent_at ? new Date(msg.sent_at).toLocaleString() : ''}</span>
      </div>

      <div className="email-meta">
        <span className="email-sender"><strong>From:</strong> {emailAddress}</span>
        <span className={msg.needs_response ? 'status-needs-response' : 'status-resolved'}>
          {msg.needs_response ? 'Needs Response' : 'Resolved'}
        </span>
      </div>
    </li>
  );
}

function ThreadCard({ threadId, messages, onMessageUpdate, onThreadMoved, onSelectMessage, selectedEmail }) {
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
      const sortedData = [...data].sort((a, b) => new Date(b.sent_at) - new Date(a.sent_at));
      setThreadMessages(sortedData);
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
        `${API_BASE_URL}/api/emails/threads/merge?old_thread_id=${threadId}&new_thread_id=${encodeURIComponent(targetThreadId)}`,
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
          <button onClick={handleToggleCollapse} className="btn-collapse" type="button">
            {collapsed ? '▶ Expand' : '▼ Collapse'}
          </button>
          <h4 className="thread-title">
            Thread #{threadId !== 'Unassigned' ? threadId : 'Unassigned'}
            <span className="thread-count"> ({threadMessages.length} {threadMessages.length === 1 ? 'msg' : 'msgs'})</span>
          </h4>

          {threadId !== 'Unassigned' && (
            <button onClick={fetchFullThreadMessages} disabled={loadingThread} className="btn-fetch-thread" title="Fetch all messages in this thread" type="button">
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
              <button onClick={handleMergeThreads} disabled={merging} className="btn-merge" type="button">
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
            onSelectMessage={onSelectMessage}
          />
        ))}
      </ul>
      {collapsed && threadMessages.length > 1 && (
        <p className="hidden-msg-text">+ {threadMessages.length - 1} older message(s) hidden.</p>
      )}
    </div>
  );
}

function MessageThreadList({ messages, messageFilter, onMessageUpdate, onThreadMoved, onSelectMessage, selectedEmail }) {
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
          onSelectMessage={onSelectMessage}
          selectedEmail={selectedEmail}
        />
      ))}
    </div>
  );
}

function App() {
  const [view, setView] = useState('courses');
  const [theme, setTheme] = useState('dark');
  const [courses, setCourses] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [courseData, setCourseData] = useState({ entries: [], messages: [] });
  const [customerHistory, setCustomerHistory] = useState({ customer: null, messages: [], course_entries: [] });
  const [loading, setLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [messageFilter, setMessageFilter] = useState('all');
  const [middleView, setMiddleView] = useState('entries');
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [replyText, setReplyText] = useState('');
  const [moveThreadTarget, setMoveThreadTarget] = useState('');
  const [isReplying, setIsReplying] = useState(false);
  const [sendingReply, setSendingReply] = useState(false);
  const [movingEmail, setMovingEmail] = useState(false);
  const [togglingStatus, setTogglingStatus] = useState(false);

  useEffect(() => {
    setMiddleView('entries');
    setReplyText('');
    setMoveThreadTarget('');
    setIsReplying(false);
  }, [selectedCourse, selectedCustomer]);

  const fetchCoursesAndCustomers = () => {
    fetch(`${API_BASE_URL}/api/courses`)
      .then((res) => res.json())
      .then((data) => setCourses(Array.isArray(data) ? data : []))
      .catch((err) => console.error('Error fetching courses:', err));

    fetch(`${API_BASE_URL}/api/customers`)
      .then((res) => res.json())
      .then((data) => setCustomers(Array.isArray(data) ? data : []))
      .catch((err) => console.error('Error fetching customers:', err));
  };

  useEffect(() => {
    fetchCoursesAndCustomers();
  }, []);

  const handleCourseClick = async (courseName) => {
    setSelectedCourse(courseName);
    setSelectedCustomer(null);
    setSelectedEmail(null);
    setMessageFilter('all');
    setLoading(true);

    try {
      const [entriesRes, messagesRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/courses/${encodeURIComponent(courseName)}/entries`),
        fetch(`${API_BASE_URL}/api/courses/${encodeURIComponent(courseName)}/emails`),
      ]);

      const entriesData = await entriesRes.json();
      const messagesData = await messagesRes.json();

      setCourseData({
        entries: entriesData,
        messages: messagesData,
      });
    } catch (err) {
      console.error('Error fetching course details:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAllCourseEntries = async () => {
    setSelectedCourse('All');
    setSelectedCustomer(null);
    setSelectedEmail(null);
    setMessageFilter('all');
    setMiddleView('entries');
    setLoading(true);

    try {
      const [entriesRes, emailsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/courses/entries`),
        fetch(`${API_BASE_URL}/api/emails`),
      ]);

      const entriesData = entriesRes.ok ? await entriesRes.json() : [];
      const messagesData = emailsRes.ok ? await emailsRes.json() : [];

      setCourseData({
        entries: entriesData,
        messages: messagesData,
      });
    } catch (err) {
      console.error('Error fetching all course entries:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCustomerClick = async (email) => {
    setSelectedCustomer(email);
    setSelectedCourse(null);
    setSelectedEmail(null);
    setMessageFilter('all');
    setLoading(true);

    try {
      const [entriesRes, messagesRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/customers/${encodeURIComponent(email)}/entries`),
        fetch(`${API_BASE_URL}/api/customers/${encodeURIComponent(email)}/emails`),
      ]);

      const entriesData = await entriesRes.json();
      const messagesData = await messagesRes.json();

      setCustomerHistory({
        customer: messagesData.customer || entriesData.customer || { email },
        messages: messagesData,
        course_entries: entriesData,
      });
    } catch (err) {
      console.error('Error fetching customer history:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAllCustomerEmails = async () => {
    setSelectedCustomer('All');
    setSelectedCourse(null);
    setSelectedEmail(null);
    setMessageFilter('all');
    setMiddleView('emails');
    setLoading(true);

    try {
      const [entriesRes, emailsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/courses/entries`),
        fetch(`${API_BASE_URL}/api/emails`),
      ]);

      const entriesData = entriesRes.ok ? await entriesRes.json() : [];
      const messagesData = emailsRes.ok ? await emailsRes.json() : [];

      setCustomerHistory({
        customer: { email: 'All' },
        messages: messagesData,
        course_entries: entriesData,
      });
    } catch (err) {
      console.error('Error fetching all customer emails:', err);
    } finally {
      setLoading(false);
    }
  };

  const refreshActiveView = () => {
    if (selectedCourse === 'All') {
      handleAllCourseEntries();
    } else if (selectedCourse) {
      handleCourseClick(selectedCourse);
    } else if (selectedCustomer === 'All') {
      handleAllCustomerEmails();
    } else if (selectedCustomer) {
      handleCustomerClick(selectedCustomer);
    }
  };

  const handleSyncData = async () => {
    setIsSyncing(true);
    try {
      const coursesRes = await fetch(`${API_BASE_URL}/api/courses/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!coursesRes.ok) {
        const errorData = await coursesRes.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to import courses');
      }

      const emailsRes = await fetch(`${API_BASE_URL}/api/integrations/emails/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!emailsRes.ok) {
        const errorData = await emailsRes.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to pull emails');
      }

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

    setSelectedEmail((prev) => (prev && prev.provider_message_id === updatedMsg.provider_message_id ? { ...prev, ...updatedMsg } : prev));
  };

  const handleToggleNeedsResponse = async () => {
    if (!selectedEmail) return;

    const newStatus = !selectedEmail.needs_response;
    setTogglingStatus(true);

    try {
      const statusRes = await fetch(
        `${API_BASE_URL}/api/emails/${selectedEmail.provider_message_id}/status?needs_response=${newStatus}`,
        { method: 'PATCH' }
      );

      if (!statusRes.ok) {
        throw new Error('Failed to update message status');
      }

      const updatedMessage = {
        ...selectedEmail,
        needs_response: newStatus,
      };

      handleMessageUpdate(updatedMessage);
    } catch (err) {
      console.error('Error toggling status:', err);
      alert('Failed to update status.');
    } finally {
      setTogglingStatus(false);
    }
  };

  const handleSendReply = async () => {
    if (!selectedEmail || !replyText.trim()) return;
    setSendingReply(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipient_email: selectedEmail.customer_email || selectedEmail.sender || selectedCustomer,
          subject: `Re: ${selectedEmail.subject || 'No Subject'}`,
          body: replyText,
          reply_message_id: selectedEmail.provider_message_id,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send email');
      }

      const statusRes = await fetch(
        `${API_BASE_URL}/api/emails/${selectedEmail.provider_message_id}/status?needs_response=false`,
        { method: 'PATCH' }
      );

      if (!statusRes.ok) {
        throw new Error('Failed to update message status');
      }

      handleMessageUpdate({ ...selectedEmail, needs_response: false });
      setReplyText('');
      setIsReplying(false);
      alert('Reply sent successfully!');
    } catch (err) {
      console.error('Error sending reply:', err);
      alert('Failed to send reply.');
    } finally {
      setSendingReply(false);
    }
  };

  const handleMoveMessage = async () => {
    if (!selectedEmail) return;
    if (!moveThreadTarget.trim()) {
      alert('Please enter a target Thread ID.');
      return;
    }

    setMovingEmail(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/emails/${selectedEmail.provider_message_id}/move?new_thread_id=${encodeURIComponent(moveThreadTarget)}`,
        { method: 'PATCH' }
      );

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to move message');
      }

      setMoveThreadTarget('');
      refreshActiveView();
      alert('Message moved successfully!');
    } catch (err) {
      console.error('Error moving message:', err);
      alert(`Error: ${err.message}`);
    } finally {
      setMovingEmail(false);
    }
  };

  const listItems = view === 'courses' ? courses : customers;

  return (
    <div className={`app-shell theme-${theme}`}>
      <header className="topbar">
        <div>
          <p className="eyebrow">CRM workspace</p>
          <h1>Email Insights</h1>
        </div>

        <div className="topbar-actions">
          <button className="theme-toggle" onClick={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))} type="button">
            {theme === 'dark' ? 'Light mode' : 'Dark mode'}
          </button>
          <button className="sync-button" onClick={handleSyncData} disabled={isSyncing} type="button">
            {isSyncing ? 'Syncing…' : 'Sync data'}
          </button>
        </div>
      </header>

      <div className="dashboard-shell">
        <aside className="sidebar panel">
          <div className="segment-toggle" aria-label="Toggle data source">
            <button className={view === 'courses' ? 'segment active' : 'segment'} onClick={() => setView('courses')} type="button">Courses</button>
            <button className={view === 'customers' ? 'segment active' : 'segment'} onClick={() => setView('customers')} type="button">Customers</button>
          </div>

          <div className="panel-header">
            <h2>{view === 'courses' ? 'Courses' : 'Customers'}</h2>
          </div>

          <div className="list-panel">
            <button
              type="button"
              className={
                (view === 'courses' && selectedCourse === 'All') || (view === 'customers' && selectedCustomer === 'All')
                  ? 'list-item all-button active'
                  : 'list-item all-button'
              }
              onClick={() => {
                if (view === 'courses') {
                  handleAllCourseEntries();
                } else {
                  handleAllCustomerEmails();
                }
              }}
            >
              All
            </button>

            {listItems.length === 0 ? (
              <div className="empty-state small">No records available.</div>
            ) : (
              listItems.map((item) => {
                const label = view === 'courses' ? item.course_name : item.customer_email;
                const isSelected = view === 'courses' ? selectedCourse === item.course_name : selectedCustomer === item.customer_email;

                return (
                  <button
                    key={view === 'courses' ? item.course_id : item.customer_id}
                    className={isSelected ? 'list-item active' : 'list-item'}
                    onClick={() => {
                      if (view === 'courses') {
                        handleCourseClick(item.course_name);
                      } else {
                        handleCustomerClick(item.customer_email);
                      }
                    }}
                    type="button"
                  >
                    {label}
                  </button>
                );
              })
            )}
          </div>
        </aside>

        <main className="content-panel panel">
          {loading && <p className="status-text-info">Loading details...</p>}

          {!loading && selectedCourse && (
            <div className="content-inner">
              <div className="panel-header">
                <h2>Course details: {selectedCourse}</h2>
              </div>

              <div className="detail-toggle-row">
                <button
                  type="button"
                  className={middleView === 'entries' ? 'detail-toggle active' : 'detail-toggle'}
                  onClick={() => setMiddleView('entries')}
                >
                  Entries
                </button>
                <button
                  type="button"
                  className={middleView === 'emails' ? 'detail-toggle active' : 'detail-toggle'}
                  onClick={() => setMiddleView('emails')}
                >
                  Emails
                </button>
              </div>

              {middleView === 'entries' ? (
                <div className="entries-block">
                  <div className="entries-header">
                    <h3>Entries</h3>
                  </div>
                  {courseData.entries.length === 0 ? (
                    <p className="empty-text">No entries found for this course.</p>
                  ) : (
                    <ul className="entries-list">
                      {sortEntriesNewestFirst(courseData.entries).map((entry) => (
                        <li key={entry.course_entry_id} className="entry-item">
                          <strong>Email:</strong> {entry.customer_email || 'Unknown'} | <strong>Course Date:</strong>{' '}
                          {entry.course_date ? new Date(entry.course_date).toLocaleDateString() : '—'}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ) : (
                <>
                  <div className="filter-header">
                    <div>
                      <label className="filter-label">Filter:</label>
                      <select value={messageFilter} onChange={(e) => setMessageFilter(e.target.value)} className="filter-select">
                        <option value="all">All</option>
                        <option value="true">Needs Response: True</option>
                        <option value="false">Needs Response: False</option>
                      </select>
                    </div>
                    <h3 className="details-subtitle no-margin">Related Messages</h3>
                  </div>

                  <MessageThreadList
                    messages={courseData.messages}
                    messageFilter={messageFilter}
                    onMessageUpdate={handleMessageUpdate}
                    onThreadMoved={refreshActiveView}
                    onSelectMessage={setSelectedEmail}
                    selectedEmail={selectedEmail}
                  />
                </>
              )}
            </div>
          )}

          {!loading && selectedCustomer && (
            <div className="content-inner">
              <div className="panel-header">
                <h2>Customer history: {selectedCustomer}</h2>
              </div>

              <div className="detail-toggle-row">
                <button
                  type="button"
                  className={middleView === 'entries' ? 'detail-toggle active' : 'detail-toggle'}
                  onClick={() => setMiddleView('entries')}
                >
                  Entries
                </button>
                <button
                  type="button"
                  className={middleView === 'emails' ? 'detail-toggle active' : 'detail-toggle'}
                  onClick={() => setMiddleView('emails')}
                >
                  Emails
                </button>
              </div>

              {middleView === 'emails' ? (
                <>
                  <div className="filter-header compact-header">
                    <div>
                      <label className="filter-label">Filter:</label>
                      <select value={messageFilter} onChange={(e) => setMessageFilter(e.target.value)} className="filter-select">
                        <option value="all">All</option>
                        <option value="true">Needs Response: True</option>
                        <option value="false">Needs Response: False</option>
                      </select>
                    </div>
                    <h3 className="details-subtitle no-margin">Messages</h3>
                  </div>

                  <MessageThreadList
                    messages={customerHistory.messages}
                    messageFilter={messageFilter}
                    onMessageUpdate={handleMessageUpdate}
                    onThreadMoved={refreshActiveView}
                    onSelectMessage={setSelectedEmail}
                    selectedEmail={selectedEmail}
                  />
                </>
              ) : (
                <div className="entries-block">
                  <div className="entries-header">
                    <h3>Course Entries</h3>
                  </div>
                  {customerHistory.course_entries.length === 0 ? (
                    <p className="empty-text">No course entries found for this customer.</p>
                  ) : (
                    <ul className="entries-list">
                      {sortEntriesNewestFirst(customerHistory.course_entries).map((entry) => (
                        <li key={entry.course_entry_id} className="entry-item">
                          <strong>Course:</strong> {entry.course_name} | <strong>Date:</strong>{' '}
                          {entry.course_date ? new Date(entry.course_date).toLocaleDateString() : '—'}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          )}

          {!loading && !selectedCourse && !selectedCustomer && (
            <div className="empty-state detail-placeholder">Select a course or customer from the left panel.</div>
          )}
        </main>

        <aside className="detail-panel panel">
          <div className="panel-header">
            <h2>Selected email</h2>
          </div>

          {!selectedEmail ? (
            <div className="empty-state detail-placeholder">Choose a message from the thread list to view it here.</div>
          ) : (
            <div className="email-detail">
              <div className="email-detail__meta">
                <span className="badge">{selectedEmail.needs_response ? 'Needs response' : 'Resolved'}</span>
                <span className="email-detail__timestamp">{selectedEmail.sent_at ? new Date(selectedEmail.sent_at).toLocaleString() : ''}</span>
              </div>

              <div className="selected-email-actions">
                <button
                  type="button"
                  className="btn-reply"
                  onClick={() => setIsReplying((current) => !current)}
                >
                  {isReplying ? 'Hide reply' : 'Reply'}
                </button>
                <button
                  type="button"
                  className="btn-toggle-status"
                  onClick={handleToggleNeedsResponse}
                  disabled={togglingStatus}
                >
                  {togglingStatus ? '...' : selectedEmail.needs_response ? 'Resolve' : 'Reopen'}
                </button>
              </div>

              <div className="move-message-row">
                <input
                  type="number"
                  placeholder="Move to thread ID"
                  value={moveThreadTarget}
                  onChange={(e) => setMoveThreadTarget(e.target.value)}
                  className="input-target-id"
                />
                <button type="button" className="btn-merge" onClick={handleMoveMessage} disabled={movingEmail}>
                  {movingEmail ? 'Moving...' : 'Move to thread'}
                </button>
              </div>

              {isReplying && (
                <div className="reply-form compact">
                  <textarea
                    rows="4"
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    placeholder="Type your reply here..."
                    className="reply-textarea"
                  />
                  <div className="reply-actions">
                    <button type="button" className="btn-send" onClick={handleSendReply} disabled={sendingReply}>
                      {sendingReply ? 'Sending...' : 'Send'}
                    </button>
                    <button type="button" className="btn-cancel" onClick={() => setIsReplying(false)}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              <div className="email-body" dangerouslySetInnerHTML={{ __html: selectedEmail.body || '<p>No email body available.</p>' }} />
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

export default App;

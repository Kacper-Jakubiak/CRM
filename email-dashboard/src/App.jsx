import React, { useState, useEffect } from 'react';
import DOMPurify from 'dompurify';
import './App.css';

const fetchWithAuth = async (url, options = {}) => {
  const secretKey = localStorage.getItem('adminSecret') || '';

  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${secretKey}`,
  };

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    localStorage.removeItem('adminSecret');
    window.dispatchEvent(new Event('auth-unauthorized'));
  }

  return response;
};

const sortEntriesNewestFirst = (entries) => {
  return [...entries].sort((a, b) => {
    const dateA = a.course_date ? new Date(a.course_date).getTime() : 0;
    const dateB = b.course_date ? new Date(b.course_date).getTime() : 0;
    return dateB - dateA;
  });
};

const groupEntriesByDate = (entries) => {
  const grouped = entries.reduce((acc, entry) => {
    const dateKey = entry.course_date ? new Date(entry.course_date).toISOString().slice(0, 10) : 'No date';
    if (!acc[dateKey]) {
      acc[dateKey] = [];
    }
    acc[dateKey].push(entry);
    return acc;
  }, {});

  return Object.entries(grouped)
    .map(([dateKey, items]) => ({
      dateKey,
      dateLabel: dateKey === 'No date' ? 'No date' : new Date(dateKey).toLocaleDateString(),
      items: sortEntriesNewestFirst(items),
    }))
    .sort((a, b) => {
      if (a.dateKey === 'No date') return 1;
      if (b.dateKey === 'No date') return -1;
      return b.dateKey.localeCompare(a.dateKey);
    });
};

function DisplayEmail({ msg, customerEmail, onSelectMessage, isSelected, onMessageUpdate }) {
  const emailAddress = customerEmail;
  const displayClass = msg.seen === false ? 'is-unseen' : 'is-seen';

  const handleClick = async () => {
    let currentMsg = msg;

    if (msg.seen === false) {
      try {
        const res = await fetchWithAuth(`/api/emails/seen?provider_message_id=${encodeURIComponent(msg.provider_message_id)}&seen_status=true`, {
          method: 'PATCH',
        });
        
        if (res.ok) {
          const updatedMsg = await res.json();
          currentMsg = updatedMsg;
          if (onMessageUpdate) {
            onMessageUpdate(updatedMsg);
          }
        }
      } catch (err) {
        console.error('Failed to mark email as seen:', err);
      }
    }

    if (onSelectMessage) {
      onSelectMessage(currentMsg);
    }
  };

  return (
    <li
      className={`email-item ${isSelected ? 'selected' : ''}`}
      onClick={handleClick}
    >
      <div className="email-header">
        <span className={`email-subject ${displayClass}`}>{msg.subject || '(No Subject)'}</span>
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
    setThreadMessages((prevThreadMsgs) => {
      if (!hasFetchedFullThread) return messages;
      return prevThreadMsgs.map((m) => {
        const updated = messages.find((p) => p.provider_message_id === m.provider_message_id);
        return updated ? { ...m, ...updated } : m;
      });
    });
  }, [messages, hasFetchedFullThread]);

  const fetchFullThreadMessages = async () => {
    if (threadId === 'Unassigned') return;

    setLoadingThread(true);
    try {
      const res = await fetchWithAuth(`/api/emails/thread-messages?thread_id=${threadId}`);
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
      const res = await fetchWithAuth(
        `/api/emails/threads/merge?old_thread_id=${threadId}&new_thread_id=${encodeURIComponent(targetThreadId)}`,
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
  const hasUnseen = threadMessages.some(m => m.seen === false);
  const threadClass = hasUnseen ? 'is-unseen' : 'is-seen';

  return (
    <div className="thread-card">
      <div 
        className={`thread-header ${collapsed ? 'collapsed' : 'expanded'}`}
        onClick={handleToggleCollapse}
      >
        <h4 className={`thread-title ${threadClass}`}>
          {collapsed ? '▶ ' : '▼ '}Thread #{threadId !== 'Unassigned' ? threadId : 'Unassigned'}
          <span className="thread-count"> ({threadMessages.length} {threadMessages.length === 1 ? 'msg' : 'msgs'})</span>
        </h4>

        <div className="thread-actions-group" onClick={(e) => e.stopPropagation()}>
          {threadId !== 'Unassigned' && (
            <button onClick={fetchFullThreadMessages} disabled={loadingThread} className="btn-fetch-thread" title="Fetch all messages in this thread" type="button">
              {loadingThread ? 'Loading...' : hasFetchedFullThread ? '✓ Synced' : '↻ Fetch'}
            </button>
          )}

          {threadId !== 'Unassigned' ? (
            <>
              <input
                type="number"
                placeholder="Merge ID"
                value={targetThreadId}
                onChange={(e) => setTargetThreadId(e.target.value)}
                className="input-target-id"
              />
              <button onClick={handleMergeThreads} disabled={merging} className="btn-merge" type="button">
                {merging ? 'Merging...' : 'Merge'}
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
            isSelected={selectedEmail?.provider_message_id === msg.provider_message_id}
          />
        ))}
      </ul>
    </div>
  );
}

function MessageThreadList({ messages, messageFilter, onMessageUpdate, onThreadMoved, onSelectMessage, selectedEmail }) {
  const filteredMessages = messages.filter((msg) => {
    if (messageFilter === 'no' || messageFilter === 'true') return msg.needs_response === true;
    if (messageFilter === 'yes' || messageFilter === 'false') return msg.needs_response === false;
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
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!localStorage.getItem('adminSecret'));
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const [view, setView] = useState('customers');
  const [theme, setTheme] = useState('dark');
  const [courses, setCourses] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [globalEntries, setGlobalEntries] = useState([]);
  const [globalMessages, setGlobalMessages] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState('All');
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [courseData, setCourseData] = useState({ entries: [], messages: [] });
  const [customerHistory, setCustomerHistory] = useState({ customer: null, messages: [], course_entries: [] });
  const [loading, setLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [messageFilter, setMessageFilter] = useState('all');
  const [middleView, setMiddleView] = useState('emails');
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [replyText, setReplyText] = useState('');
  const [isHtmlReply, setIsHtmlReply] = useState(false);
  const [moveThreadTarget, setMoveThreadTarget] = useState('');
  const [isReplying, setIsReplying] = useState(false);
  const [sendingReply, setSendingReply] = useState(false);
  const [movingEmail, setMovingEmail] = useState(false);
  const [togglingStatus, setTogglingStatus] = useState(false);
  const [customerNote, setCustomerNote] = useState('');
  const [savingCustomerNote, setSavingCustomerNote] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [collapsedCompanies, setCollapsedCompanies] = useState({});

  useEffect(() => {
    const handleAuthError = () => setIsAuthenticated(false);
    window.addEventListener('auth-unauthorized', handleAuthError);
    return () => window.removeEventListener('auth-unauthorized', handleAuthError);
  }, []);

  useEffect(() => {
    setReplyText('');
    setMoveThreadTarget('');
    setIsReplying(false);
  }, [selectedCourse, selectedCustomer]);

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Invalid username or password');
      }

      const data = await res.json();
      localStorage.setItem('adminSecret', data.access_token);
      setIsAuthenticated(true);
      setUsername('');
      setPassword('');
    } catch (err) {
      alert(err.message);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('adminSecret');
    setIsAuthenticated(false);
  };

  const toggleCompanyCollapse = (companyName) => {
    setCollapsedCompanies((prev) => ({
      ...prev,
      [companyName]: !prev[companyName],
    }));
  };

  const fetchCoursesAndCustomers = () => {
    fetchWithAuth(`/api/courses`)
      .then((res) => res.json())
      .then((data) => setCourses(Array.isArray(data) ? data : []))
      .catch((err) => console.error('Error fetching courses:', err));

    fetchWithAuth(`/api/customers`)
      .then((res) => res.json())
      .then((data) => setCustomers(Array.isArray(data) ? data : []))
      .catch((err) => console.error('Error fetching customers:', err));
  };

  const fetchGlobalData = async () => {
    try {
      const [entriesRes, emailsRes] = await Promise.all([
        fetchWithAuth(`/api/courses/entries`),
        fetchWithAuth(`/api/emails`),
      ]);
      const entriesData = entriesRes.ok ? await entriesRes.json() : [];
      const messagesData = emailsRes.ok ? await emailsRes.json() : [];
      setGlobalEntries(entriesData);
      setGlobalMessages(messagesData);
      return { entriesData, messagesData };
    } catch (err) {
      console.error('Error fetching global data:', err);
      return { entriesData: [], messagesData: [] };
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchCoursesAndCustomers();
      handleAllCourseEntries();
    }
  }, [isAuthenticated]);

  const handleCourseClick = async (courseName) => {
    setSelectedCourse(courseName);
    setSelectedCustomer(null);
    setSelectedEmail(null);
    setMessageFilter('all');
    setLoading(true);

    try {
      const [entriesRes, messagesRes] = await Promise.all([
        fetchWithAuth(`/api/courses/course-entries?course_name=${encodeURIComponent(courseName)}`),
        fetchWithAuth(`/api/courses/emails?course_name=${encodeURIComponent(courseName)}`),
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
    setLoading(true);

    try {
      const { entriesData, messagesData } = await fetchGlobalData();
      
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
        fetchWithAuth(`/api/customers/entries?email_address=${encodeURIComponent(email)}`),
        fetchWithAuth(`/api/customers/emails?email_address=${encodeURIComponent(email)}`),
      ]);

      const entriesData = await entriesRes.json();
      const messagesData = await messagesRes.json();

      const foundCustomer = customers.find((c) => (c.email) === email);
      const customerObj = foundCustomer || messagesData.customer || entriesData.customer || { email };

      setCustomerHistory({
        customer: customerObj,
        messages: messagesData,
        course_entries: entriesData,
      });
      setCustomerNote(customerObj.note || '');
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
    setLoading(true);

    try {
      const { entriesData, messagesData } = await fetchGlobalData();

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
      const coursesRes = await fetchWithAuth(`/api/integrations/courses/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!coursesRes.ok) {
        const errorData = await coursesRes.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to import courses');
      }

      const emailsRes = await fetchWithAuth(`/api/integrations/emails/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!emailsRes.ok) {
        const errorData = await emailsRes.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to pull emails');
      }

      fetchCoursesAndCustomers();
      await fetchGlobalData();
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

    setGlobalMessages((prev) => prev.map((m) => 
      m.provider_message_id === updatedMsg.provider_message_id ? { ...m, ...updatedMsg } : m
    ));

    setSelectedEmail((prev) => (prev && prev.provider_message_id === updatedMsg.provider_message_id ? { ...prev, ...updatedMsg } : prev));
  };

  const handleToggleNeedsResponse = async () => {
    if (!selectedEmail) return;

    const newStatus = !selectedEmail.needs_response;
    setTogglingStatus(true);

    try {
      const statusRes = await fetchWithAuth(
        `/api/emails/status?provider_message_id=${encodeURIComponent(selectedEmail.provider_message_id)}&needs_response=${newStatus}`,
        { method: 'PATCH' }
      );

      if (!statusRes.ok) {
        throw new Error('Failed to update message status');
      }

      let updatedMessage;
      try {
        updatedMessage = await statusRes.json();
      } catch {
        updatedMessage = { ...selectedEmail, needs_response: newStatus };
      }

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
      const response = await fetchWithAuth(`/api/integrations/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipient_email: selectedEmail.customer_email,
          subject: `Re: ${selectedEmail.subject || 'No Subject'}`,
          body: replyText,
          reply_message_id: selectedEmail.provider_message_id,
          should_add_html: isHtmlReply
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send email');
      }

      const statusRes = await fetchWithAuth(
        `/api/emails/status?provider_message_id=${encodeURIComponent(selectedEmail.provider_message_id)}&needs_response=false`,
        { method: 'PATCH' }
      );

      if (!statusRes.ok) {
        throw new Error('Failed to update message status');
      }

      let updatedMessage;
      try {
        updatedMessage = await statusRes.json();
      } catch {
        updatedMessage = { ...selectedEmail, needs_response: false };
      }

      handleMessageUpdate(updatedMessage);
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
      const res = await fetchWithAuth(
        `/api/emails/move?provider_message_id=${encodeURIComponent(selectedEmail.provider_message_id)}&new_thread_id=${encodeURIComponent(moveThreadTarget)}`,
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

  const handleSaveCustomerNote = async () => {
    if (!selectedCustomer) return;
    setSavingCustomerNote(true);
    try {
      const res = await fetchWithAuth(
        `/api/customers/note?email_address=${encodeURIComponent(selectedCustomer)}&note_text=${encodeURIComponent(customerNote)}`,
        { method: 'PATCH' }
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to save note');
      }

      const updated = await res.json();
      setCustomers((prev) => prev.map((c) => (c.email === updated.email ? { ...c, note: updated.note } : c)));
      setCustomerHistory((prev) => ({
        ...prev,
        customer: { ...prev.customer, note: updated.note },
      }));
      setCustomerNote(updated.note || '');
      alert('Customer note saved');
    } catch (err) {
      console.error('Error saving customer note:', err);
      alert('Failed to save customer note');
    } finally {
      setSavingCustomerNote(false);
    }
  };

  const handleCourseEntryClick = async (entry) => {
    if (entry.seen !== false) return; 

    try {
      const res = await fetchWithAuth(`/api/courses/seen?provider_message_id=${encodeURIComponent(entry.provider_message_id)}&seen_status=true`, {
        method: 'PATCH',
      });
      
      if (res.ok) {
        const updatedEntry = await res.json();
        
        setCourseData((prev) => ({
          ...prev,
          entries: prev.entries.map((e) =>
            e.provider_message_id === updatedEntry.provider_message_id ? { ...e, ...updatedEntry } : e
          ),
        }));

        setCustomerHistory((prev) => ({
          ...prev,
          course_entries: prev.course_entries.map((e) =>
            e.provider_message_id === updatedEntry.provider_message_id ? { ...e, ...updatedEntry } : e
          ),
        }));

        setGlobalEntries((prev) => prev.map((e) =>
          e.provider_message_id === updatedEntry.provider_message_id ? { ...e, ...updatedEntry } : e
        ));
      }
    } catch (err) {
      console.error('Error marking course entry as seen:', err);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className={`app-shell theme-${theme}`} style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div className="panel" style={{ padding: '2rem', minWidth: '300px' }}>
          <h2>Login</h2>
          <form onSubmit={handleLoginSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="search-input"
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="search-input"
              required
            />
            <button type="submit" className="sync-button">
              Log In
            </button>
          </form>
        </div>
      </div>
    );
  }

  const q = searchQuery.trim().toLowerCase();

  const filteredCourses = courses
    .filter((c) => (q ? c.name.toLowerCase().includes(q) : true))
    .slice();
  filteredCourses.sort((a, b) => a.name.localeCompare(b.name));

  const filteredCustomers = customers
    .filter((c) => {
      if (!q) return true;
      const email = (c.email || '').toLowerCase();
      const name = (c.name || '').toLowerCase();
      const note = (c.note || '').toLowerCase();
      const company = (c.company_domain || '').toLowerCase();
      return email.includes(q) || name.includes(q) || note.includes(q) || company.includes(q);
    })
    .slice();
  filteredCustomers.sort((a, b) => (a.email).localeCompare(b.email));

  const customersByCompany = Object.entries(
    filteredCustomers.reduce((acc, c) => {
      const key = c.company_domain ?? 'No company';
      if (!acc[key]) acc[key] = [];
      acc[key].push(c);
      return acc;
    }, {})
  );

  const renderFilterRadios = () => (
    <div className="filter-group">
      <span className="filter-label">Resolved:</span>

      <label className="radio-label">
        <input
          type="radio"
          name="messageFilter"
          value="all"
          checked={messageFilter === "all"}
          onChange={(e) => setMessageFilter(e.target.value)}
        />
        All
      </label>

      <label className="radio-label">
        <input
          type="radio"
          name="messageFilter"
          value="no"
          checked={messageFilter === "no" || messageFilter === "true"}
          onChange={(e) => setMessageFilter(e.target.value)}
        />
        No
      </label>

      <label className="radio-label">
        <input
          type="radio"
          name="messageFilter"
          value="yes"
          checked={messageFilter === "yes" || messageFilter === "false"}
          onChange={(e) => setMessageFilter(e.target.value)}
        />
        Yes
      </label>
    </div>
  );

  return (
    <div className={`app-shell theme-${theme}`}>
      <header className="topbar">
        <div className="topbar-actions">
          <button className="theme-toggle" onClick={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))} type="button">
            {theme === 'dark' ? 'Light mode' : 'Dark mode'}
          </button>
          <button className="sync-button" onClick={handleSyncData} disabled={isSyncing} type="button">
            {isSyncing ? 'Syncing…' : 'Sync data'}
          </button>
          <button className="theme-toggle" onClick={handleLogout} type="button">
            Log out
          </button>
        </div>
      </header>

      <div className="dashboard-shell">
        <aside className="sidebar panel">
          <div className="segment-toggle" aria-label="Toggle data source">
            <button className={view === 'courses' ? 'segment active' : 'segment'} onClick={() => setView('courses')} type="button">Courses</button>
            <button className={view === 'customers' ? 'segment active' : 'segment'} onClick={() => setView('customers')} type="button">Customers</button>
          </div>

          <div className="list-controls">
            <input
              type="search"
              placeholder={view === 'courses' ? 'Search courses...' : 'Search customers...'}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
          </div>

          <div className="all-button-row divider-bottom">
            <button
              type="button"
              className={
                selectedCourse === 'All' || selectedCustomer === 'All'
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
          </div>

          <div className="list-panel">
            {view === 'courses' ? (
              filteredCourses.length === 0 ? (
                <div className="empty-state small">No courses match.</div>
              ) : (
                filteredCourses.map((item) => (
                  <button
                    key={item.id}
                    className={`${selectedCourse === item.name ? 'list-item active' : 'list-item'} list-item-plain course-item`}
                    onClick={() => handleCourseClick(item.name)}
                    type="button"
                  >
                    {item.name}
                  </button>
                ))
              )
            ) : (
              customersByCompany.length === 0 ? (
                <div className="empty-state small">No customers match.</div>
              ) : (
                customersByCompany.map(([companyName, custs]) => {
                  const isCollapsed = Boolean(collapsedCompanies[companyName]);

                  return (
                    <div key={companyName} className="company-group">
                      <div 
                        className="company-header"
                        onClick={() => toggleCompanyCollapse(companyName)}
                      >
                        <span className="company-header-arrow">{isCollapsed ? '▶' : '▼'}</span>
                        <span className="company-header-title">{companyName}</span>
                        <span className="company-header-count">({custs.length})</span>
                      </div>

                      {!isCollapsed && custs.map((item) => {
                        const hasUnseen = globalEntries.some(e => e.customer_email === item.email && e.seen === false) || 
                                          globalMessages.some(m => m.customer_email === item.email && m.seen === false);
                        
                        const textClass = hasUnseen ? 'is-unseen' : 'is-seen';
                        
                        return (
                          <button
                            key={item.id}
                            className={`${selectedCustomer === item.email ? 'list-item active' : 'list-item'} list-item-plain list-item-flex customer-item-nested`}
                            onClick={() => handleCustomerClick(item.email)}
                            type="button"
                          >
                            <div className="list-item-customer-details">
                              {item.name && (
                                <span className={`list-item-name ${textClass}`}>
                                  {item.name}
                                </span>
                              )}
                              <span className={`list-item-email ${textClass}`} title={item.email}>
                                {item.email}
                              </span>
                            </div>
                            
                            {item.note && (
                              <span className="list-item-note" title={item.note}>
                                {item.note}
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  );
                })
              )
            )}
          </div>
        </aside>

        <main className="content-panel panel">
          {loading && <p className="status-text-info">Loading details...</p>}

          {!loading && selectedCourse && (
            <div className="content-inner">
              <div className="panel-header">
                <h2>{selectedCourse}</h2>
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
                      {groupEntriesByDate(courseData.entries).map((group) => (
                        <li key={group.dateKey} className="entry-group">
                          <div className="entry-group-title">Date: {group.dateLabel} ({group.items.length})</div>
                          <ul className="group-entry-list">
                            {group.items.map((entry) => (
                              <li 
                                key={entry.id} 
                                className={`entry-item ${entry.seen === false ? 'is-unseen' : 'is-seen'}`}
                                onClick={() => handleCourseEntryClick(entry)}
                              >
                                <div><span>Course:</span> {entry.course_name}</div>
                                <div><span>Email:</span> {entry.customer_email}</div>
                              </li>
                            ))}
                          </ul>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ) : (
                <>
                  <div className="filter-header">
                    {renderFilterRadios()}
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
                <h2>
                  {
                    customerHistory.customer?.name
                      ? `${customerHistory.customer.name} (${customerHistory.customer?.email || selectedCustomer})`
                      : (customerHistory.customer?.email || selectedCustomer)
                  }
                </h2>
              </div>

              {customerHistory.customer && (
                <div className="customer-meta">
                  {customerHistory.customer.company_domain && (
                    <div className="customer-company">Company: {customerHistory.customer.company_domain}</div>
                  )}
                </div>
              )}

              {customerHistory.customer && selectedCustomer && selectedCustomer !== 'All' && (
                <div className="note-row">
                  <textarea
                    value={customerNote}
                    onChange={(e) => setCustomerNote(e.target.value)}
                    placeholder="Edit note..."
                    className="note-input"
                  />

                  <button
                    type="button"
                    onClick={handleSaveCustomerNote}
                    disabled={savingCustomerNote}
                    className="note-save-button"
                  >
                    {savingCustomerNote ? 'Saving...' : 'Save'}
                  </button>
                </div>
              )}

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
                    {renderFilterRadios()}
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
                      {groupEntriesByDate(customerHistory.course_entries).map((group) => (
                        <li key={group.dateKey} className="entry-group">
                          <div className="entry-group-title">Date: {group.dateLabel} ({group.items.length})</div>
                          <ul className="group-entry-list">
                            {group.items.map((entry) => (
                              <li 
                                key={entry.id} 
                                className={`entry-item ${entry.seen === false ? 'is-unseen' : 'is-seen'}`}
                                onClick={() => handleCourseEntryClick(entry)}
                              >
                                <div><span>Course:</span> {entry.course_name}</div>
                                <div><span>Email:</span> {entry.customer_email}</div>
                              </li>
                            ))}
                          </ul>
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
                <span className={`badge ${selectedEmail.needs_response ? 'badge-needs-response' : 'badge-resolved'}`}>{selectedEmail.needs_response ? 'Needs response' : 'Resolved'}</span>
                <span className="email-detail__timestamp">{selectedEmail.sent_at ? new Date(selectedEmail.sent_at).toLocaleString() : ''}</span>
              </div>

              <div className="email-detail__header-info">
                <div className="email-detail__from">
                  <strong>From:</strong> {selectedEmail.customer_email}
                </div>
                <div className="email-detail__subject">
                  <strong>Subject:</strong> {selectedEmail.subject || '(No Subject)'}
                </div>
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

                <div className="move-message-row">
                  <input
                    type="number"
                    placeholder="Move ID"
                    value={moveThreadTarget}
                    onChange={(e) => setMoveThreadTarget(e.target.value)}
                    className="input-target-id"
                  />
                  <button type="button" className="btn-merge" onClick={handleMoveMessage} disabled={movingEmail}>
                    {movingEmail ? 'Moving...' : 'Move'}
                  </button>
                </div>
              </div>

              {isReplying && (
                <div className="reply-form compact">
                  <div className="reply-form-header">
                    <button type="button" className="btn-send" onClick={handleSendReply} disabled={sendingReply}>
                      {sendingReply ? 'Sending...' : 'Send'}
                    </button>
                    <button type="button" className="btn-cancel" onClick={() => setIsReplying(false)}>
                      Cancel
                    </button>
                    <label className="html-toggle-label">
                      <input 
                        type="checkbox" 
                        checked={isHtmlReply} 
                        onChange={(e) => setIsHtmlReply(e.target.checked)} 
                      />
                      HTML
                    </label>
                  </div>
                  <textarea
                    rows="4"
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    placeholder="Type your reply here..."
                    className="reply-textarea"
                  />
                </div>
              )}

              <div 
                className="email-body" 
                dangerouslySetInnerHTML={{ 
                  __html: selectedEmail.body 
                    ? DOMPurify.sanitize(selectedEmail.body) 
                    : '<p>No email body available.</p>' 
                }} 
              />
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

export default App;
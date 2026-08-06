import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

// Helper component to display an email message with an expandable body and reply functionality
function DisplayEmail({ msg, customerEmail }) {
  const [replyBody, setReplyBody] = useState('');
  const [isReplying, setIsReplying] = useState(false);
  const [sending, setSending] = useState(false);
  const [needsResponse, setNeedsResponse] = useState(msg.needs_response);

  // Use the explicitly passed customer email or fall back to properties if needed
  const emailAddress = customerEmail || "Unknown";

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
          reply_message_id: msg.provider_message_id
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send email');
      }

      // Update message status needs_response to false after successful send
      const statusRes = await fetch(`${API_BASE_URL}/api/messages/${msg.provider_message_id}/status?needs_response=false`, {
        method: 'PATCH',
      });
      
      if (statusRes.ok) {
        const data = await statusRes.json();
        setNeedsResponse(data.needs_response);
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
    <li key={msg.provider_message_id} style={{ marginBottom: '15px', borderBottom: '1px solid #ddd', paddingBottom: '10px' }}>
      <strong>Subject:</strong> {msg.subject} <br />
      <strong>Email:</strong> {emailAddress} <br />
      <strong>Date:</strong> {msg.sent_at ? new Date(msg.sent_at).toLocaleString() : ''} <br />
      <strong>Needs Response:</strong>{' '}
      <span style={{ color: needsResponse ? 'red' : 'green', fontWeight: 'bold' }}>
        {needsResponse ? 'Yes' : 'No'}
      </span> <br />
      
      <details style={{ marginTop: '5px', border: '1px solid #ccc', borderRadius: '4px', background: '#fff' }}>
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
            style={{ padding: '4px 10px', background: '#007bff', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Answer
          </button>
        ) : (
          <div style={{ marginTop: '8px', padding: '10px', background: '#f9f9f9', border: '1px solid #ddd', borderRadius: '4px' }}>
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
                style={{ padding: '4px 10px', background: '#28a745', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', marginRight: '6px' }}
              >
                {sending ? 'Sending...' : 'Send Reply'}
              </button>
              <button 
                onClick={() => setIsReplying(false)}
                style={{ padding: '4px 10px', background: '#6c757d', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
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
        fetch(`${API_BASE_URL}/api/courses/${encodeURIComponent(courseName)}/messages`)
      ]);

      const entriesData = await entriesRes.json();
      const messagesData = await messagesRes.json();

      setCourseData({
        entries: entriesData.course_entries || [],
        messages: messagesData.messages || []
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
      const response = await fetch(`${API_BASE_URL}/api/customers/${encodeURIComponent(email)}/history`);
      const data = await response.json();

      setCustomerHistory({
        customer: data.customer || { email },
        messages: data.messages || [],
        course_entries: data.course_entries || []
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
      const historyPromises = customers.map((c) =>
        fetch(`${API_BASE_URL}/api/customers/${encodeURIComponent(c.customer_email)}/history`)
          .then((res) => res.json())
          .catch(() => ({ customer: c, messages: [], course_entries: [] }))
      );

      const results = await Promise.all(historyPromises);
      
      const allMsgsMap = new Map();
      const allEntriesMap = new Map();

      results.forEach((res) => {
        const customerEmail = res.customer?.email;
        (res.messages || []).forEach((m) => {
          // Attach customer_email to the message object if not present
          allMsgsMap.set(m.provider_message_id, { ...m, customer_email: customerEmail || m.customer_email });
        });
        (res.course_entries || []).forEach((e) => {
          allEntriesMap.set(e.course_entry_id, { ...e, customer_email: customerEmail || e.customer_email });
        });
      });

      setAllCustomersData({
        messages: Array.from(allMsgsMap.values()),
        course_entries: Array.from(allEntriesMap.values())
      });
    } catch (err) {
      console.error('Error fetching all customers history:', err);
    } finally {
      setLoading(false);
    }
  };

  // Helper function to filter messages based on needs_response selection
  const filterMessages = (messages) => {
    return messages.filter((msg) => {
      if (messageFilter === 'true') return msg.needs_response === true;
      if (messageFilter === 'false') return msg.needs_response === false;
      return true;
    });
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
                      cursor: 'pointer'
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
                  fontSize: '14px'
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
                      cursor: 'pointer'
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
        <div className="details-column" style={{ flex: '2', background: '#fdfdfd', padding: '20px', border: '1px solid #eee', borderRadius: '6px' }}>
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
                <h3 style={{ margin: 0 }}>Related Messages</h3>
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

              {filterMessages(courseData.messages).length === 0 ? (
                <p style={{ marginTop: '10px' }}>No messages found matching the filter.</p>
              ) : (
                <ul style={{ marginTop: '10px' }}>
                  {filterMessages(courseData.messages).map((msg) => (
                    <DisplayEmail key={msg.provider_message_id} msg={msg} customerEmail={msg.customer_email} />
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Customer Details View */}
          {!loading && selectedCustomer && (
            <div>
              <h2>Customer History: {selectedCustomer}</h2>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px' }}>
                <h3 style={{ margin: 0 }}>Messages</h3>
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

              {filterMessages(customerHistory.messages).length === 0 ? (
                <p style={{ marginTop: '10px' }}>No messages found matching the filter.</p>
              ) : (
                <ul style={{ marginTop: '10px' }}>
                  {filterMessages(customerHistory.messages).map((msg) => (
                    <DisplayEmail key={msg.provider_message_id} msg={msg} customerEmail={customerHistory.customer?.email || selectedCustomer} />
                  ))}
                </ul>
              )}

              <h3>Course Entries</h3>
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
                <h3 style={{ margin: 0 }}>All Messages</h3>
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

              {filterMessages(allCustomersData.messages).length === 0 ? (
                <p style={{ marginTop: '10px' }}>No messages found matching the filter.</p>
              ) : (
                <ul style={{ marginTop: '10px' }}>
                  {filterMessages(allCustomersData.messages).map((msg) => (
                    <DisplayEmail key={msg.provider_message_id} msg={msg} customerEmail={msg.customer_email} />
                  ))}
                </ul>
              )}

              <h3>All Course Entries</h3>
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
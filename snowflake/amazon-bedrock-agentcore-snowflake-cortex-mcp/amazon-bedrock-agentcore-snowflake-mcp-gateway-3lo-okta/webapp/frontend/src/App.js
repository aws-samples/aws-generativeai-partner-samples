import React, { useState, useRef, useEffect, useCallback } from 'react';
import { signIn, completeNewPassword, getCurrentSession, signOut } from './auth';

const API = process.env.REACT_APP_API_URL || '/api';

function LoginScreen({ onLogin }) {
  const [mode, setMode] = useState('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [cognitoUser, setCognitoUser] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getCurrentSession().then(session => { if (session) onLogin(session); });
  }, [onLogin]);

  const handleSignIn = async (e) => {
    e.preventDefault(); setError(''); setLoading(true);
    try {
      const result = await signIn(email, password);
      if (result.newPasswordRequired) { setCognitoUser(result.user); setMode('newpassword'); }
      else onLogin(result);
    } catch (err) { setError(err.message || 'Sign in failed'); }
    setLoading(false);
  };

  const handleNewPassword = async (e) => {
    e.preventDefault(); setError(''); setLoading(true);
    try { onLogin(await completeNewPassword(cognitoUser, newPassword)); }
    catch (err) { setError(err.message || 'Password change failed'); }
    setLoading(false);
  };

  return (
    <div className="login-screen">
      <div className="login-box">
        <h2>🏦 Credit Risk Console</h2>
        <p>3LO + Okta — Hybrid RAG: Bedrock KB + Snowflake MCP Server (SSO via Okta, Per-User Auth)</p>
        {error && <div className="login-error">{error}</div>}
        {mode === 'signin' ? (
          <form onSubmit={handleSignIn}>
            <input type="email" placeholder="Staff email" value={email} onChange={e => setEmail(e.target.value)} autoFocus required />
            <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required />
            <button type="submit" disabled={loading}>{loading ? 'Signing in...' : 'Sign In'}</button>
          </form>
        ) : (
          <form onSubmit={handleNewPassword}>
            <h3>Set New Password</h3>
            <input type="password" placeholder="New password (min 8 chars)" value={newPassword} onChange={e => setNewPassword(e.target.value)} required minLength={8} />
            <button type="submit" disabled={loading}>{loading ? 'Setting...' : 'Set Password & Sign In'}</button>
          </form>
        )}
      </div>
    </div>
  );
}


function fmtMs(ms) {
  if (ms === null || ms === undefined) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function TracePanel({ trace }) {
  if (!trace) return (
    <div className="trace-panel">
      <h3>Agent Trace</h3>
      <div className="trace-empty">Send a message to see the agent trace.</div>
    </div>
  );

  const toolCalls = trace.tool_calls || [];
  const hasCortex = toolCalls.some(tc => tc.tool === 'cortex_search' || tc.tool === 'cortex_analyst');
  const e2e = trace.end_to_end_ms;
  const reasoning = trace.reasoning_ms;
  const overhead = trace.overhead_ms;

  return (
    <div className="trace-panel">
      <h3>Agent Trace</h3>
      <div className="trace-item timings">
        <div className="label">⏱ Timing</div>
        <div className="timing-grid">
          <span>End-to-end</span><span>{fmtMs(e2e)}</span>
          <span>Reasoning</span><span>{fmtMs(reasoning)}</span>
          <span>Tools total</span><span>{fmtMs(toolCalls.reduce((s, t) => s + (t.duration_ms || 0), 0))}</span>
          <span>Overhead</span><span>{fmtMs(overhead)}</span>
        </div>
      </div>
      <div className="trace-item">
        <div className="label">🔐 Cognito JWT Auth</div>
        <div className="detail">Verified ✅</div>
      </div>
      <div className="trace-item">
        <div className="label">🤖 AgentCore Runtime <span className="duration-badge">{fmtMs(trace.agent_elapsed_ms)}</span></div>
        <div className="detail">Claude Sonnet 4.5 • Strands Agent</div>
        <div className="detail">Tools called: {toolCalls.length} · Reasoning: {fmtMs(reasoning)}</div>
      </div>
      {toolCalls.map((tc, i) => {
        const name = tc.tool || '';
        const dur = <span className="duration-badge">{fmtMs(tc.duration_ms)}</span>;
        if (name === 'knowledge_base_search') return (
          <div key={i} className="trace-item">
            <div className="label">📚 knowledge_base_search {dur}</div>
            <div className="detail">Bedrock KB → OpenSearch Serverless</div>
          </div>
        );
        if (name === 'cortex_search') return (
          <div key={i} className="trace-item">
            <div className="label">🔍 cortex_search {dur}</div>
            <div className="detail">Gateway → Snowflake MCP (Cortex Search)</div>
            <div className="detail">Cedar: ENFORCE ✅ | 3LO + Okta: Per-user SSO ✅</div>
          </div>
        );
        if (name === 'cortex_analyst') return (
          <div key={i} className="trace-item">
            <div className="label">📊 cortex_analyst {dur}</div>
            <div className="detail">Gateway → Snowflake MCP (Cortex Analyst)</div>
            <div className="detail">Cedar: ENFORCE ✅ | 3LO + Okta: Per-user SSO ✅</div>
          </div>
        );
        return <div key={i} className="trace-item"><div className="label">🔧 {name} {dur}</div></div>;
      })}
      {toolCalls.length === 0 && (
        <div className="trace-item"><div className="label">🧠 Agent Reasoning</div><div className="detail">No external tools invoked</div></div>
      )}
      {hasCortex && (
        <div className="trace-item"><div className="label">🔑 AgentCore Identity (3LO + Okta)</div><div className="detail">Okta SSO → Snowflake External OAuth ✅</div></div>
      )}
      <div className="trace-item">
        <div className="label">🛡️ Bedrock Guardrail</div>
        {trace.guardrail_blocked ? (
          <span className="guardrail-badge blocked">{trace.guardrail_reason}</span>
        ) : (
          <span className="guardrail-badge clear">Passed</span>
        )}
      </div>
    </div>
  );
}

function TraceModal() { return null; }

export default function App() {
  const [auth, setAuth] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [customerId, setCustomerId] = useState('C-1042');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [trace, setTrace] = useState(null);
  const [activeScenario, setActiveScenario] = useState(null);
  const [sfConnected, setSfConnected] = useState(() => localStorage.getItem('sf_connected') === 'true');
  const [sfConnecting, setSfConnecting] = useState(false);
  const [snowflakeIdentity, setSnowflakeIdentity] = useState(() => {
    try { return JSON.parse(localStorage.getItem('sf_identity') || 'null'); } catch { return null; }
  });
  const messagesEnd = useRef(null);

  const getHeaders = useCallback(async () => {
    const session = await getCurrentSession();
    if (!session) { signOut(); setAuth(null); return null; }
    if (session.token !== auth?.token) setAuth(session);
    return { 'Content-Type': 'application/json', Authorization: `Bearer ${session.token}` };
  }, [auth]);

  // --- Handle /auth/okta-callback route ---
  useEffect(() => {
    const path = window.location.pathname;
    if (path !== '/auth/okta-callback') return;
    // Prevent double execution
    if (window._ssoCallbackHandled) return;
    window._ssoCallbackHandled = true;

    const params = new URLSearchParams(window.location.search);
    const sessionUri = params.get('session_id') || params.get('session_uri') || params.get('sessionUri') || params.get('sessionId');
    console.log('[3LO+Okta callback] search:', window.location.search, 'sessionUri:', sessionUri);

    if (!sessionUri) {
      console.error('[3LO+Okta callback] No session_id in callback URL');
      window.location.href = '/';
      return;
    }

    // Complete the auth flow, then redirect to main app
    (async () => {
      try {
        const h = await getHeaders();
        if (!h) {
          console.error('[3LO+Okta callback] No Cognito session');
          window.location.href = '/';
          return;
        }
        const resp = await fetch(`${API}/auth/complete-sso-auth`, {
          method: 'POST', headers: h,
          body: JSON.stringify({ session_uri: sessionUri }),
        });
        if (resp.ok) {
          console.log('[3LO+Okta callback] CompleteResourceTokenAuth succeeded');
          localStorage.setItem('sf_connected', 'true');
          try {
            const data = await resp.json();
            if (data.identity) {
              localStorage.setItem('sf_identity', JSON.stringify(data.identity));
            }
          } catch {}
        } else {
          const err = await resp.text();
          console.error('[3LO+Okta callback] CompleteResourceTokenAuth failed:', resp.status, err);
        }
      } catch (e) {
        console.error('[3LO+Okta callback] Error:', e);
      }
      window.location.href = '/';
    })();
  }, []); // eslint-disable-line

  useEffect(() => {
    if (!auth) return;
    const h = { Authorization: `Bearer ${auth.token}` };
    fetch(`${API}/scenarios`, { headers: h }).then(r => r.json()).then(setScenarios).catch(() => {});
    fetch(`${API}/customers`, { headers: h }).then(r => r.json()).then(setCustomers).catch(() => {});
    // Restore Snowflake identity from server cache if available
    fetch(`${API}/auth/sso-status`, { headers: h }).then(r => r.json()).then(d => {
      if (d.connected && d.identity) {
        setSnowflakeIdentity(d.identity);
        setSfConnected(true);
        localStorage.setItem('sf_connected', 'true');
        localStorage.setItem('sf_identity', JSON.stringify(d.identity));
      }
    }).catch(() => {});
  }, [auth]);

  useEffect(() => { messagesEnd.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handleLogout = () => {
    signOut(); setAuth(null); setMessages([]); setTrace(null);
    localStorage.removeItem('sf_connected');
    localStorage.removeItem('sf_identity');
    setSfConnected(false);
    setSnowflakeIdentity(null);
  };

  // --- Connect to Okta (3LO SSO) ---
  const connectSso = async () => {
    setSfConnecting(true);
    try {
      const h = await getHeaders();
      if (!h) return;
      const resp = await fetch(`${API}/auth/sso-auth-url`, { headers: h });
      if (!resp.ok) throw new Error('Failed to get auth URL');
      const data = await resp.json();
      if (data.auth_url) {
        // Navigate to Okta login in the same tab
        window.location.href = data.auth_url;
      } else {
        // Already connected — backend may have returned the identity
        localStorage.setItem('sf_connected', 'true');
        setSfConnected(true);
        if (data.identity) {
          setSnowflakeIdentity(data.identity);
          localStorage.setItem('sf_identity', JSON.stringify(data.identity));
        }
      }
    } catch (e) {
      console.error('Connect Okta failed:', e);
      alert('Failed to initiate Okta SSO. Please try again.');
    } finally {
      setSfConnecting(false);
    }
  };

  const sendMessage = async (prompt, sendCustomerId = true) => {
    if (!prompt.trim() || loading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: prompt }]);
    setLoading(true);
    setTrace(null);
    try {
      const h = await getHeaders();
      if (!h) return;
      const res = await fetch(`${API}/chat`, {
        method: 'POST', headers: h,
        body: JSON.stringify({ prompt, ...(sendCustomerId && customerId ? { customer_id: customerId } : {}) }),
      });
      if (res.status === 401) { signOut(); setAuth(null); return; }
      if (!res.ok) throw new Error('Request failed');
      const data = await res.json();

      if (data.job_id) {
        const pollStart = Date.now();
        for (let i = 0; i < 100; i++) {
          await new Promise(r => setTimeout(r, 3000));
          const elapsed = Math.round((Date.now() - pollStart) / 1000);
          setMessages(prev => {
            const msgs = [...prev];
            const last = msgs[msgs.length - 1];
            const step = elapsed < 15 ? 'Agent is processing your request'
              : elapsed < 60 ? 'Still working (multi-tool queries take 60-120s)'
              : elapsed < 120 ? 'Almost done — synthesizing results'
              : 'Still processing — please wait';
            const msg = `⏳ Working... ${elapsed}s — ${step}`;
            if (last?.role === 'assistant' && last.polling) {
              msgs[msgs.length - 1] = { ...last, content: msg };
            } else {
              msgs.push({ role: 'assistant', content: msg, polling: true });
            }
            return msgs;
          });
          try {
            const ph = await getHeaders();
            if (!ph) return;
            const pr = await fetch(`${API}/chat/status/${data.job_id}`, { headers: ph });
            if (!pr.ok) continue;
            const pd = await pr.json();

            // 3LO: If auth required, prompt user to connect first
            if (pd.status === 'sso_auth_required') {
              localStorage.removeItem('sf_connected');
              localStorage.removeItem('sf_identity');
              setSfConnected(false);
              setSnowflakeIdentity(null);
              setMessages(prev => {
                const msgs = prev.filter(m => !m.polling);
                msgs.push({ role: 'assistant', content: '🔐 Okta sign-in required. Please click the "Sign in with Okta" button in the header, then retry your question.' });
                return msgs;
              });
              return;
            }

            if (pd.status === 'done' || pd.status === 'error') {
              setMessages(prev => {
                const msgs = prev.filter(m => !m.polling);
                msgs.push({ role: 'assistant', content: pd.response, trace: pd });
                return msgs;
              });
              setTrace(pd);
              return;
            }
          } catch (e) { /* retry on network error */ }
        }
        setMessages(prev => {
          const msgs = prev.filter(m => !m.polling);
          msgs.push({ role: 'assistant', content: 'Request timed out after 5 minutes. Please try again.' });
          return msgs;
        });
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: data.response, trace: data }]);
        setTrace(data);
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  if (!auth) return <LoginScreen onLogin={setAuth} />;

  return (
    <div className="app-layout">
      <div className="header">
        <div className="header-left">
          <h1>🏦 Credit Risk Assessment Console</h1>
          <span className="tag">3LO + Okta — Hybrid RAG: KB + Snowflake MCP Server (SSO via Okta, Per-User Auth)</span>
        </div>
        <div className="header-right">
          {sfConnected ? (
            <span className="sf-badge connected" title="Snowflake identity (via Okta SSO, External OAuth)">
              ❄️ Connected · {snowflakeIdentity ? `${snowflakeIdentity.user} / ${snowflakeIdentity.role}` : 'Snowflake'}
            </span>
          ) : (
            <button className="sf-connect-btn" onClick={connectSso} disabled={sfConnecting}>
              {sfConnecting ? '⏳ Connecting...' : '🔐 Sign in with Okta'}
            </button>
          )}
          <span className="user-badge">{auth.name || auth.email}</span>
          <button onClick={handleLogout}>Logout</button>
        </div>
      </div>

      <div className="main-content">
        <div className="sidebar">
          <div className="section">
            <h3>Demo Scenarios</h3>
            {scenarios.map(s => (
              <button key={s.id} className={`scenario-btn${activeScenario === s.id ? ' active' : ''}`} onClick={() => {
                setActiveScenario(s.id);
                if (s.customer_id) setCustomerId(s.customer_id);
                sendMessage(s.prompt, !!s.customer_id);
              }}>
                {s.label}
                <span className="desc">{s.description}</span>
              </button>
            ))}
          </div>
          <div className="section">
            <h3>Customer</h3>
            <select className="customer-select" value={customerId} onChange={e => setCustomerId(e.target.value)}>
              {customers.map(c => (
                <option key={c.id} value={c.id}>{c.id} — {c.name} ({c.segment}{c.score ? `, ${c.score}` : ''})</option>
              ))}
            </select>
          </div>
        </div>

        <div className="chat-area">
          <div className="messages">
            {messages.length === 0 && (
              <div style={{ color: '#546e7a', textAlign: 'center', marginTop: 60, fontSize: 14 }}>
                {!sfConnected && <div style={{ marginBottom: 16, padding: '12px 16px', background: '#fff3e0', borderRadius: 8, display: 'inline-block' }}>
                  🔐 <strong>Step 1:</strong> Click "Sign in with Okta" in the header to authenticate via SSO. Snowflake will trust the Okta-issued token and run queries as your user.
                </div>}
                <div>Select a demo scenario or type a question about a customer.</div>
              </div>
            )}
            {messages.map((m, i) => {
              // Is this the first assistant message that used a Snowflake tool?
              const usedSf = m.role === 'assistant' && m.trace?.tool_calls?.some(
                tc => tc.tool === 'cortex_search' || tc.tool === 'cortex_analyst'
              );
              const firstSfIdx = messages.findIndex(x =>
                x.role === 'assistant' && x.trace?.tool_calls?.some(
                  tc => tc.tool === 'cortex_search' || tc.tool === 'cortex_analyst'
                )
              );
              const showCallout = usedSf && i === firstSfIdx && snowflakeIdentity;
              return (
                <div key={i} className={`msg ${m.role}`}>
                  <div className="role">{m.role}</div>
                  <div className="bubble">{m.content}</div>
                  {m.role === 'assistant' && m.trace && (
                    <button
                      className={`trace-pill${trace === m.trace ? ' active' : ''}`}
                      onClick={() => setTrace(m.trace)}
                    >
                      📊 View Trace · {(m.trace.tool_calls || []).length} tools · {fmtMs(m.trace.end_to_end_ms)}
                    </button>
                  )}
                  {showCallout && (
                    <div className="first-sf-callout">
                      ↑ This query ran in Snowflake as <b>{snowflakeIdentity.user}</b> / <b>{snowflakeIdentity.role}</b> — see header
                    </div>
                  )}
                </div>
              );
            })}
            {loading && !messages.some(m => m.polling) && <div className="typing-indicator">⏳ Agent is processing your request...</div>}
            <div ref={messagesEnd} />
          </div>
          <div className="chat-input">
            <input
              placeholder={`Ask about customer ${customerId}...`}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage(input)}
              disabled={loading}
            />
            <button onClick={() => sendMessage(input)} disabled={loading || !input.trim()}>Send</button>
          </div>
        </div>

        <TracePanel trace={trace} />
      </div>

    </div>
  );
}

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
        <p>MCP 2LO — Hybrid RAG: Bedrock KB + Snowflake MCP Server</p>
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
  if (ms == null) return '—';
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

function TracePanel({ trace }) {
  if (!trace) return (
    <div className="trace-panel">
      <h3>Agent Trace</h3>
      <div className="trace-empty">Send a message to see the agent trace.</div>
    </div>
  );

  const toolCalls = trace.tool_calls || [];
  const traceEntries = trace.trace || [];
  const agentEntry = traceEntries.find(t => t.type === 'agent');
  const timings = agentEntry?.timings || {};
  const toolTimings = timings.tools || [];
  const reasoningMs = timings.reasoning_ms;
  const toolsTotal = toolTimings.reduce((s, t) => s + (t.total_ms || 0), 0);
  const e2e = trace.end_to_end_ms;
  const agentMs = timings.total_ms || (agentEntry?.total_time ? Math.round(agentEntry.total_time * 1000) : null);
  const overhead = (e2e != null && agentMs != null) ? Math.max(0, e2e - agentMs) : null;
  const hasCortex = toolCalls.some(tc => tc.tool === 'cortex_search' || tc.tool === 'cortex_analyst');

  const getToolTiming = (toolName) => {
    const mcp = { 'cortex_search': 'customer-profile-search', 'cortex_analyst': 'credit-risk-analyst' };
    const key = mcp[toolName] || toolName;
    return toolTimings.find(t => t.tool === key || t.tool === toolName);
  };

  return (
    <div className="trace-panel">
      <h3>Agent Trace</h3>

      <div className="trace-item timings">
        <div className="label">⏱ Timing</div>
        <div className="timing-grid">
          <span>End-to-end</span><span>{fmtMs(e2e)}</span>
          <span>Reasoning</span><span>{fmtMs(reasoningMs)}</span>
          <span>Tools total</span><span>{fmtMs(toolsTotal)}</span>
          <span>Overhead</span><span>{fmtMs(overhead)}</span>
        </div>
      </div>

      <div className="trace-item">
        <div className="label">🔐 Cognito JWT Auth</div>
        <div className="detail">Verified ✅</div>
      </div>

      <div className="trace-item">
        <div className="label">🤖 AgentCore Runtime <span className="duration-badge">{fmtMs(agentMs)}</span></div>
        <div className="detail">Claude Sonnet 4.5 • Strands Agent</div>
        <div className="detail">Tools called: {toolCalls.length} · Reasoning: {fmtMs(reasoningMs)}</div>
      </div>

      {toolCalls.map((tc, i) => {
        const name = tc.tool || '';
        const timing = getToolTiming(name);
        const dur = timing ? <span className="duration-badge">{fmtMs(timing.total_ms)}</span> : null;
        const gatewayMs = timing?.gateway_ms ? fmtMs(timing.gateway_ms) : null;
        const tokenMs = timing?.token_ms;
        const tokenLabel = tokenMs != null ? (tokenMs < 50 ? 'cached' : fmtMs(tokenMs)) : null;

        if (name === 'knowledge_base_search') return (
          <div key={i} className="trace-item">
            <div className="label">📚 knowledge_base_search {dur}</div>
            <div className="detail">Bedrock KB → OpenSearch Serverless</div>
            <div className="detail">Source: S3 policy PDFs (Titan Embed v2)</div>
          </div>
        );
        if (name === 'cortex_search') return (
          <div key={i} className="trace-item">
            <div className="label">🔍 cortex_search {dur}</div>
            <div className="detail">AgentCore Gateway → Snowflake MCP Server</div>
            <div className="detail">MCP tool: customer-profile-search (Cortex Search)</div>
            {gatewayMs && <div className="detail">Snowflake + Gateway processing: {gatewayMs}{tokenLabel && ` | Token: ${tokenLabel}`}</div>}
            <div className="detail">Cedar Policy: ENFORCE ✅</div>
          </div>
        );
        if (name === 'cortex_analyst') return (
          <div key={i} className="trace-item">
            <div className="label">📊 cortex_analyst {dur}</div>
            <div className="detail">AgentCore Gateway → Snowflake MCP Server</div>
            <div className="detail">MCP tools: credit-risk-analyst + sql-exec (Cortex Analyst → Execute SQL)</div>
            {gatewayMs && <div className="detail">Snowflake + Gateway processing: {gatewayMs}{tokenLabel && ` | Token: ${tokenLabel}`}</div>}
            <div className="detail">Cedar Policy: ENFORCE ✅</div>
          </div>
        );
        return (
          <div key={i} className="trace-item">
            <div className="label">🔧 {name} {dur}</div>
          </div>
        );
      })}

      {toolCalls.length === 0 && (
        <div className="trace-item">
          <div className="label">🧠 Agent Reasoning</div>
          <div className="detail">No external tools invoked</div>
        </div>
      )}

      {hasCortex && (
        <div className="trace-item">
          <div className="label">🔑 AgentCore Identity</div>
          <div className="detail">Okta OAuth → Snowflake External OAuth ✅</div>
        </div>
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
  const messagesEnd = useRef(null);

  const getHeaders = useCallback(async () => {
    const session = await getCurrentSession();
    if (!session) { signOut(); setAuth(null); return null; }
    if (session.token !== auth?.token) setAuth(session);
    return { 'Content-Type': 'application/json', Authorization: `Bearer ${session.token}` };
  }, [auth]);

  useEffect(() => {
    if (!auth) return;
    const h = { Authorization: `Bearer ${auth.token}` };
    fetch(`${API}/scenarios`, { headers: h }).then(r => r.json()).then(setScenarios).catch(() => {});
    fetch(`${API}/customers`, { headers: h }).then(r => r.json()).then(setCustomers).catch(() => {});
  }, [auth]);

  useEffect(() => { messagesEnd.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handleLogout = () => { signOut(); setAuth(null); setMessages([]); setTrace(null); };

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
        const pollForResult = async () => {
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
              if (last && last.role === 'assistant' && last.polling) {
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
        };
        await pollForResult();
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
          <span className="tag">MCP 2LO — Hybrid RAG: KB + Snowflake MCP Server</span>
        </div>
        <div className="header-right">
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
                Select a demo scenario or type a question about a customer.
              </div>
            )}
            {messages.map((m, i) => (
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
              </div>
            ))}
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

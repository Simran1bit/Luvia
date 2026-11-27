import React, { useEffect, useRef, useState } from 'react';
import './chatbot.css';

const API = import.meta.env.VITE_LUVIA_CHATBOT_API || '/api/chatbot/chat';
const starters = [
  "What's the current weather in Delhi?",
  "Show recent floods in India",
  "Are there any active warnings in Delhi?",
  "What is a heatwave?",
  "Give me the forecast for tomorrow in Mumbai"
];
const POS_KEY = 'luvia-chat-fab-pos';
const DRAG_THRESHOLD = 6; // px of movement before a press counts as a drag, not a tap
const EDGE = 10;          // keep the launcher this far from the viewport edges

function clamp(x, y, w, h) {
  return {
    x: Math.round(Math.min(Math.max(EDGE, x), window.innerWidth - w - EDGE)),
    y: Math.round(Math.min(Math.max(EDGE, y), window.innerHeight - h - EDGE))
  };
}

const greeting ={ role: 'assistant', text: "Hello! I'm LUVIA's Weather Assistant. Ask me about current weather, forecasts, historical events, IMD warnings, or weather safety." };

// Small inline icons (this folder sits outside frontend/, so no icon package imports here).
const Icon = {
  chat: <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.9A8 8 0 1 1 21 12z"/><path d="M8.5 12h.01M12 12h.01M15.5 12h.01" strokeWidth="2.6"/></svg>,
  close: <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>,
  send: <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4z"/></svg>,
  reset: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/></svg>
};

export default function Chatbot() {
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(false);
  const [messages, setMessages] = useState([greeting]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [session, setSession] = useState(() => `luv-${Date.now()}`);
  const bottom = useRef(null);
  const inputRef = useRef(null);
  const openRef = useRef(open);
  openRef.current = open;

  // ---- Draggable launcher ----
  const fabRef = useRef(null);
  const drag = useRef(null);
  const justDragged = useRef(false);
  const [dragging, setDragging] = useState(false);
  const [pos, setPos] = useState(() => {
    try { return JSON.parse(localStorage.getItem(POS_KEY)) || null; } catch { return null; }
  });

  // Keep the button on screen when the window resizes (or a saved spot no longer fits).
  useEffect(() => {
    const fit = () => setPos(p => {
      if (!p || !fabRef.current) return p;
      const { width, height } = fabRef.current.getBoundingClientRect();
      const c = clamp(p.x, p.y, width, height);
      return c.x === p.x && c.y === p.y ? p : c;
    });
    fit();
    window.addEventListener('resize', fit);
    return () => window.removeEventListener('resize', fit);
  }, []);

  function onPointerDown(e) {
    if (e.button !== 0) return;
    const r = e.currentTarget.getBoundingClientRect();
    drag.current = { sx: e.clientX, sy: e.clientY, ox: r.left, oy: r.top, w: r.width, h: r.height, moved: false };
    e.currentTarget.setPointerCapture(e.pointerId);
  }

  function onPointerMove(e) {
    const d = drag.current;
    if (!d) return;
    const dx = e.clientX - d.sx, dy = e.clientY - d.sy;
    if (!d.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
    if (!d.moved) { d.moved = true; setDragging(true); }
    setPos(clamp(d.ox + dx, d.oy + dy, d.w, d.h));
  }

  function onPointerUp() {
    const d = drag.current;
    drag.current = null;
    if (!d?.moved) return;
    justDragged.current = true; // swallow the click that follows a drag
    setDragging(false);
    setPos(p => { try { localStorage.setItem(POS_KEY, JSON.stringify(p)); } catch { /* ignore */ } return p; });
  }

  function onFabClick() {
    if (justDragged.current) { justDragged.current = false; return; }
    setOpen(true);
  }

  useEffect(() => {
    if (open) bottom.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading, open]);

  useEffect(() => {
    if (!open) return;
    setUnread(false);
    const t = setTimeout(() => inputRef.current?.focus(), 320);
    const onKey = e => { if (e.key === 'Escape') setOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => { clearTimeout(t); window.removeEventListener('keydown', onKey); };
  }, [open]);

  async function send(value = input) {
    const question = value.trim();
    if (!question || loading) return;

    setMessages(m => [...m, { role: 'user', text: question }]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: question, session_id: session })
      });
      if (!response.ok) throw new Error(`Server returned ${response.status}`);

      const result = await response.json();
      setMessages(m => [...m, {
        role: 'assistant',
        text: result.answer,
        data: result.data,
        sources: result.sources,
        disclaimer: result.disclaimer
      }]);
    } catch (e) {
      setMessages(m => [...m, {
        role: 'assistant',
        text: `I couldn't reach the LUVIA chatbot service. Check that the backend is running. (${e.message})`,
        error: true
      }]);
    } finally {
      setLoading(false);
      if (!openRef.current) setUnread(true);
    }
  }

  function resetChat() {
    setMessages([greeting]);
    setSession(`luv-${Date.now()}`);
    setInput('');
  }

  return (
    <>
      <div className={`lc-backdrop ${open ? 'show' : ''}`} onClick={() => setOpen(false)} aria-hidden="true" />

      <button
        ref={fabRef}
        className={`lc-fab ${open ? 'hidden' : ''} ${dragging ? 'dragging' : ''}`}
        style={pos ? { left: pos.x, top: pos.y, right: 'auto', bottom: 'auto' } : undefined}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onClick={onFabClick}
        title="Drag to move · Click to chat"
        aria-label="Open LUVIA Assistant"
        aria-expanded={open}
      >
        <span className="lc-fab-ring" />
        {Icon.chat}
        <span className="lc-fab-label">Ask LUVIA</span>
        {unread && <span className="lc-fab-dot" />}
      </button>

      <section className={`luvia-chatbot ${open ? 'open' : ''}`} role="dialog" aria-label="LUVIA Assistant" aria-hidden={!open} inert={open ? undefined : ''}>
        <header className="lc-head">
          <div className="lc-mark">✦</div>
          <div className="lc-title">
            <h2>LUVIA Assistant</h2>
            <p><i className={loading ? 'busy' : ''} /> {loading ? 'Thinking…' : 'Online · Grounded in LUVIA data'}</p>
          </div>
          <button className="lc-icon-btn" onClick={resetChat} aria-label="Start new chat" title="New chat">{Icon.reset}</button>
          <button className="lc-icon-btn" onClick={() => setOpen(false)} aria-label="Close assistant" title="Close (Esc)">{Icon.close}</button>
        </header>

        <main className="lc-messages">
          {messages.map((m, i) => (
            <article className={`lc-message ${m.role}`} key={i}>
              <div className="lc-avatar">{m.role === 'user' ? 'You' : '✦'}</div>
              <div className={`lc-bubble ${m.error ? 'lc-error' : ''}`}>
                <div className="lc-text">{m.text}</div>

                {m.data?.records?.length > 0 && (
                  <div className="lc-records">
                    <b>{m.data.count ?? m.data.records.length} record(s)</b>
                    {m.data.records.slice(0, 8).map((r, j) => (
                      <details key={j}>
                        <summary>{r.title || r.event_type || r.name || r.event_name || `Record ${j + 1}`}</summary>
                        <pre>{JSON.stringify(r, null, 2)}</pre>
                      </details>
                    ))}
                  </div>
                )}

                {m.data?.current && (
                  <div className="lc-weather">
                    <strong>{m.data.current.temperature_2m} °C</strong>
                    <span>Feels like {m.data.current.apparent_temperature} °C</span>
                    <span>Humidity {m.data.current.relative_humidity_2m}%</span>
                    <span>Wind {m.data.current.wind_speed_10m} km/h</span>
                  </div>
                )}

                {m.sources?.length > 0 && (
                  <small className="lc-source">
                    Source: {m.sources.join(', ')}
                    {m.data?.checked_at ? ` · Checked ${m.data.checked_at}` : ''}
                  </small>
                )}

                {m.disclaimer && <small className="lc-disclaimer">{m.disclaimer}</small>}
              </div>
            </article>
          ))}

          {loading && (
            <div className="lc-loading">
              <div className="lc-avatar">✦</div>
              <div className="lc-typing"><span /><span /><span /></div>
            </div>
          )}

          {messages.length === 1 && !loading && (
            <div className="lc-starters">
              <p>TRY ASKING</p>
              {starters.map((s, i) => (
                <button key={s} onClick={() => send(s)} style={{ animationDelay: `${0.15 + i * 0.06}s` }}>
                  <span>{s}</span><b>↗</b>
                </button>
              ))}
            </div>
          )}
          <div ref={bottom} />
        </main>

        <form className="lc-compose" onSubmit={e => { e.preventDefault(); send(); }}>
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask about weather, events or warnings…"
            maxLength={1500}
          />
          <button disabled={!input.trim() || loading} aria-label="Send message">{Icon.send}</button>
        </form>

        <footer className="lc-foot">LUVIA can make mistakes. Always follow official weather advisories.</footer>
      </section>
    </>
  );
}

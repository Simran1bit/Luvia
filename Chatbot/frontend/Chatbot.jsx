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

export default function Chatbot() {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: "Hello! I'm LUVIA's Weather Assistant. Ask me about current weather, forecasts, historical events, IMD warnings, or weather safety." }
  ]);
  const [input, setInput] = useState(''); 
  const [loading, setLoading] = useState(false);
  const [session] = useState(() => `luv-${Date.now()}`); 
  const bottom = useRef(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

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
    }
  }

  return (
    <section className="luvia-chatbot">
      <header className="lc-head">
        <div className="lc-mark">✦</div>
        <div>
          <h2>LUVIA Assistant</h2>
          <p>Weather intelligence · Grounded in LUVIA data</p>
        </div>
        <span className="lc-status"><i/> Ready</span>
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
                      <summary>{r.title || r.event_type || r.name || r.event_name || `Record ${j+1}`}</summary>
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
            <span/><span/><span/> <small>Checking LUVIA data…</small>
          </div>
        )}
        <div ref={bottom}/>
      </main>

      {messages.length === 1 && (
        <div className="lc-starters">
          <p>TRY ASKING</p>
          {starters.map(s => (
            <button key={s} onClick={() => send(s)}>
              {s}<span>↗</span>
            </button>
          ))}
        </div>
      )}

      <form className="lc-compose" onSubmit={e => { e.preventDefault(); send(); }}>
        <input 
          value={input} 
          onChange={e => setInput(e.target.value)} 
          placeholder="Ask about weather, events or warnings…" 
          maxLength={1500}
        />
        <button disabled={!input.trim() || loading} aria-label="Send message">➤</button>
      </form>
      
      <footer className="lc-foot">LUVIA can make mistakes. Always follow official weather advisories.</footer>
    </section>
  );
}
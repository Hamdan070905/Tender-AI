import React, { useState } from 'react';

export const TenderAIChat: React.FC<{ tenderId: string }> = ({ tenderId }) => {
  const [messages, setMessages] = useState([
    { sender: 'ai', text: `Hello! I've analyzed tender ${tenderId}. Ask me anything about deliverables, risk factors, or compliance criteria.` }
  ]);
  const [input, setInput] = useState('');

  const sendMessage = () => {
    if (!input.trim()) return;
    const newMsgs = [...messages, { sender: 'user', text: input }];
    setMessages(newMsgs);
    setInput('');
    setTimeout(() => {
      setMessages([...newMsgs, { sender: 'ai', text: 'Based on the extracted vector context, this project requires ISO 9001 compliance and automated batch concrete delivery schedules.' }]);
    }, 1000);
  };

  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', display: 'flex', flexDirection: 'column', height: '400px', padding: '16px' }}>
      <div style={{ fontFamily: 'JetBrains Mono', fontSize: '12px', color: 'var(--accent)', marginBottom: '12px' }}>RAG TENDER CHAT (Groq 70B)</div>
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '12px' }}>
        {messages.map((m, i) => (
          <div key={i} style={{ alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start', background: m.sender === 'user' ? 'var(--accent2)' : 'var(--surface2)', color: 'var(--text)', padding: '10px 14px', borderRadius: '8px', maxWidth: '80%', fontSize: '13px' }}>
            {m.text}
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: '8px' }}>
        <input style={{ flex: 1 }} value={input} onChange={e => setInput(e.target.value)} placeholder="Ask about budget caps, penalties, or specs..." />
        <button onClick={sendMessage} style={{ background: 'var(--accent)', color: 'var(--bg)', border: 'none', padding: '0 16px', borderRadius: '6px', fontWeight: 600 }}>Send</button>
      </div>
    </div>
  );
};
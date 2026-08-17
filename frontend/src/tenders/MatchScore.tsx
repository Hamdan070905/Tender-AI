import React from 'react';

export const MatchScore: React.FC<{ score: number }> = ({ score }) => (
  <div style={{ fontFamily: 'JetBrains Mono', fontSize: '11px', background: 'rgba(0,194,168,0.1)', color: 'var(--accent)', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(0,194,168,0.2)' }}>
    Match: {Math.round(score * 100)}%
  </div>
);

export const TenderCard: React.FC<{ tender: any; onSelect: (t: any) => void }> = ({ tender, onSelect }) => (
  <div onClick={() => onSelect(tender)} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', padding: '20px', cursor: 'pointer', transition: 'border-color 0.2s' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
      <span style={{ fontSize: '10px', fontFamily: 'JetBrains Mono', color: 'var(--accent2)', textTransform: 'uppercase' }}>{tender.source}</span>
      <MatchScore score={tender.match_score} />
    </div>
    <h3 style={{ fontSize: '16px', fontWeight: 600, margin: '0 0 8px 0' }}>{tender.title}</h3>
    <p style={{ fontSize: '13px', color: 'var(--muted)', margin: 0 }}>{tender.summary ? tender.summary.slice(0, 120) + '...' : 'Indexing summary via Groq Llama 3.3...'}</p>
  </div>
);
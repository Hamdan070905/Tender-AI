import React from 'react';

export const PipelineCRM: React.FC = () => {
  const columns = ['Discovered', 'Reviewing', 'Applying', 'Submitted', 'Won'];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px' }}>
      {columns.map((col, idx) => (
        <div key={idx} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', padding: '12px', minHeight: '300px' }}>
          <div style={{ fontFamily: 'JetBrains Mono', fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', marginBottom: '12px' }}>{col}</div>
          <div style={{ background: 'var(--surface2)', padding: '10px', borderRadius: '6px', fontSize: '12px', borderLeft: '3px solid var(--accent)' }}>
            <strong>3D Concrete Printing Pilot</strong>
            <div style={{ color: 'var(--muted)', fontSize: '11px', marginTop: '4px' }}>€450,000 · TED EU</div>
          </div>
        </div>
      ))}
    </div>
  );
};
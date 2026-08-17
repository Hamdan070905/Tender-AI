import React from 'react';

export const AnalyticsDashboard: React.FC = () => (
  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', padding: '20px' }}>
      <div style={{ fontSize: '11px', fontFamily: 'JetBrains Mono', color: 'var(--muted)' }}>SUCCESS RATE</div>
      <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--accent)', marginTop: '8px' }}>68.4%</div>
    </div>
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', padding: '20px' }}>
      <div style={{ fontSize: '11px', fontFamily: 'JetBrains Mono', color: 'var(--muted)' }}>ACTIVE PIPELINE VALUE</div>
      <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--accent2)', marginTop: '8px' }}>€12.4M</div>
    </div>
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', padding: '20px' }}>
      <div style={{ fontSize: '11px', fontFamily: 'JetBrains Mono', color: 'var(--muted)' }}>WIN/LOSS RATIO</div>
      <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--accent3)', marginTop: '8px' }}>3.2 : 1</div>
    </div>
  </div>
);
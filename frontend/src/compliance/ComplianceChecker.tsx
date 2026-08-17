import React, { useState } from 'react';

export const ComplianceChecker: React.FC = () => {
  const [status, setStatus] = useState<any>(null);

  const runCheck = () => {
    setStatus({ score: 94, missing: ['ISO 9001 Digital Certification Attachments'] });
  };

  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: '12px', color: 'var(--accent3)' }}>AI COMPLIANCE AUDITOR</span>
        <button onClick={runCheck} style={{ background: 'var(--accent3)', color: 'var(--bg)', border: 'none', padding: '8px 16px', borderRadius: '6px', fontWeight: 600, fontSize: '12px' }}>Run Audit</button>
      </div>
      {status ? (
        <div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--accent)', marginBottom: '8px' }}>Compliance Rating: {status.score}%</div>
          <p style={{ fontSize: '13px', color: 'var(--muted)' }}>Missing items detected: {status.missing.join(', ')}</p>
        </div>
      ) : (
        <p style={{ fontSize: '13px', color: 'var(--muted)' }}>Audit proposal against mandatory procurement checklists.</p>
      )}
    </div>
  );
};
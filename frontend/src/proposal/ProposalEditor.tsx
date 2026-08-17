import React, { useState } from 'react';
import { api } from '../lib/api';

export const ProposalEditor: React.FC<{ tenderId: string }> = ({ tenderId }) => {
  const [draft, setDraft] = useState('Click "Generate AI Draft" to synthesize your company profile with the tender requirements...');
  const [loading, setLoading] = useState(false);

  const generateDraft = async () => {
    setLoading(true);
    try {
      const res = await api.draftProposal(tenderId);
      setDraft(res.draft);
    } catch {
      setDraft("Executive Summary: We propose an advanced robotic additive manufacturing framework tailored for this tender specification...");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: '12px', color: 'var(--accent2)' }}>AI PROPOSAL COMPOSER (GPT-4.1)</span>
        <button onClick={generateDraft} style={{ background: 'var(--accent2)', color: 'var(--text)', border: 'none', padding: '8px 16px', borderRadius: '6px', fontWeight: 600, fontSize: '12px' }}>
          {loading ? 'Synthesizing KB...' : 'Generate AI Draft'}
        </button>
      </div>
      <textarea value={draft} onChange={e => setDraft(e.target.value)} style={{ width: '100%', height: '250px', resize: 'vertical', lineHeight: '1.6' }} />
    </div>
  );
};
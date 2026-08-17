import React, { useEffect, useState } from 'react';
import { TenderCard } from '../tenders/TenderCard';
import { TenderAIChat } from '../ai-chat/TenderAIChat';
import { ProposalEditor } from '../proposal/ProposalEditor';
import { ComplianceChecker } from '../compliance/ComplianceChecker';
import { PipelineCRM } from '../crm/PipelineCRM';
import { AnalyticsDashboard } from '../analytics/AnalyticsDashboard';
import { api } from '../lib/api';

export const DashboardHome: React.FC = () => {
  const [tenders, setTenders] = useState<any[]>([]);
  const [selectedTender, setSelectedTender] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'tenders' | 'crm' | 'analytics'>('tenders');

  useEffect(() => {
    api.getTenders()
  .then(data => {
    console.log("API Response:", data);

    if (Array.isArray(data)) {
      setTenders(data);
      if (data.length > 0) {
        setSelectedTender(data[0]);
      }
    } else {
      console.error("Expected an array but got:", data);
      setTenders([]);
    }
  })
  .catch(err => {
    console.error(err);
  });
  }, []);

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: 700 }}>Procurement Intelligence</h1>
          <p style={{ color: 'var(--muted)', fontSize: '14px' }}>Autonomous agent tracking for Concrete 3D Printing tenders.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {['tenders', 'crm', 'analytics'].map((tab) => (
            <button key={tab} onClick={() => setActiveTab(tab as any)} style={{ background: activeTab === tab ? 'var(--accent)' : 'var(--surface)', color: activeTab === tab ? 'var(--bg)' : 'var(--text)', border: '1px solid var(--border)', padding: '6px 14px', borderRadius: '6px', fontSize: '12px', textTransform: 'uppercase', fontFamily: 'JetBrains Mono' }}>
              {tab}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'tenders' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          <div>
            <h3 style={{ fontSize: '16px', marginBottom: '12px' }}>Discovered Tenders</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '600px', overflowY: 'auto' }}>
              {tenders.map(t => <TenderCard key={t.id} tender={t} onSelect={setSelectedTender} />)}
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {selectedTender ? (
              <>
                <TenderAIChat tenderId={selectedTender.id} />
                <ProposalEditor tenderId={selectedTender.id} />
                <ComplianceChecker />
              </>
            ) : (
              <p style={{ color: 'var(--muted)' }}>Select a tender to run interactive tools.</p>
            )}
          </div>
        </div>
      )}

      {activeTab === 'crm' && <PipelineCRM />}
      {activeTab === 'analytics' && <AnalyticsDashboard />}
    </div>
  );
};
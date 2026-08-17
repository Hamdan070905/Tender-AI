import React, { useState } from 'react';

export const AuthScreen: React.FC<{ onLogin: () => void }> = ({ onLogin }) => {
  const [isLogin, setIsLogin] = useState(true);
  return (
    <div style={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center', background: 'var(--bg)' }}>
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '40px', borderRadius: '12px', width: '400px' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <span style={{ background: 'var(--tag-bg)', border: '1px solid var(--accent)', color: 'var(--accent)', fontSize: '10px', fontFamily: 'JetBrains Mono', padding: '4px 8px', borderRadius: '4px' }}>SECURE ACCESS</span>
          <h2 style={{ fontSize: '24px', fontWeight: 700, marginTop: '12px' }}>Tender<span style={{ color: 'var(--accent)' }}>AI</span></h2>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <input type="email" placeholder="name@company.com" />
          <input type="password" placeholder="••••••••" />
          <button onClick={onLogin} style={{ background: 'var(--accent)', color: 'var(--bg)', border: 'none', padding: '12px', fontWeight: 600, borderRadius: '6px' }}>
            {isLogin ? 'Sign In' : 'Create Account'}
          </button>
          <p onClick={() => setIsLogin(!isLogin)} style={{ fontSize: '12px', color: 'var(--muted)', textAlign: 'center', cursor: 'pointer' }}>
            {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </p>
        </div>
      </div>
    </div>
  );
};
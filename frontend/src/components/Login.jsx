import { useState } from 'react';
import { login } from '../api';

const DEMO_ACCOUNTS = [
  { label: 'Rescuer',       sub: 'Field rescue team',   username: 'rescuer1',    password: 'password', icon: '🦺', color: '#0d9488' },
  { label: 'Police Admin',  sub: 'Match verification',  username: 'police_admin',password: 'password', icon: '🚔', color: '#1e3a5f' },
  { label: 'Family Member', sub: 'Report missing person',username:'family_user', password: 'password', icon: '👨‍👩‍👦', color: '#ea580c' },
];

export function Login({ onLogin }) {
  const [form, setForm]           = useState({ username: '', password: '' });
  const [error, setError]         = useState('');
  const [loading, setLoading]     = useState(false);
  const [loadingDemo, setLoadingDemo] = useState(null);

  const doLogin = async (username, password, demoIdx = null) => {
    setError('');
    if (demoIdx !== null) {
      setLoadingDemo(demoIdx);
    } else {
      setLoading(true);
    }
    try {
      const data = await login(username, password);
      onLogin(data);
    } catch (err) {
      setError(err.message || 'Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
      setLoadingDemo(null);
    }
  };

  const anyLoading = loading || loadingDemo !== null;

  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(135deg, var(--navy), var(--navy-light))',
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center', 
      padding: '1rem',
      flexDirection: 'column',
      gap: '2rem',
    }}>
      <div style={{ width: '100%', maxWidth: '420px' }}>

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{ 
            width: '60px', 
            height: '60px', 
            background: 'linear-gradient(135deg, var(--teal), var(--teal-light))', 
            borderRadius: '12px', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            fontSize: '1.8rem', 
            margin: '0 auto 1rem',
            boxShadow: 'var(--shadow-md)',
          }}>
            🚨
          </div>
          <h1 style={{ fontSize: 'clamp(1.3rem, 5vw, 1.6rem)', color: 'white', marginBottom: '0.5rem', fontWeight: 700 }}>
            DFR System
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.9)', fontSize: 'clamp(0.85rem, 3vw, 1rem)', fontWeight: 500 }}>
            Disaster Family Reunification
          </p>
        </div>

        {/* Card */}
        <div className="card fade-in" style={{ width: '100%', minHeight: 'auto', padding: 'clamp(1.25rem, 4vw, 2rem)' }}>
          <h2 style={{ marginBottom: '1.5rem', fontSize: 'clamp(1.05rem, 3vw, 1.25rem)' }}>
            Sign in to your account
          </h2>

          {error && (
            <div className="alert alert-error">
              <span>⚠</span> {error}
            </div>
          )}

          {/* Demo quick-login */}
          <p style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '1rem' }}>
            Quick Access — Demo Accounts
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
            {DEMO_ACCOUNTS.map((acc, i) => (
              <button
                key={acc.username}
                onClick={() => doLogin(acc.username, acc.password, i)}
                disabled={anyLoading}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '12px 14px',
                  borderRadius: '8px',
                  cursor: anyLoading ? 'not-allowed' : 'pointer',
                  background: loadingDemo === i ? '#f8fafc' : '#ffffff',
                  border: `1.5px solid ${loadingDemo === i ? acc.color : 'var(--border)'}`,
                  opacity: anyLoading && loadingDemo !== i ? 0.55 : 1,
                  transition: 'all 0.2s ease',
                  textAlign: 'left',
                  width: '100%',
                  minHeight: '56px',
                  boxShadow: 'var(--shadow-xs)',
                }}
                onMouseEnter={e => { 
                  if (!anyLoading) { 
                    e.currentTarget.style.borderColor = acc.color;
                    e.currentTarget.style.background = '#f8fafc';
                    e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                  }
                }}
                onMouseLeave={e => { 
                  e.currentTarget.style.borderColor = loadingDemo === i ? acc.color : 'var(--border)';
                  e.currentTarget.style.background = '#ffffff';
                  e.currentTarget.style.boxShadow = 'var(--shadow-xs)';
                }}
              >
                <div style={{ 
                  width: '40px', 
                  height: '40px', 
                  borderRadius: '8px', 
                  background: `${acc.color}18`, 
                  border: `1px solid ${acc.color}30`, 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  fontSize: '1.2rem', 
                  flexShrink: 0,
                }}>
                  {acc.icon}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--navy)', marginBottom: '2px' }}>
                    {acc.label}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {acc.sub}
                  </div>
                </div>
                <div style={{ fontSize: '0.8rem', color: loadingDemo === i ? acc.color : 'var(--text-muted)', fontWeight: 600, flexShrink: 0 }}>
                  {loadingDemo === i ? 'Signing in…' : '→'}
                </div>
              </button>
            ))}
          </div>

          <div className="divider">or sign in manually</div>

          {/* Manual form */}
          <form onSubmit={(e) => { e.preventDefault(); doLogin(form.username, form.password); }} style={{ width: '100%' }}>
            <div className="input-group">
              <label className="input-label">Username</label>
              <input 
                className="form-input" 
                name="username" 
                value={form.username}
                onChange={e => setForm({ ...form, username: e.target.value })}
                placeholder="Enter username" 
                autoComplete="username" 
                disabled={anyLoading}
              />
            </div>
            <div className="input-group" style={{ marginBottom: '1.5rem' }}>
              <label className="input-label">Password</label>
              <input 
                className="form-input" 
                name="password" 
                type="password" 
                value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })}
                placeholder="Enter password" 
                autoComplete="current-password" 
                disabled={anyLoading} 
              />
            </div>
            <button 
              type="submit" 
              className="btn btn-primary" 
              disabled={anyLoading || !form.username || !form.password}
              style={{ width: '100%', minHeight: '48px', fontSize: '1rem', fontWeight: 700 }}
            >
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>
        </div>

        <p style={{ textAlign: 'center', marginTop: '1.5rem', color: 'rgba(255,255,255,0.9)', fontSize: '0.8rem' }}>
          Demo Password: <strong style={{ color: 'white' }}>password</strong>
        </p>
      </div>
    </div>
  );
}

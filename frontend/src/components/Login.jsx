import { useState } from 'react';
import { login } from '../api';

const DEMO_ACCOUNTS = [
  { label: 'Rescuer',       sub: 'Field rescue team',   username: 'rescuer1',    password: 'password', icon: '🦺', color: '#4f6ef7' },
  { label: 'Police Admin',  sub: 'Match verification',  username: 'police_admin',password: 'password', icon: '🚔', color: '#1e3a5f' },
  { label: 'Family Member', sub: 'Report missing person',username:'family_user', password: 'password', icon: '👨‍👩‍👦', color: '#d97706' },
];

export function Login({ onLogin }) {
  const [form, setForm]           = useState({ username: '', password: '' });
  const [error, setError]         = useState('');
  const [loading, setLoading]     = useState(false);
  const [loadingDemo, setLoadingDemo] = useState(null);

  const doLogin = async (username, password, demoIdx = null) => {
    setError('');
    demoIdx !== null ? setLoadingDemo(demoIdx) : setLoading(true);
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
    <div style={{ minHeight: '100vh', background: '#f4f6f9', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem 1rem' }}>
      <div style={{ width: '100%', maxWidth: '420px' }}>

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{ width: '56px', height: '56px', background: 'linear-gradient(135deg, #1e3a5f, #4f6ef7)', borderRadius: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem', margin: '0 auto 1rem' }}>🚨</div>
          <h1 style={{ fontSize: '1.5rem', color: '#1e3a5f', marginBottom: '4px' }}>DFR System</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.875rem' }}>Disaster Family Reunification Platform</p>
        </div>

        <div className="card fade-in">
          <h2 style={{ marginBottom: '1.25rem', fontSize: '1.05rem' }}>Sign in to your account</h2>

          {error && (
            <div className="alert alert-error">
              <span>⚠</span> {error}
            </div>
          )}

          {/* Demo quick-login */}
          <p style={{ fontSize: '0.72rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px' }}>Quick Access — Demo Accounts</p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '7px', marginBottom: '1.25rem' }}>
            {DEMO_ACCOUNTS.map((acc, i) => (
              <button
                key={acc.username}
                onClick={() => doLogin(acc.username, acc.password, i)}
                disabled={anyLoading}
                style={{
                  display: 'flex', alignItems: 'center', gap: '12px',
                  padding: '10px 14px', borderRadius: '8px', cursor: anyLoading ? 'not-allowed' : 'pointer',
                  background: loadingDemo === i ? '#f8fafc' : '#ffffff',
                  border: `1.5px solid ${loadingDemo === i ? acc.color : '#e2e8f0'}`,
                  opacity: anyLoading && loadingDemo !== i ? 0.55 : 1,
                  transition: 'all 0.12s', textAlign: 'left', width: '100%',
                }}
                onMouseEnter={e => { if (!anyLoading) { e.currentTarget.style.borderColor = acc.color; e.currentTarget.style.background = '#f8fafc'; }}}
                onMouseLeave={e => { e.currentTarget.style.borderColor = loadingDemo === i ? acc.color : '#e2e8f0'; e.currentTarget.style.background = '#ffffff'; }}
              >
                <div style={{ width: '34px', height: '34px', borderRadius: '8px', background: `${acc.color}18`, border: `1px solid ${acc.color}30`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1rem', flexShrink: 0 }}>
                  {acc.icon}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem', color: '#0f172a' }}>{acc.label}</div>
                  <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>{acc.sub}</div>
                </div>
                <div style={{ fontSize: '0.75rem', color: loadingDemo === i ? acc.color : '#cbd5e1', fontWeight: 600 }}>
                  {loadingDemo === i ? 'Signing in…' : '→'}
                </div>
              </button>
            ))}
          </div>

          <div className="divider">or sign in manually</div>

          {/* Manual form */}
          <form onSubmit={(e) => { e.preventDefault(); doLogin(form.username, form.password); }}>
            <div className="input-group">
              <label className="input-label">Username</label>
              <input className="form-input" name="username" value={form.username}
                onChange={e => setForm({ ...form, username: e.target.value })}
                placeholder="Enter username" autoComplete="username" disabled={anyLoading} />
            </div>
            <div className="input-group" style={{ marginBottom: '1.25rem' }}>
              <label className="input-label">Password</label>
              <input className="form-input" name="password" type="password" value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })}
                placeholder="Enter password" autoComplete="current-password" disabled={anyLoading} />
            </div>
            <button type="submit" className="btn btn-primary" disabled={anyLoading || !form.username || !form.password}>
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>
        </div>

        <p style={{ textAlign: 'center', marginTop: '1.5rem', color: '#94a3b8', fontSize: '0.75rem' }}>
          All demo accounts use password: <strong style={{ color: '#475569' }}>password</strong>
        </p>
      </div>
    </div>
  );
}

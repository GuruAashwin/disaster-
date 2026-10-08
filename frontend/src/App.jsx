import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom';
import { isLoggedIn, getRole, getUsername, clearSession } from './api';
import { Login } from './components/Login';
import { AddFoundPerson } from './components/AddFoundPerson';
import { MissingPersonForm } from './components/MissingPersonForm';
import { MatchReview } from './components/MatchReview';

function RequireAuth({ children, allowedRoles }) {
  if (!isLoggedIn()) return <Navigate to="/login" replace />;
  const role = getRole();
  if (allowedRoles && !allowedRoles.includes(role)) return <Navigate to="/" replace />;
  return children;
}

const ROLE_LABEL = { rescuer: 'Rescuer', police: 'Police Admin', admin: 'Admin', public: 'Family' };
const ROLE_COLOR = { rescuer: 'badge-primary', police: 'badge-navy', admin: 'badge-navy', public: 'badge-warning' };

function NavBar({ onLogout }) {
  const role     = getRole();
  const username = getUsername();
  const isPolice = role === 'police' || role === 'admin';
  const isPublic = role === 'public';

  const linkStyle = ({ isActive }) => ({
    textDecoration: 'none',
    fontWeight: 500,
    fontSize: '0.9rem',
    padding: '8px 16px',
    borderRadius: '4px',
    color: isActive ? 'var(--navy)' : 'var(--text-secondary)',
    background: isActive ? 'var(--bg-subtle)' : 'transparent',
    border: isActive ? '1px solid var(--border)' : '1px solid transparent',
    transition: 'all 0.2s ease',
  });

  return (
    <header style={{
      background: 'var(--bg-card)',
      borderBottom: '1px solid var(--border)',
      boxShadow: 'var(--shadow-sm)',
      position: 'sticky', top: 0, zIndex: 50,
    }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '0 1.5rem', height: '58px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexShrink: 0 }}>
          <div style={{ width: '36px', height: '36px', background: 'linear-gradient(135deg, var(--navy), var(--primary))', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem' }}>🚨</div>
          <div>
            <div style={{ fontWeight: 500, fontSize: '1.05rem', color: 'var(--navy)', lineHeight: 1.2 }}>DFR System</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>Family Reunification</div>
          </div>
        </div>

        {/* Nav links */}
        <nav style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
          {(role === 'rescuer' || isPolice) && <NavLink to="/found"   style={linkStyle}>Found Person</NavLink>}
          {(isPublic         || isPolice) && <NavLink to="/missing" style={linkStyle}>Missing Reports</NavLink>}
          {isPolice                        && <NavLink to="/matches" style={linkStyle}>Match Review</NavLink>}
        </nav>

        {/* User */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexShrink: 0 }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text)' }}>{username}</div>
            <div style={{ marginTop: '1px' }}>
              <span className={`badge ${ROLE_COLOR[role] || 'badge-neutral'}`}>{ROLE_LABEL[role] || role}</span>
            </div>
          </div>
          <button className="btn btn-ghost" onClick={onLogout} style={{ flexShrink: 0 }}>
            Sign Out
          </button>
        </div>
      </div>
    </header>
  );
}

function Shell({ onLogout, children }) {
  return (
    <>
      <NavBar onLogout={onLogout} />
      <main style={{ maxWidth: '1400px', margin: '0 auto', padding: '2rem 1.5rem' }}>
        {children}
      </main>
    </>
  );
}

function AppRoutes() {
  const [authed, setAuthed] = useState(isLoggedIn());
  const navigate = useNavigate();

  const handleLogin = (data) => {
    setAuthed(true);
    const r = data.role;
    if (r === 'police' || r === 'admin') navigate('/matches');
    else if (r === 'public') navigate('/missing');
    else navigate('/found');
  };

  const handleLogout = () => { clearSession(); setAuthed(false); navigate('/login'); };

  useEffect(() => { if (!authed) navigate('/login'); }, [authed, navigate]);

  return (
    <Routes>
      <Route path="/login" element={authed ? <Navigate to="/found" replace /> : <Login onLogin={handleLogin} />} />

      <Route path="/found" element={
        <RequireAuth allowedRoles={['rescuer', 'police', 'admin']}>
          <Shell onLogout={handleLogout}><AddFoundPerson /></Shell>
        </RequireAuth>
      } />

      <Route path="/missing" element={
        <RequireAuth allowedRoles={['public', 'police', 'admin']}>
          <Shell onLogout={handleLogout}><MissingPersonForm /></Shell>
        </RequireAuth>
      } />

      <Route path="/matches" element={
        <RequireAuth allowedRoles={['police', 'admin']}>
          <Shell onLogout={handleLogout}><MatchReview /></Shell>
        </RequireAuth>
      } />

      <Route path="*" element={
        !authed ? <Navigate to="/login" replace /> :
        <Navigate to={getRole() === 'public' ? '/missing' : getRole() === 'police' || getRole() === 'admin' ? '/matches' : '/found'} replace />
      } />
    </Routes>
  );
}

export default function App() {
  return <BrowserRouter><AppRoutes /></BrowserRouter>;
}

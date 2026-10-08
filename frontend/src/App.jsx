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
    fontSize: '0.875rem',
    padding: '6px 14px',
    borderRadius: '6px',
    color: isActive ? '#1e3a5f' : '#475569',
    background: isActive ? '#eef1fe' : 'transparent',
    border: isActive ? '1px solid #c7d2fe' : '1px solid transparent',
    transition: 'all 0.12s',
  });

  return (
    <header style={{
      background: '#ffffff',
      borderBottom: '1px solid #e2e8f0',
      boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      position: 'sticky', top: 0, zIndex: 50,
    }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '0 1.5rem', height: '58px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
          <div style={{ width: '32px', height: '32px', background: 'linear-gradient(135deg, #1e3a5f, #4f6ef7)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1rem' }}>🚨</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#1e3a5f', lineHeight: 1.1 }}>DFR System</div>
            <div style={{ fontSize: '0.65rem', color: '#94a3b8', letterSpacing: '0.04em', textTransform: 'uppercase' }}>Family Reunification</div>
          </div>
        </div>

        {/* Nav links */}
        <nav style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
          {(role === 'rescuer' || isPolice) && <NavLink to="/found"   style={linkStyle}>Found Person</NavLink>}
          {(isPublic         || isPolice) && <NavLink to="/missing" style={linkStyle}>Missing Reports</NavLink>}
          {isPolice                        && <NavLink to="/matches" style={linkStyle}>Match Review</NavLink>}
        </nav>

        {/* User */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#0f172a' }}>{username}</div>
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
        <RequireAuth>
          <Shell onLogout={handleLogout}><AddFoundPerson /></Shell>
        </RequireAuth>
      } />

      <Route path="/missing" element={
        <RequireAuth>
          <Shell onLogout={handleLogout}><MissingPersonForm /></Shell>
        </RequireAuth>
      } />

      <Route path="/matches" element={
        <RequireAuth allowedRoles={['police', 'admin']}>
          <Shell onLogout={handleLogout}><MatchReview /></Shell>
        </RequireAuth>
      } />

      <Route path="*" element={<Navigate to={authed ? '/found' : '/login'} replace />} />
    </Routes>
  );
}

export default function App() {
  return <BrowserRouter><AppRoutes /></BrowserRouter>;
}

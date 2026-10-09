import { useState, useEffect, useCallback } from 'react';
import { listMatches, verifyMatch, rejectMatch, runMatching } from '../api';
import { PersonsTable } from './PersonsTable';
import { PhotoComparison } from './PhotoComparison';

const STATE_CFG = {
  under_review: { label: 'Under Review', cls: 'badge-warning' },
  verified:     { label: 'Verified',     cls: 'badge-success' },
  rejected:     { label: 'Rejected',     cls: 'badge-danger'  },
};

function ScorePill({ score }) {
  const pct   = Math.round(score * 100);
  const cls   = pct >= 80 ? 'badge-success' : pct >= 55 ? 'badge-warning' : 'badge-neutral';
  return <span className={`badge ${cls}`}>{pct}% match</span>;
}

function MatchCard({ match, onVerify, onReject, busy }) {
  const [expanded, setExpanded] = useState(false);
  const reasons  = match.reasons?.reasons  || [];
  const cfg      = STATE_CFG[match.state] || { label: match.state, cls: 'badge-neutral' };

  return (
    <div style={{ border: '1px solid #e2e8f0', borderRadius: '10px', overflow: 'hidden', background: '#fff' }}>
      {/* Card top */}
      <div style={{ padding: '14px 16px', background: '#fafbfc', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <ScorePill score={match.score} />
          {match.photo_confidence > 0 && (
            <span className="badge badge-primary" style={{ fontSize: '0.7rem' }}>
              📸 {Math.round(match.photo_confidence)}% photo match
            </span>
          )}
          <span className={`badge ${cfg.cls}`}>{cfg.label}</span>
          <span style={{ fontSize: '0.7rem', color: '#94a3b8', fontWeight: 500 }}>{match.model_version}</span>
        </div>
        <button onClick={() => setExpanded(!expanded)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.75rem', color: '#4f6ef7', fontWeight: 600, padding: '2px 6px' }}>
          {expanded ? '▲ Less' : '▼ Details'}
        </button>
      </div>

      {/* Names */}
      <div style={{ padding: '14px 16px', display: 'grid', gridTemplateColumns: '1fr 36px 1fr', alignItems: 'center', gap: '10px' }}>
        <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '10px 12px' }}>
          <div style={{ fontSize: '0.65rem', fontWeight: 700, color: '#059669', letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: '4px' }}>Found</div>
          <div style={{ fontWeight: 600, color: '#0f172a', fontSize: '0.9rem' }}>{match.found_name || '(unknown)'}</div>
        </div>
        <div style={{ textAlign: 'center', color: '#94a3b8', fontSize: '1rem', fontWeight: 300 }}>↔</div>
        <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '8px', padding: '10px 12px' }}>
          <div style={{ fontSize: '0.65rem', fontWeight: 700, color: '#d97706', letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: '4px' }}>Missing</div>
          <div style={{ fontWeight: 600, color: '#0f172a', fontSize: '0.9rem' }}>{match.missing_name || '(unknown)'}</div>
        </div>
      </div>

      {/* Reason chips */}
      {reasons.length > 0 && (
        <div style={{ padding: '0 16px 12px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {reasons.map((r, i) => <span key={i} className="badge badge-primary" style={{ fontSize: '0.7rem' }}>{r}</span>)}
        </div>
      )}

      {/* Photo Comparison */}
      {(match.found_photos?.length > 0 || match.missing_photos?.length > 0) && expanded && (
        <div style={{ margin: '12px 16px 0', padding: '16px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
          <PhotoComparison
            foundPhotos={match.found_photos || []}
            missingPhotos={match.missing_photos || []}
            photoConfidence={match.photo_confidence || 0}
          />
        </div>
      )}

      {/* Individual Information */}
      {expanded && (
        <div style={{ margin: '12px 16px 0', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px', display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
          
          <div style={{ flex: 1, minWidth: '250px' }}>
            <h4 style={{ margin: '0 0 12px 0', fontSize: '0.8rem', color: '#059669', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Found Person Details</h4>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
              <tbody>
                {match.found_person && Object.entries(match.found_person).filter(([k,v]) => v && k !== 'name').map(([k, v]) => (
                  <tr key={k} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '6px 12px 6px 0', color: '#64748b', fontWeight: 600, textTransform: 'capitalize', width: '35%' }}>{k.replace('_', ' ')}</td>
                    <td style={{ padding: '6px 0', color: '#334155' }}>{Array.isArray(v) ? v.join(', ') : String(v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ width: '1px', background: '#e2e8f0' }}></div>

          <div style={{ flex: 1, minWidth: '250px' }}>
            <h4 style={{ margin: '0 0 12px 0', fontSize: '0.8rem', color: '#d97706', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Missing Person Details</h4>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
              <tbody>
                {match.missing_person && Object.entries(match.missing_person).filter(([k,v]) => v && k !== 'name').map(([k, v]) => (
                  <tr key={k} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '6px 12px 6px 0', color: '#64748b', fontWeight: 600, textTransform: 'capitalize', width: '35%' }}>{k.replace('_', ' ')}</td>
                    <td style={{ padding: '6px 0', color: '#334155' }}>{Array.isArray(v) ? v.join(', ') : String(v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

        </div>
      )}

      {/* Actions */}
      {match.state === 'under_review' && (
        <div style={{ padding: '12px 16px', borderTop: '1px solid #f1f5f9', display: 'flex', gap: '8px' }}>
          <button className="btn btn-primary" style={{ flex: 1, padding: '8px' }} onClick={() => onVerify(match.id)} disabled={busy}>
            {busy ? '…' : '✓ Verify Match'}
          </button>
          <button className="btn btn-danger-outline" onClick={() => onReject(match.id)} disabled={busy}>
            {busy ? '…' : '✗ Reject'}
          </button>
        </div>
      )}
    </div>
  );
}

export function MatchReview() {
  const [matches, setMatches]           = useState([]);
  const [filter, setFilter]             = useState('under_review');
  const [loading, setLoading]           = useState(false);
  const [runningMatch, setRunningMatch] = useState(false);
  const [actionId, setActionId]         = useState(null);
  const [error, setError]               = useState('');
  const [toast, setToast]               = useState('');
  const [tableRefresh, setTableRefresh] = useState(0);

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(''), 3500); };

  const fetchMatches = useCallback(async () => {
    setLoading(true); setError('');
    try { setMatches(await listMatches({ state: filter || undefined, minScore: 0.3 })); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { fetchMatches(); }, [fetchMatches]);

  const handleVerify = async (id) => {
    setActionId(id);
    try { await verifyMatch(id); showToast('Match verified and recorded.'); fetchMatches(); }
    catch (err) { setError(err.message); }
    finally { setActionId(null); }
  };

  const handleReject = async (id) => {
    setActionId(id);
    try { await rejectMatch(id); showToast('Match rejected.'); fetchMatches(); }
    catch (err) { setError(err.message); }
    finally { setActionId(null); }
  };

  const handleRunMatching = async () => {
    setRunningMatch(true);
    try {
      const res = await runMatching();
      showToast(`Matching complete — ${res.new_matches_created} new candidates generated.`);
      fetchMatches(); setTableRefresh(t => t + 1);
    } catch (err) { setError(err.message); }
    finally { setRunningMatch(false); }
  };

  const FILTERS = [
    { val: 'under_review', label: 'Under Review' },
    { val: 'verified',     label: 'Verified' },
    { val: 'rejected',     label: 'Rejected' },
    { val: '',             label: 'All' },
  ];

  return (
    <div className="grid-3col" style={{ alignItems: 'start' }}>

      {/* Col 1 — Found persons */}
      <PersonsTable type="found"   title="Found Persons"    accentColor="#059669" refreshTrigger={tableRefresh} />

      {/* Col 2 — Missing reports */}
      <PersonsTable type="missing" title="Missing Reports"  accentColor="#d97706" refreshTrigger={tableRefresh} />

      {/* Col 3 — Match review */}
      <div className="card fade-in" style={{ padding: 0, overflow: 'hidden' }}>

        {/* Panel header */}
        <div style={{ padding: '16px 20px', background: '#fafbfc', borderBottom: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h2 style={{ marginBottom: '2px' }}>Match Review</h2>
            <p style={{ color: '#94a3b8', fontSize: '0.78rem' }}>Confirm or reject AI-generated candidate matches</p>
          </div>
          <button className="btn btn-accent" style={{ width: 'auto', padding: '8px 18px', fontSize: '0.85rem' }} onClick={handleRunMatching} disabled={runningMatch}>
            {runningMatch ? 'Running…' : '⚡ Run Matching'}
          </button>
        </div>

        <div style={{ padding: '16px 20px' }}>
          {/* Alerts */}
          {toast && <div className="alert alert-success">✓ {toast}</div>}
          {error && <div className="alert alert-error">⚠ {error}</div>}

          {/* Filter tabs */}
          <div style={{ display: 'flex', gap: '6px', marginBottom: '1.1rem', flexWrap: 'wrap' }}>
            {FILTERS.map(({ val, label }) => (
              <button
                key={val || 'all'}
                onClick={() => setFilter(val)}
                style={{
                  padding: '5px 14px', borderRadius: '6px', cursor: 'pointer',
                  border: `1.5px solid ${filter === val ? '#4f6ef7' : '#e2e8f0'}`,
                  background: filter === val ? '#eef1fe' : '#ffffff',
                  color: filter === val ? '#4f6ef7' : '#475569',
                  fontSize: '0.8rem', fontWeight: 600, transition: 'all 0.12s',
                }}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Match cards */}
          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>⏳</div>
              <div style={{ fontSize: '0.85rem' }}>Loading matches…</div>
            </div>
          ) : matches.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>🔍</div>
              <div style={{ fontSize: '0.85rem' }}>No matches for this filter</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {matches.map((m) => (
                <MatchCard key={m.id} match={m} onVerify={handleVerify} onReject={handleReject} busy={actionId === m.id} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

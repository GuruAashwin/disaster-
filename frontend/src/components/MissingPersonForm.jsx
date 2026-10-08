import { useState, useEffect, useCallback } from 'react';
import { submitMissingPerson } from '../api';
import { db } from '../db';
import { PersonsTable } from './PersonsTable';

// Flush all pending missing-person records from IndexedDB to the backend.
// Mirrors the same pattern used in AddFoundPerson.
async function flushOfflineQueue() {
  const pending = await db.offlineQueue.where('status').equals('pending').toArray();
  for (const item of pending) {
    // Only flush records that belong to this form
    if (item.data?._type !== 'missing') continue;
    try {
      const payload = { ...item.data };
      delete payload._type;
      await submitMissingPerson(payload);
      await db.offlineQueue.update(item.id, { status: 'synced' });
    } catch (err) {
      console.warn('Sync failed', item.record_id, err.message);
    }
  }
}

export function MissingPersonForm() {
  const [form, setForm]     = useState({ name: '', age: '', gender: 'Unknown', location: '', descriptors: '' });
  const [submitting, setSubmitting] = useState(false);
  const [isOffline, setIsOffline]   = useState(!navigator.onLine);
  const [isSyncing, setIsSyncing]   = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [result, setResult]         = useState(null);
  const [error, setError]           = useState('');
  const [refresh, setRefresh]       = useState(0);

  const refreshPending = useCallback(async () => {
    // Count only this form's pending records
    const all = await db.offlineQueue.where('status').equals('pending').toArray();
    setPendingCount(all.filter(r => r.data?._type === 'missing').length);
  }, []);

  const handleOnline = useCallback(async () => {
    setIsOffline(false);
    setIsSyncing(true);
    await flushOfflineQueue();
    await refreshPending();
    setIsSyncing(false);
    setRefresh(t => t + 1);
  }, [refreshPending]);

  useEffect(() => {
    refreshPending();
    const off = () => setIsOffline(true);
    window.addEventListener('online',  handleOnline);
    window.addEventListener('offline', off);
    return () => {
      window.removeEventListener('online',  handleOnline);
      window.removeEventListener('offline', off);
    };
  }, [handleOnline, refreshPending]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true); setError(''); setResult(null);
    const payload = { name: form.name, age_raw: form.age, gender: form.gender, location: form.location, descriptors: form.descriptors };
    try {
      if (isOffline) {
        await db.offlineQueue.add({ record_id: crypto.randomUUID(), data: { ...payload, _type: 'missing' }, status: 'pending', timestamp: Date.now() });
        await refreshPending();
        setResult('Saved offline — will sync when connected.');
      } else {
        const res = await submitMissingPerson(payload);
        setResult(`Report submitted successfully (ID: ${res.id.slice(0, 8)}…)`);
        setRefresh(t => t + 1);
      }
      setForm({ name: '', age: '', gender: 'Unknown', location: '', descriptors: '' });
    } catch (err) {
      setError(err.message || 'Submission failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const syncStatus = isSyncing ? 'sync-syncing' : isOffline ? 'sync-offline' : 'sync-online';
  const syncLabel  = isSyncing ? 'Syncing…'    : isOffline ? 'Offline'      : 'Online';

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '20px', alignItems: 'start' }}>

      {/* Left — history */}
      <PersonsTable type="missing" title="Missing Person Reports" accentColor="#d97706" refreshTrigger={refresh} />

      {/* Right — form */}
      <div className="card fade-in">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem', paddingBottom: '1rem', borderBottom: '1px solid #f1f5f9' }}>
          <div>
            <h2>File a Missing Person Report</h2>
            <p style={{ color: '#94a3b8', fontSize: '0.8rem', marginTop: '3px' }}>Provide details to help locate your family member</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {pendingCount > 0 && <span className="badge badge-warning">{pendingCount} pending</span>}
            <div className={`sync-badge ${syncStatus}`}><div className="sync-dot" />{syncLabel}</div>
          </div>
        </div>

        {result && <div className="alert alert-success">✓ {result}</div>}
        {error   && <div className="alert alert-error">⚠ {error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label className="input-label">Full Name <span style={{ color: '#dc2626' }}>*</span></label>
            <input className="form-input" name="name" value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="e.g. Arun Kumar" required />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="input-group">
              <label className="input-label">Age</label>
              <input className="form-input" name="age" value={form.age} onChange={e => setForm({...form, age: e.target.value})} placeholder="e.g. 40 or 35–45" />
            </div>
            <div className="input-group">
              <label className="input-label">Gender</label>
              <select className="form-input" name="gender" value={form.gender} onChange={e => setForm({...form, gender: e.target.value})}>
                <option>Unknown</option><option>Male</option><option>Female</option>
              </select>
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">Last Known Location <span style={{ color: '#dc2626' }}>*</span></label>
            <input className="form-input" name="location" value={form.location} onChange={e => setForm({...form, location: e.target.value})} placeholder="e.g. Velachery, Chennai" required />
          </div>

          <div className="input-group">
            <label className="input-label">Physical Description</label>
            <input className="form-input" name="descriptors" value={form.descriptors} onChange={e => setForm({...form, descriptors: e.target.value})} placeholder="e.g. blue shirt, 5ft 6in, scar on left cheek" />
          </div>

          <button type="submit" className="btn btn-accent" disabled={submitting} style={{ marginTop: '0.5rem' }}>
            {submitting ? 'Submitting…' : 'Submit Report'}
          </button>
        </form>
      </div>
    </div>
  );
}

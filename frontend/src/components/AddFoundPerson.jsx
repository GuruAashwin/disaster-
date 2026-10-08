import { useState, useEffect, useCallback } from 'react';
import { db } from '../db';
import { submitFoundPerson } from '../api';
import { PersonsTable } from './PersonsTable';
import { ImageUploadZone } from './ImageUploadZone';

async function flushOfflineQueue() {
  const pending = await db.offlineQueue.where('status').equals('pending').toArray();
  for (const item of pending) {
    try {
      const payload = { ...item.data };
      delete payload._type;
      await submitFoundPerson(payload);
      await db.offlineQueue.update(item.id, { status: 'synced' });
    } catch (err) {
      console.warn('Sync failed', item.record_id, err.message);
    }
  }
}

export function AddFoundPerson() {
  const [form, setForm]       = useState({ name: '', age: '', gender: 'Unknown', location: '', condition: '' });
  const [imageFile, setImageFile] = useState(null);
  const [submitting, setSubmitting]   = useState(false);
  const [isOffline, setIsOffline]     = useState(!navigator.onLine);
  const [isSyncing, setIsSyncing]     = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [result, setResult]           = useState(null);
  const [error, setError]             = useState('');
  const [refresh, setRefresh]         = useState(0);

  const refreshPending = useCallback(async () => {
    setPendingCount(await db.offlineQueue.where('status').equals('pending').count());
  }, []);

  const handleOnline = useCallback(async () => {
    setIsOffline(false); setIsSyncing(true);
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
    return () => { window.removeEventListener('online', handleOnline); window.removeEventListener('offline', off); };
  }, [handleOnline, refreshPending]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true); setError(''); setResult(null);
    const payload = { name: form.name, age_raw: form.age, gender: form.gender, location: form.location, condition: form.condition };
    try {
      if (isOffline) {
        // For offline, we can't store the image in IndexedDB efficiently
        if (imageFile) {
          setError('Cannot upload images while offline. Please try again when online.');
          setSubmitting(false);
          return;
        }
        await db.offlineQueue.add({ record_id: crypto.randomUUID(), data: { ...payload, _type: 'found' }, status: 'pending', timestamp: Date.now() });
        await refreshPending();
        setResult('Saved offline — will sync when connected.');
      } else {
        const res = await submitFoundPerson(payload, imageFile);
        setResult(`Record submitted successfully (ID: ${res.id.slice(0, 8)}…)`);
        setRefresh(t => t + 1);
      }
      setForm({ name: '', age: '', gender: 'Unknown', location: '', condition: '' });
      setImageFile(null);
    } catch (err) {
      setError(err.message || 'Submission failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const syncStatus = isSyncing ? 'sync-syncing' : isOffline ? 'sync-offline' : 'sync-online';
  const syncLabel  = isSyncing ? 'Syncing…' : isOffline ? 'Offline' : 'Online';

  return (
    <div className="grid-2col" style={{ alignItems: 'start' }}>

      {/* Left — history */}
      <PersonsTable type="found" title="Found Persons Log" accentColor="#059669" refreshTrigger={refresh} />

      {/* Right — form */}
      <div className="card fade-in">
        {/* Card header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem', paddingBottom: '1rem', borderBottom: '1px solid #f1f5f9' }}>
          <div>
            <h2>Report Found Person</h2>
            <p style={{ color: '#94a3b8', fontSize: '0.8rem', marginTop: '3px' }}>Record details of a rescued individual</p>
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
            <label className="input-label">Full Name</label>
            <input className="form-input" name="name" value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="Leave blank if unknown" />
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
            <label className="input-label">Location Found <span style={{ color: '#dc2626' }}>*</span></label>
            <input className="form-input" name="location" value={form.location} onChange={e => setForm({...form, location: e.target.value})} placeholder="e.g. Velachery Bus Stand, Chennai" required />
          </div>

          <div className="input-group">
            <label className="input-label">Medical Condition</label>
            <input className="form-input" name="condition" value={form.condition} onChange={e => setForm({...form, condition: e.target.value})} placeholder="e.g. stable, minor injuries, unconscious" />
          </div>

          <ImageUploadZone onImageSelected={setImageFile} maxSizeMB={5} />

          <button type="submit" className="btn btn-primary" disabled={submitting} style={{ marginTop: '0.5rem' }}>
            {submitting ? 'Submitting…' : 'Submit Record'}
          </button>
        </form>
      </div>
    </div>
  );
}

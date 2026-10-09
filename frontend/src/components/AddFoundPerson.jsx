import { useState, useEffect, useCallback } from 'react';
import { db } from '../db';
import { submitFoundPerson, uploadPersonPhotos } from '../api';
import { PersonsTable } from './PersonsTable';
import { PhotoGallery } from './PhotoGallery';

async function flushOfflineQueue() {
  try {
    const pending = await db.offlineQueue.where('status').equals('pending').toArray();
    for (const item of pending) {
      if (item.data?._type !== 'found') continue;
      try {
        const payload = { ...item.data };
        delete payload._type;
        await submitFoundPerson(payload);
        await db.offlineQueue.update(item.id, { status: 'synced' });
      } catch (err) {
        console.warn('Sync failed', item.record_id, err.message);
      }
    }
  } catch (err) {
    console.warn('Offline queue read failed:', err.message);
  }
}

export function AddFoundPerson() {
  const [form, setForm] = useState({ name: '', age: '', gender: 'Unknown', location: '', condition: '' });
  const [photoFiles, setPhotoFiles] = useState([]);
  const [photoFilenames, setPhotoFilenames] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [isSyncing, setIsSyncing] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);

  const refreshPending = useCallback(async () => {
    try {
      const count = await db.offlineQueue.where('status').equals('pending').count();
      setPendingCount(count);
    } catch (err) {
      console.warn('refreshPending failed:', err.message);
    }
  }, []);

  useEffect(() => {
    refreshPending();
    
    const handleOnline = async () => {
      setIsOffline(false); 
      setIsSyncing(true);
      await flushOfflineQueue();
      await refreshPending();
      setIsSyncing(false);
      setRefresh(t => t + 1);
    };

    const handleOffline = () => setIsOffline(true);
    
    window.addEventListener('online',  handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => { 
      window.removeEventListener('online', handleOnline); 
      window.removeEventListener('offline', handleOffline); 
    };
  }, [refreshPending]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true); 
    setError(''); 
    setResult(null);

    if (!form.location.trim()) {
      setError('Location is required');
      setSubmitting(false);
      return;
    }

    const payload = { 
      name: form.name, 
      age_raw: form.age, 
      gender: form.gender, 
      location: form.location, 
      condition: form.condition 
    };

    try {
      if (isOffline) {
        if (photoFiles.length > 0) {
          setError('Cannot upload photos while offline. Please try again when online.');
          setSubmitting(false);
          return;
        }
        await db.offlineQueue.add({ 
          record_id: crypto.randomUUID(), 
          data: { ...payload, _type: 'found' }, 
          status: 'pending', 
          timestamp: Date.now() 
        });
        await refreshPending();
        setResult('Saved offline — will sync when connected.');
      } else {
        // Submit person data first (without photos in initial submission)
        const res = await submitFoundPerson(payload, null);
        
        // If photos are pending, upload them after person creation
        if (photoFiles.length > 0) {
          try {
            await uploadPersonPhotos(res.id, photoFiles);
          } catch (photoErr) {
            console.warn('Photo upload failed but person was saved:', photoErr);
            setResult(`Record submitted (ID: ${res.id.slice(0, 8)}…) - Photo upload failed, try uploading from log`);
          }
        }
        
        setResult(`✅ Record submitted successfully (ID: ${res.id.slice(0, 8)}…) with ${photoFiles.length} photos`);
        setRefresh(t => t + 1);
      }

      // Reset form
      setForm({ name: '', age: '', gender: 'Unknown', location: '', condition: '' });
      setPhotoFiles([]);
      setPhotoFilenames([]);
      setShowPhotosBeforeSubmit(false);
    } catch (err) {
      setError(err.message || 'Submission failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const syncStatus = isSyncing ? 'sync-syncing' : isOffline ? 'sync-offline' : 'sync-online';
  const syncLabel = isSyncing ? 'Syncing…' : isOffline ? 'Offline' : 'Online';

  return (
    <div className="grid-2col" style={{ alignItems: 'start' }}>

      {/* Left — history */}
      <PersonsTable type="found" title="Found Persons Log" accentColor="#059669" refreshTrigger={refresh} showPhotoUpload={true} />

      {/* Right — form */}
      <div className="card fade-in">
        {/* Card header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem', paddingBottom: '1rem', borderBottom: '1px solid #f1f5f9' }}>
          <div>
            <h2>Report Found Person</h2>
            <p style={{ color: '#94a3b8', fontSize: '0.8rem', marginTop: '3px' }}>Record details of a rescued individual with evidence photos</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {pendingCount > 0 && <span className="badge badge-warning">{pendingCount} pending</span>}
            <div className={`sync-badge ${syncStatus}`}><div className="sync-dot" />{syncLabel}</div>
          </div>
        </div>

        {result && <div className="alert alert-success">✓ {result}</div>}
        {error   && <div className="alert alert-error">⚠ {error}</div>}

        <form onSubmit={handleSubmit}>
          {/* Step indicator */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            marginBottom: '1.5rem',
            paddingBottom: '1rem',
            borderBottom: '1px solid #e2e8f0'
          }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '8px',
              color: '#059669',
              fontWeight: 600,
              fontSize: '0.9rem'
            }}>
              <span style={{ 
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                background: '#059669',
                color: 'white',
                fontWeight: 700,
              }}>1</span>
              Person Details
            </div>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '8px',
              color: photoFiles.length > 0 ? '#059669' : '#94a3b8',
              fontWeight: 600,
              fontSize: '0.9rem'
            }}>
              <span style={{ 
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                background: photoFiles.length > 0 ? '#059669' : '#e2e8f0',
                color: photoFiles.length > 0 ? 'white' : '#64748b',
                fontWeight: 700,
              }}>2</span>
              Evidence Photos ({photoFiles.length})
            </div>
          </div>

          {/* Person details */}
          <div className="input-group">
            <label className="input-label">Full Name</label>
            <input 
              className="form-input" 
              name="name" 
              value={form.name} 
              onChange={e => setForm({...form, name: e.target.value})} 
              placeholder="Leave blank if unknown" 
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="input-group">
              <label className="input-label">Age</label>
              <input 
                className="form-input" 
                name="age" 
                value={form.age} 
                onChange={e => setForm({...form, age: e.target.value})} 
                placeholder="e.g. 40 or 35–45" 
              />
            </div>
            <div className="input-group">
              <label className="input-label">Gender</label>
              <select 
                className="form-input" 
                name="gender" 
                value={form.gender} 
                onChange={e => setForm({...form, gender: e.target.value})}
              >
                <option>Unknown</option>
                <option>Male</option>
                <option>Female</option>
              </select>
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">Location Found <span style={{ color: '#dc2626' }}>*</span></label>
            <input 
              className="form-input" 
              name="location" 
              value={form.location} 
              onChange={e => setForm({...form, location: e.target.value})} 
              placeholder="e.g. Velachery Bus Stand, Chennai" 
              required 
            />
          </div>

          <div className="input-group">
            <label className="input-label">Medical Condition</label>
            <input 
              className="form-input" 
              name="condition" 
              value={form.condition} 
              onChange={e => setForm({...form, condition: e.target.value})} 
              placeholder="e.g. stable, minor injuries, unconscious" 
            />
          </div>

          {/* Photo collection section */}
          <div style={{
            marginTop: '1.5rem',
            padding: '1rem',
            background: '#f0fdf4',
            border: '1px solid #bbf7d0',
            borderRadius: 'var(--radius)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1rem' }}>
              <span style={{ fontSize: '1.2rem' }}>📸</span>
              <div>
                <div style={{ fontWeight: 700, color: '#059669' }}>Collect Evidence Photos</div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Upload multiple photos before submitting ({photoFiles.length} selected)</div>
              </div>
            </div>

            <PhotoGallery 
              personId={null}
              photos={photoFilenames}
              onPhotosSelected={(files) => setPhotoFiles(files)}
              isDisabled={isOffline}
              showLocalPreview={true}
            />
          </div>

          {/* Photo preview grid (before submit) */}
          {photoFiles.length > 0 && (
            <div style={{
              marginTop: '1rem',
              padding: '1rem',
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: 'var(--radius)',
            }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#1e3a5f', marginBottom: '0.75rem' }}>
                Selected Photos ({photoFiles.length})
              </div>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(80px, 1fr))',
                gap: '0.5rem',
              }}>
                {photoFiles.map((file, idx) => (
                  <div
                    key={idx}
                    style={{
                      position: 'relative',
                      aspectRatio: '1',
                      borderRadius: '6px',
                      overflow: 'hidden',
                      border: '2px solid var(--teal)',
                      background: '#fff',
                    }}
                  >
                    <img
                      src={URL.createObjectURL(file)}
                      alt={`Photo ${idx + 1}`}
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                      }}
                    />
                    <div style={{
                      position: 'absolute',
                      top: '2px',
                      right: '2px',
                      background: 'rgba(0,0,0,0.6)',
                      color: 'white',
                      borderRadius: '3px',
                      padding: '2px 5px',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                    }}>
                      {idx + 1}
                    </div>
                  </div>
                ))}
              </div>
              <div style={{
                marginTop: '0.75rem',
                fontSize: '0.8rem',
                color: '#059669',
                fontWeight: 600,
              }}>
                ✓ {(photoFiles.reduce((sum, f) => sum + f.size, 0) / (1024 * 1024)).toFixed(2)} MB total
              </div>
            </div>
          )}

          {/* Submit button */}
          <button 
            type="submit" 
            className="btn btn-primary" 
            disabled={submitting || !form.location.trim()} 
            style={{ marginTop: '1.5rem', width: '100%' }}
          >
            {submitting ? '⏳ Submitting…' : `📤 Submit Record${photoFiles.length > 0 ? ` with ${photoFiles.length} Photo${photoFiles.length !== 1 ? 's' : ''}` : ''}`}
          </button>
        </form>
      </div>
    </div>
  );
}

import Dexie from 'dexie';

export const db = new Dexie('DisasterReunificationDB');

db.version(1).stores({
  offlineQueue: '++id, record_id, data, status, timestamp' // status: 'pending', 'synced'
});

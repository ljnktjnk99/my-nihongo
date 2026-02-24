/**
 * IndexedDB wrapper for NihonGo Meeting PWA
 * Stores vocabulary, progress, and SRS data locally on device
 */
const DB_NAME = 'nihongo_meeting';
const DB_VERSION = 1;

class NihongoDB {
  constructor() {
    this.db = null;
  }

  async open() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onerror = () => reject(req.error);
      req.onsuccess = () => { this.db = req.result; resolve(this.db); };
      req.onupgradeneeded = (e) => {
        const db = e.target.result;

        // Meetings metadata
        if (!db.objectStoreNames.contains('meetings')) {
          db.createObjectStore('meetings', { keyPath: 'id' });
        }

        // All vocabulary/phrases/grammar items
        if (!db.objectStoreNames.contains('items')) {
          const store = db.createObjectStore('items', { keyPath: 'id' });
          store.createIndex('meeting', 'meeting_id', { unique: false });
          store.createIndex('type', 'type', { unique: false });
          store.createIndex('status', 'status', { unique: false });
        }

        // SRS progress for each item
        if (!db.objectStoreNames.contains('srs')) {
          db.createObjectStore('srs', { keyPath: 'item_id' });
        }

        // Exercise results
        if (!db.objectStoreNames.contains('results')) {
          const rstore = db.createObjectStore('results', { keyPath: 'id', autoIncrement: true });
          rstore.createIndex('date', 'date', { unique: false });
          rstore.createIndex('type', 'type', { unique: false });
        }

        // App settings
        if (!db.objectStoreNames.contains('settings')) {
          db.createObjectStore('settings', { keyPath: 'key' });
        }
      };
    });
  }

  // Generic CRUD
  async put(storeName, data) {
    const tx = this.db.transaction(storeName, 'readwrite');
    tx.objectStore(storeName).put(data);
    return new Promise((resolve, reject) => {
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }

  async get(storeName, key) {
    const tx = this.db.transaction(storeName, 'readonly');
    const req = tx.objectStore(storeName).get(key);
    return new Promise((resolve, reject) => {
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async getAll(storeName) {
    const tx = this.db.transaction(storeName, 'readonly');
    const req = tx.objectStore(storeName).getAll();
    return new Promise((resolve, reject) => {
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async getAllByIndex(storeName, indexName, value) {
    const tx = this.db.transaction(storeName, 'readonly');
    const index = tx.objectStore(storeName).index(indexName);
    const req = index.getAll(value);
    return new Promise((resolve, reject) => {
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async delete(storeName, key) {
    const tx = this.db.transaction(storeName, 'readwrite');
    tx.objectStore(storeName).delete(key);
    return new Promise((resolve, reject) => {
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }

  // Meeting-specific methods
  async importMeeting(meetingData) {
    // Save meeting metadata
    await this.put('meetings', {
      id: meetingData.meeting_id,
      date: meetingData.date,
      topic: meetingData.topic_hint,
      imported_at: new Date().toISOString(),
    });

    // Save all items with meeting reference
    const allItems = [
      ...(meetingData.vocabulary || []).map(v => ({ ...v, meeting_id: meetingData.meeting_id, status: 'new' })),
      ...(meetingData.phrases || []).map(p => ({ ...p, meeting_id: meetingData.meeting_id, status: 'new' })),
      ...(meetingData.grammar || []).map(g => ({ ...g, meeting_id: meetingData.meeting_id, status: 'new' })),
    ];

    for (const item of allItems) {
      // Don't overwrite existing status
      const existing = await this.get('items', item.id);
      if (existing) {
        item.status = existing.status;
      }
      await this.put('items', item);
    }

    // Save exercises as part of meeting metadata
    await this.put('meetings', {
      id: meetingData.meeting_id,
      date: meetingData.date,
      topic: meetingData.topic_hint,
      exercises: meetingData.exercises,
      imported_at: new Date().toISOString(),
    });

    return allItems.length;
  }

  // SRS methods
  async getSRSData(itemId) {
    return await this.get('srs', itemId) || {
      item_id: itemId,
      ease_factor: 2.5,
      interval: 0,
      repetitions: 0,
      next_review: new Date().toISOString(),
      last_review: null,
    };
  }

  async updateSRS(itemId, quality) {
    const srs = await this.getSRSData(itemId);
    // SM-2 algorithm
    if (quality >= 3) {
      if (srs.repetitions === 0) srs.interval = 1;
      else if (srs.repetitions === 1) srs.interval = 3;
      else srs.interval = Math.round(srs.interval * srs.ease_factor);
      srs.repetitions++;
    } else {
      srs.repetitions = 0;
      srs.interval = 0;
    }
    srs.ease_factor = Math.max(1.3, srs.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)));
    srs.last_review = new Date().toISOString();
    srs.next_review = new Date(Date.now() + srs.interval * 86400000).toISOString();

    await this.put('srs', srs);

    // Update item status
    const item = await this.get('items', itemId);
    if (item) {
      if (srs.interval >= 21) item.status = 'mastered';
      else if (srs.repetitions > 0) item.status = 'learning';
      else item.status = 'new';
      await this.put('items', item);
    }
    return srs;
  }

  // Get items due for review today
  async getDueItems(meetingId) {
    const now = new Date().toISOString();
    let items = meetingId
      ? await this.getAllByIndex('items', 'meeting', meetingId)
      : await this.getAll('items');

    const dueItems = [];
    for (const item of items) {
      const srs = await this.getSRSData(item.id);
      if (srs.next_review <= now || srs.repetitions === 0) {
        dueItems.push({ ...item, srs });
      }
    }
    return dueItems;
  }

  // Save exercise result
  async saveResult(type, correct, total, meetingId) {
    await this.put('results', {
      date: new Date().toISOString().split('T')[0],
      type,
      correct,
      total,
      meeting_id: meetingId,
      timestamp: new Date().toISOString(),
    });
  }

  // Get stats
  async getStats() {
    const items = await this.getAll('items');
    const results = await this.getAll('results');
    return {
      total: items.length,
      new: items.filter(i => i.status === 'new').length,
      learning: items.filter(i => i.status === 'learning').length,
      mastered: items.filter(i => i.status === 'mastered').length,
      results,
    };
  }
}

// Singleton
window.nihongoDB = new NihongoDB();

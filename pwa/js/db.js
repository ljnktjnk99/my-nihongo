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

  // Normalize a sentence item from new schema
  _normalizeSentence(s, meetingId) {
    return {
      ...s,
      meeting_id: meetingId,
      meeting: meetingId,
      type: 'sentence',
      status: 'new',
      // Map for UI compatibility
      word: s.sentence || '',
      meaning: s.meaning_vi || '',
      context: s.sentence || '',
      context_reading: s.reading || '',
      context_vi: s.meaning_vi || '',
      usage: '',
      errors: 0,
    };
  }

  // Legacy: normalize vocab/phrase/grammar item (for old format JSON)
  _normalizeItem(item, type, meetingId) {
    const base = {
      ...item,
      meeting_id: meetingId,
      meeting: meetingId,
      type: type,
      status: 'new',
      meaning: item.meaning_vi || item.meaning || '',
      context: item.context_sentence || item.context || '',
      context_reading: item.context_reading || '',
      context_vi: item.context_meaning_vi || item.context_vi || '',
      usage: item.usage_note || item.usage || '',
      errors: 0,
    };
    if (type === 'phrase' && item.phrase && !item.word) {
      base.word = item.phrase;
      base.reading = item.reading || item.phrase;
    }
    if (type === 'grammar' && item.pattern && !item.word) {
      base.word = item.pattern;
      base.reading = item.reading || item.pattern;
    }
    return base;
  }

  // Normalize exercises from real JSON format to UI format
  _normalizeExercises(exercises) {
    if (!exercises) return null;
    const norm = {};
    if (exercises.translate_vj) {
      norm.translate_vj = exercises.translate_vj.map(e => ({
        prompt: e.prompt_vi || e.prompt,
        answers: e.acceptable_answers || e.answers || [],
        keys: e.key_points || e.keys || [],
        difficulty: e.difficulty,
        ref_id: e.ref_id,
      }));
    }
    if (exercises.translate_jv) {
      norm.translate_jv = exercises.translate_jv.map(e => ({
        prompt: e.prompt_ja || e.prompt,
        prompt_reading: e.prompt_reading || '',
        answers: e.acceptable_keywords_vi || e.answers || [],
        keys: e.acceptable_keywords_vi || e.keys || [],
        reference_answer: e.reference_answer_vi,
        ref_id: e.ref_id,
      }));
    }
    if (exercises.fill_blank) {
      norm.fill_blank = exercises.fill_blank.map(e => ({
        sentence: e.sentence,
        sentence_reading: e.sentence_reading || '',
        answer: e.answer,
        options: e.options,
        hint: e.hint_vi || e.hint,
        ref_id: e.ref_id,
      }));
    }
    if (exercises.reorder) {
      norm.reorder = exercises.reorder.map(e => ({
        fragments: e.fragments,
        correct: e.correct_order || e.correct,
        meaning: e.meaning_vi || e.meaning,
        ref_id: e.ref_id,
      }));
    }
    return norm;
  }

  // Meeting-specific methods
  async importMeeting(meetingData) {
    const meetingId = meetingData.meeting_id;

    // Support both new (sentences) and old (vocabulary/phrases/grammar) schema
    let allItems;
    if (meetingData.sentences) {
      allItems = meetingData.sentences.map(s => this._normalizeSentence(s, meetingId));
    } else {
      allItems = [
        ...(meetingData.vocabulary || []).map(v => this._normalizeItem(v, 'vocab', meetingId)),
        ...(meetingData.phrases || []).map(p => this._normalizeItem(p, 'phrase', meetingId)),
        ...(meetingData.grammar || []).map(g => this._normalizeItem(g, 'grammar', meetingId)),
      ];
    }

    for (const item of allItems) {
      // Preserve existing learning status
      const existing = await this.get('items', item.id);
      if (existing) {
        item.status = existing.status;
        item.errors = existing.errors || 0;
      }
      await this.put('items', item);
    }

    // Normalize exercises and save meeting metadata
    const exercises = this._normalizeExercises(meetingData.exercises);
    await this.put('meetings', {
      id: meetingId,
      date: meetingData.date,
      topic: meetingData.topic_hint,
      exercises: exercises,
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

  // Load all data into a flat object for UI consumption
  async loadAllData() {
    const meetings = await this.getAll('meetings');
    const items = await this.getAll('items');
    const exercises = {};

    // Merge exercises from all meetings, tagging each with meeting id
    for (const m of meetings) {
      if (!m.exercises) continue;
      for (const type of ['translate_vj', 'translate_jv', 'fill_blank', 'reorder']) {
        if (!m.exercises[type]) continue;
        if (!exercises[type]) exercises[type] = [];
        exercises[type].push(...m.exercises[type].map(e => ({ ...e, meeting: m.id })));
      }
    }

    return {
      meetings: meetings.map(m => ({ id: m.id, topic: m.topic, date: m.date })),
      vocabulary: items,
      exercises,
      weeklyStudy: [0, 0, 0, 0, 0, 0, 0],
    };
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

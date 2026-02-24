/**
 * Data Loader - Fetches meeting data from GitHub Pages and syncs to IndexedDB
 */
class DataLoader {
  constructor() {
    // Auto-detect base URL: works on GitHub Pages and local dev
    this.baseUrl = this._detectBaseUrl();
  }

  _detectBaseUrl() {
    const loc = window.location;
    // If on GitHub Pages, data is at ./data/
    // If local, data is at ./data/
    return loc.origin + loc.pathname.replace(/\/[^/]*$/, '');
  }

  async fetchIndex() {
    try {
      const resp = await fetch(`${this.baseUrl}/data/index.json?t=${Date.now()}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (e) {
      console.warn('Failed to fetch index from network, using cached data');
      return null;
    }
  }

  async fetchMeeting(filename) {
    try {
      const resp = await fetch(`${this.baseUrl}/data/${filename}?t=${Date.now()}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (e) {
      console.warn(`Failed to fetch ${filename}`);
      return null;
    }
  }

  async syncAll() {
    const db = window.nihongoDB;
    if (!db.db) await db.open();

    const index = await this.fetchIndex();
    if (!index || !index.meetings) {
      console.log('No new data from server, using local data');
      return { synced: 0, total: (await db.getAll('meetings')).length };
    }

    let synced = 0;
    for (const meeting of index.meetings) {
      // Check if already imported
      const existing = await db.get('meetings', meeting.id);
      if (existing && existing.imported_at) {
        continue; // Already have this meeting
      }

      const data = await this.fetchMeeting(meeting.file);
      if (data) {
        const count = await db.importMeeting(data);
        synced++;
        console.log(`Imported: ${meeting.topic} (${count} items)`);
      }
    }

    return { synced, total: index.meetings.length };
  }
}

window.dataLoader = new DataLoader();

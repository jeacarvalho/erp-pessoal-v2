const STORAGE_KEY = 'offline_notes_urls';

export interface OfflineNote {
  url: string;
  timestamp: number;
}

export const getOfflineNotes = (): OfflineNote[] => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    return JSON.parse(stored);
  } catch {
    return [];
  }
};

export const saveOfflineNote = (url: string): void => {
  try {
    const notes = getOfflineNotes();
    
    const alreadyExists = notes.some((n) => n.url === url);
    if (alreadyExists) {
      return;
    }
    
    notes.push({ url, timestamp: Date.now() });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notes));
  } catch {
    console.error('[OfflineStorage] Failed to save note');
  }
};

export const removeOfflineNote = (url: string): void => {
  try {
    const notes = getOfflineNotes();
    const filtered = notes.filter((n) => n.url !== url);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
  } catch {
    console.error('[OfflineStorage] Failed to remove note');
  }
};

export const clearOfflineNotes = (): void => {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    console.error('[OfflineStorage] Failed to clear notes');
  }
};

export const getOfflineNotesCount = (): number => {
  return getOfflineNotes().length;
};

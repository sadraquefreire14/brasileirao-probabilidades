import snapshotJson from '../data/brasileirao.json';
import historyJson from '../data/history.json';
import type { HistoryEntry, Snapshot } from './types';

export const snapshot = snapshotJson as Snapshot;
export const history = (historyJson as HistoryEntry[]).filter(
  (h) => Boolean(h.sample) === snapshot.sample,
);

import { describe, expect, it, vi } from 'vitest';
import {
  appendMlTestingRun,
  createDefaultDraftConfig,
  createEmptySession,
  deleteMlTestingRun,
  loadMlTestingSession,
  parseMlTestingSession,
  saveMlTestingSession,
  sessionStorageKey,
  toggleMlTestingRunStar,
  updateMlTestingRun,
  type MlTestingRun,
} from '../utils/mlTestingSession';

function mockStorage(): Storage {
  const map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    clear: () => map.clear(),
    getItem: (key: string) => map.get(key) ?? null,
    key: (index: number) => [...map.keys()][index] ?? null,
    removeItem: (key: string) => {
      map.delete(key);
    },
    setItem: (key: string, value: string) => {
      map.set(key, value);
    },
  };
}

describe('mlTestingSession', () => {
  it('builds storage key from symbol and timeframe', () => {
    expect(sessionStorageKey('aapl', '1d')).toBe('ml-testing:v1:AAPL:1d');
  });

  it('round-trips session through storage', () => {
    const storage = mockStorage();
    const session = createEmptySession({
      symbol: 'MSFT',
      timeframe: '1d',
      dateRange: { preset: '1Y' },
    });
    saveMlTestingSession(session, storage);
    const loaded = loadMlTestingSession('MSFT', '1d', storage);
    expect(loaded?.symbol).toBe('MSFT');
    expect(loaded?.draftConfig.modelType).toBe('ml_gradient_boosting');
  });

  it('appends and deletes runs', () => {
    const session = createEmptySession({
      symbol: 'AAPL',
      timeframe: '1d',
      dateRange: { preset: 'MAX' },
    });
    const run: MlTestingRun = {
      clientId: 'run-1',
      config: createDefaultDraftConfig({
        symbol: 'AAPL',
        timeframe: '1d',
        dateRange: { preset: 'MAX' },
      }),
      status: 'completed',
      createdAt: '2026-01-01T00:00:00Z',
    };
    const withRun = appendMlTestingRun(session, run);
    expect(withRun.runs).toHaveLength(1);
    const cleared = deleteMlTestingRun(withRun, 'run-1');
    expect(cleared.runs).toHaveLength(0);
  });

  it('toggles star on a run', () => {
    const session = createEmptySession({
      symbol: 'AAPL',
      timeframe: '1d',
      dateRange: { preset: 'MAX' },
    });
    const run: MlTestingRun = {
      clientId: 'run-1',
      config: session.draftConfig,
      status: 'completed',
      createdAt: '2026-01-01T00:00:00Z',
    };
    const starred = toggleMlTestingRunStar(appendMlTestingRun(session, run), 'run-1');
    expect(starred.runs[0].starred).toBe(true);
  });

  it('rejects invalid JSON', () => {
    expect(parseMlTestingSession('{bad')).toBeNull();
  });

  it('marks a pending run completed after append', () => {
    const session = createEmptySession({
      symbol: 'MSFT',
      timeframe: '1d',
      dateRange: { preset: '1Y' },
    });
    const pending: MlTestingRun = {
      clientId: 'run-pending',
      config: session.draftConfig,
      status: 'running',
      createdAt: '2026-06-02T00:00:00Z',
    };
    const withPending = appendMlTestingRun(session, pending);
    const completed = updateMlTestingRun(withPending, 'run-pending', {
      status: 'completed',
      backendRunId: 'backend-1',
    });
    expect(completed.runs[0].status).toBe('completed');
    expect(completed.runs[0].backendRunId).toBe('backend-1');
  });
});

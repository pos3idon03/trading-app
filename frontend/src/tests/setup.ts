import '@testing-library/jest-dom';

// Recharts' ResponsiveContainer uses ResizeObserver which is not available in jsdom
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock;

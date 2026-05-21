import axios from 'axios';

/** Same-origin path; Vite dev server proxies /api → tiingo_backend (see vite.config.ts). */
export const api = axios.create({ baseURL: '/api/v1', timeout: 120_000 });

import axios, { AxiosError, type AxiosInstance } from 'axios';

import { getApiErrorMessage } from '../utils/apiErrorMessage';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

/** Walk-forward optimization can run hundreds of backtests; allow up to 15 minutes. */
export const OPTIMIZE_REQUEST_TIMEOUT_MS = 900_000;

const api: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 60_000,
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const message = getApiErrorMessage(error.response?.data, error.message ?? 'Unknown error');
    return Promise.reject(new Error(message));
  },
);

export default api;

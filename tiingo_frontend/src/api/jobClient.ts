import axios from 'axios';

/** Job status polling can outlast default API timeouts (LSTM walk-forward, etc.). */
export const jobPollApi = axios.create({
  baseURL: '/api/v1',
  timeout: 600_000,
});

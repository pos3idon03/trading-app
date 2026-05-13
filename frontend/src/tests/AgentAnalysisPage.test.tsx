import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AgentAnalysisPage from '../pages/AgentAnalysisPage';

vi.mock('../api/endpoints', () => ({
  dataApi: {
    getAssets: vi.fn().mockResolvedValue({
      assets: [
        { id: 1, symbol: 'NVDA', name: 'NVIDIA', asset_type: 'stock', exchange: 'NASDAQ', currency: 'USD', is_active: true },
      ],
    }),
  },
  agentApi: {
    analyze: vi.fn().mockResolvedValue({
      analysis_id: 1,
      asset_id: 1,
      symbol: 'NVDA',
      status: 'done',
      signal: {
        asset: 'NVDA',
        bias: 'bullish',
        conviction_score: 0.76,
        fundamental_summary: 'Strong revenue growth.',
        macro_summary: 'Supportive easing cycle.',
        macro_score: 0.55,
        sentiment_score: 0.75,
        reasoning: 'AI demand drives upside.',
        key_risk: 'Supply chain fragility.',
        timestamp: '2024-05-09T12:00:00Z',
      },
      reports: {
        fundamental: 'Fundamental analysis text.',
        macro: 'Macro analysis text.',
        sentiment: 'Sentiment analysis text.',
      },
      duration_ms: 63000,
      provider_used: 'openai/gpt-4o-mini',
    }),
  },
}));

describe('AgentAnalysisPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page heading', () => {
    render(<AgentAnalysisPage />);
    expect(screen.getByText('AI Agent Analysis')).toBeInTheDocument();
  });

  it('renders Run Analysis button', () => {
    render(<AgentAnalysisPage />);
    expect(screen.getByRole('button', { name: /Run Analysis/i })).toBeInTheDocument();
  });

  it('shows conviction, sentiment, and macro score after analysis', async () => {
    const user = userEvent.setup();
    render(<AgentAnalysisPage />);

    await waitFor(() => screen.getByRole('button', { name: /Run Analysis/i }));
    await user.click(screen.getByRole('button', { name: /Run Analysis/i }));

    await waitFor(() => {
      expect(screen.getAllByText('Conviction').length).toBeGreaterThanOrEqual(1);
    });

    expect(screen.getByText('Sentiment Score')).toBeInTheDocument();
    expect(screen.getByText('Macro Score')).toBeInTheDocument();
  });

  it('displays bias chip after analysis', async () => {
    const user = userEvent.setup();
    render(<AgentAnalysisPage />);

    await waitFor(() => screen.getByRole('button', { name: /Run Analysis/i }));
    await user.click(screen.getByRole('button', { name: /Run Analysis/i }));

    // BiasChip renders the bias string as-is; CSS `uppercase` transforms it visually
    await waitFor(() => {
      expect(screen.getByText('bullish')).toBeInTheDocument();
    });
  });

  it('renders macro score numeric value', async () => {
    const user = userEvent.setup();
    render(<AgentAnalysisPage />);

    await waitFor(() => screen.getByRole('button', { name: /Run Analysis/i }));
    await user.click(screen.getByRole('button', { name: /Run Analysis/i }));

    await waitFor(() => {
      expect(screen.getByText('0.55')).toBeInTheDocument();
    });
  });

  it('renders key risk section after analysis', async () => {
    const user = userEvent.setup();
    render(<AgentAnalysisPage />);

    await waitFor(() => screen.getByRole('button', { name: /Run Analysis/i }));
    await user.click(screen.getByRole('button', { name: /Run Analysis/i }));

    await waitFor(() => {
      expect(screen.getByText('Supply chain fragility.')).toBeInTheDocument();
    });
  });
});

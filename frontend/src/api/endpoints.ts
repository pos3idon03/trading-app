import api from './client';
import type {
  AgentAnalysisRequest,
  AgentAnalysisResponse,
  AssetListResponse,
  AssetWithPriceListResponse,
  AttachAlgoRequest,
  AutoTradingAssetRow,
  BacktestRequest,
  BacktestResponse,
  ChartOverlayRequest,
  ChartOverlayResponse,
  ComboBacktestRequest,
  ComboSignalsResponse,
  CompanyProfile,
  CreateStrategyRequest,
  DeleteAssetResponse,
  DetachAlgoRequest,
  ExecutionStatusResponse,
  FinancialStatement,
  FinancialsIngestResponse,
  FundamentalsOverview,
  IndicatorSnapshotResponse,
  IngestRequest,
  IngestResponse,
  IngestionStatusResponse,
  OHLCVQueryResponse,
  OptimizationRequest,
  OptimizationResponse,
  OrderHistoryResponse,
  PortfolioResponse,
  RiskConfigResponse,
  RiskConfigUpdateRequest,
  RiskEventHistoryResponse,
  SignalHistoryResponse,
  SimulationRequest,
  SimulationResponse,
  StrategyFullResponse,
  StrategyRecord,
  StrategySignalsResponse,
  StreamStartRequest,
  StreamStatusResponse,
  TickerSearchResponse,
  TradingSignalItem,
  UpdatePositionSizingRequest,
  UpdateThresholdsRequest,
} from './types';

export const dataApi = {
  triggerIngestion: (req: IngestRequest) =>
    api.post<IngestResponse>('/data/ingest', req).then((r) => r.data),

  getAssets: () =>
    api.get<AssetListResponse>('/data/assets').then((r) => r.data),

  getAssetsWithPrices: () =>
    api.get<AssetWithPriceListResponse>('/data/assets/with-prices').then((r) => r.data),

  getOHLCVBySymbol: (
    symbol: string,
    timeframe: string,
    start?: string,
    end?: string,
  ) =>
    api
      .get<OHLCVQueryResponse>(`/data/ohlcv/by-symbol/${symbol}`, {
        params: { timeframe, start, end },
      })
      .then((r) => r.data),

  getOHLCV: (
    assetId: number,
    timeframe: string,
    start?: string,
    end?: string,
  ) =>
    api
      .get<OHLCVQueryResponse>(`/data/ohlcv/${assetId}`, {
        params: { timeframe, start, end },
      })
      .then((r) => r.data),

  getStatus: () =>
    api.get<IngestionStatusResponse>('/data/status').then((r) => r.data),

  searchTickers: (query: string, limit = 10) =>
    api
      .get<TickerSearchResponse>('/data/tickers/search', { params: { query, limit } })
      .then((r) => r.data),

  deleteAsset: (symbol: string) =>
    api.delete<DeleteAssetResponse>(`/data/assets/${symbol}`).then((r) => r.data),
};

export const simulationApi = {
  calibrate: (assetId: number, timeframe = '1d') =>
    api
      .post(`/simulation/calibrate/${assetId}`, { timeframe })
      .then((r) => r.data),

  run: (req: SimulationRequest) =>
    api.post<SimulationResponse>('/simulation/run', req).then((r) => r.data),

  get: (simId: number) =>
    api.get<SimulationResponse>(`/simulation/${simId}`).then((r) => r.data),
};

export const backtestApi = {
  run: (req: BacktestRequest) =>
    api.post<BacktestResponse>('/backtest/run', req).then((r) => r.data),

  optimize: (req: OptimizationRequest) =>
    api.post<OptimizationResponse>('/backtest/optimize', req).then((r) => r.data),

  runCombo: (req: ComboBacktestRequest) =>
    api.post<BacktestResponse>('/backtest/combo', req).then((r) => r.data),

  getComboSignals: (req: ComboBacktestRequest) =>
    api.post<ComboSignalsResponse>('/backtest/combo-signals', req).then((r) => r.data),

  getChartOverlay: (req: ChartOverlayRequest) =>
    api.post<ChartOverlayResponse>('/backtest/chart-overlay', req).then((r) => r.data),
};

export const agentApi = {
  analyze: (req: AgentAnalysisRequest) =>
    api.post<AgentAnalysisResponse>('/agents/analyze', req, { timeout: 180_000 }).then((r) => r.data),

  get: (analysisId: number) =>
    api.get<AgentAnalysisResponse>(`/agents/${analysisId}`).then((r) => r.data),
};

export const liveApi = {
  startStream: (req: StreamStartRequest) =>
    api.post<StreamStatusResponse>('/live/start', req).then((r) => r.data),

  stopStream: () =>
    api.post<StreamStatusResponse>('/live/stop').then((r) => r.data),

  getStatus: () =>
    api.get<StreamStatusResponse>('/live/status').then((r) => r.data),

  getIndicators: (symbol: string, timeframe = '1h') =>
    api
      .get<IndicatorSnapshotResponse>(`/live/indicators/${symbol}`, {
        params: { timeframe },
      })
      .then((r) => r.data),

  getLatestSignal: (symbol: string) =>
    api.get<TradingSignalItem | { message: string }>(`/live/signals/${symbol}`).then((r) => r.data),

  getSignalHistory: (symbol?: string, limit = 50) =>
    api
      .get<SignalHistoryResponse>('/live/signals', {
        params: { symbol, limit },
      })
      .then((r) => r.data),

  getStrategySignals: (
    symbol: string,
    timeframe = '1h',
    options?: { includeTimeline?: boolean; timelineBars?: number },
  ) =>
    api
      .get<StrategySignalsResponse>(`/live/strategy-signals/${symbol}`, {
        params: {
          timeframe,
          ...(options?.includeTimeline ? { include_timeline: true } : {}),
          ...(options?.timelineBars != null ? { timeline_bars: options.timelineBars } : {}),
        },
      })
      .then((r) => r.data),
};

export const financialsApi = {
  getOverview: (symbol: string) =>
    api.get<FundamentalsOverview>(`/financials/${symbol}/overview`).then((r) => r.data),

  getIncomeStatement: (symbol: string) =>
    api.get<FinancialStatement>(`/financials/${symbol}/income-statement`).then((r) => r.data),

  getBalanceSheet: (symbol: string) =>
    api.get<FinancialStatement>(`/financials/${symbol}/balance-sheet`).then((r) => r.data),

  getCashFlow: (symbol: string) =>
    api.get<FinancialStatement>(`/financials/${symbol}/cash-flow`).then((r) => r.data),

  getProfile: (symbol: string) =>
    api.get<CompanyProfile>(`/financials/${symbol}/profile`).then((r) => r.data),

  ingest: (symbol: string) =>
    api.post<FinancialsIngestResponse>(`/financials/${symbol}/ingest`).then((r) => r.data),
};

export const strategyBuilderApi = {
  create: (req: CreateStrategyRequest) =>
    api.post<StrategyRecord>('/strategy-builder/create', req).then((r) => r.data),

  list: () =>
    api.get<StrategyRecord[]>('/strategy-builder/strategies').then((r) => r.data),

  getFull: (strategyId: number) =>
    api.get<StrategyFullResponse>(`/strategy-builder/${strategyId}/full`).then((r) => r.data),

  updateThresholds: (strategyId: number, req: UpdateThresholdsRequest) =>
    api.patch<StrategyRecord>(`/strategy-builder/${strategyId}/thresholds`, req).then((r) => r.data),

  attachAlgo: (req: AttachAlgoRequest) =>
    api.post<StrategyRecord>('/strategy-builder/attach-algo', req).then((r) => r.data),

  detachAlgo: (req: DetachAlgoRequest) =>
    api.delete('/strategy-builder/detach-algo', { data: req }).then((r) => r.data),

  remove: (strategyId: number) =>
    api.delete(`/strategy-builder/${strategyId}`).then((r) => r.data),
};

export const autoTradingApi = {
  list: () =>
    api.get<AutoTradingAssetRow[]>('/auto-trading/assets').then((r) => r.data),

  start: (strategyId: number, req: UpdatePositionSizingRequest) =>
    api.patch<AutoTradingAssetRow>(`/auto-trading/${strategyId}/start`, req).then((r) => r.data),

  stop: (strategyId: number) =>
    api.patch<AutoTradingAssetRow>(`/auto-trading/${strategyId}/stop`).then((r) => r.data),
};

export const executionApi = {
  enable: () =>
    api.post<ExecutionStatusResponse>('/execution/enable').then((r) => r.data),

  disable: () =>
    api.post<ExecutionStatusResponse>('/execution/disable').then((r) => r.data),

  getStatus: () =>
    api.get<ExecutionStatusResponse>('/execution/status').then((r) => r.data),

  getOrders: (symbol?: string, limit = 50, offset = 0) =>
    api
      .get<OrderHistoryResponse>('/execution/orders', {
        params: { symbol, limit, offset },
      })
      .then((r) => r.data),

  getPortfolio: () =>
    api.get<PortfolioResponse>('/execution/portfolio').then((r) => r.data),

  getRiskConfig: () =>
    api.get<RiskConfigResponse>('/execution/risk/config').then((r) => r.data),

  updateRiskConfig: (req: RiskConfigUpdateRequest) =>
    api.put<RiskConfigResponse>('/execution/risk/config', req).then((r) => r.data),

  getRiskEvents: (limit = 50) =>
    api
      .get<RiskEventHistoryResponse>('/execution/risk/events', {
        params: { limit },
      })
      .then((r) => r.data),
};

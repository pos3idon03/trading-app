import type { MlParams, MlRunRequest } from '../api/mlBacktestTypes';
import type { DateRangeValue } from '../constants/timeframes';
import { buildOhlcvQuery } from '../constants/timeframes';
import { apiRangeFromOhlcvQuery } from './multitimeframeBacktest';

export interface BuildMlRunRequestInput {
  symbol: string;
  modelType: string;
  params: Partial<MlParams>;
  timeframe: string;
  dateRange: DateRangeValue;
  initialCash?: number;
  commissionBps?: number;
}

export function buildMlRunRequest(input: BuildMlRunRequestInput): MlRunRequest {
  const ohlcvQuery = buildOhlcvQuery(input.timeframe, input.dateRange);
  return {
    symbol: input.symbol,
    model_type: input.modelType,
    params: input.params,
    timeframe: input.timeframe,
    initial_cash: input.initialCash,
    commission_bps: input.commissionBps,
    ...apiRangeFromOhlcvQuery(ohlcvQuery),
  };
}

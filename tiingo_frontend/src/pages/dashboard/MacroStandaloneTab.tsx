import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ingestionApi } from '../../api/endpoints';
import type { DashboardSeriesRef, MacroObservation, MacroSeries } from '../../api/types';
import AddTrendModal from '../../components/AddTrendModal';
import DateRangeControls from '../../components/DateRangeControls';
import ErrorAlert from '../../components/ErrorAlert';
import MacroSeriesSearch from '../../components/MacroSeriesSearch';
import UnifiedSeriesSearch from '../../components/UnifiedSeriesSearch';
import Spinner from '../../components/Spinner';
import MacroChangeContextPanel from '../../components/charts/MacroChangeContextPanel';
import MacroPeriodSlider from '../../components/charts/MacroPeriodSlider';
import MacroRelationshipScatter from '../../components/charts/MacroRelationshipScatter';
import MacroStandaloneChart from '../../components/charts/MacroStandaloneChart';
import {
  type DateRangeValue,
  computePresetRange,
} from '../../constants/timeframes';
import {
  alignAssetToMacroDates,
  buildPeriodChangeContext,
  buildPeriodChangeSeries,
  resolveMacroStep,
} from '../../utils/macroStandaloneData';
import {
  fetchSeriesObservations,
  macroToRef,
  pointsToObservations,
  type TimeSeriesPoint,
} from '../../utils/seriesData';
import {
  MAX_TREND_OVERLAYS,
  type TrendOverlayConfig,
} from '../../utils/technicalIndicators';

const INSTRUMENT_TYPES = ['stock', 'etf'];

function createOverlayId(): string {
  return `trend-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

export default function MacroStandaloneTab() {
  const { seriesId } = useParams<{ seriesId?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const assetId = searchParams.get('asset')?.toUpperCase() || null;
  const navigate = useNavigate();

  const [selected, setSelected] = useState<MacroSeries | null>(null);
  const [assetRef, setAssetRef] = useState<DashboardSeriesRef | null>(null);
  const [observations, setObservations] = useState<MacroObservation[]>([]);
  const [assetPoints, setAssetPoints] = useState<TimeSeriesPoint[]>([]);
  const [dateRange, setDateRange] = useState<DateRangeValue>(() => computePresetRange('MAX', 'date'));
  const [loading, setLoading] = useState(false);
  const [assetLoading, setAssetLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [overlays, setOverlays] = useState<TrendOverlayConfig[]>([]);
  const [trendModalOpen, setTrendModalOpen] = useState(false);
  const [sliderIndex, setSliderIndex] = useState(0);

  useEffect(() => {
    if (!seriesId) {
      setSelected(null);
      setObservations([]);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    const primaryId = seriesId.toUpperCase();

    ingestionApi
      .listMacroSeries({ ingestedOnly: true, query: primaryId, limit: 1 })
      .then((catalog) => {
        const match = catalog.find((s) => s.series_id === primaryId);
        const series =
          match ?? {
            series_id: primaryId,
            title: primaryId,
            category: 'general',
            is_enabled: false,
          };
        if (cancelled) return null;
        setSelected(series);
        return fetchSeriesObservations(macroToRef(series), dateRange);
      })
      .then((points) => {
        if (cancelled || !points) return;
        setObservations(pointsToObservations(points));
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load macro series. Backfill from Ingestion.');
          setObservations([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [seriesId, dateRange]);

  useEffect(() => {
    if (!assetId) {
      setAssetRef(null);
      setAssetPoints([]);
      return;
    }

    let cancelled = false;
    setAssetLoading(true);
    const ref: DashboardSeriesRef = {
      source: 'instrument',
      id: assetId,
      label: assetId,
    };

    fetchSeriesObservations(ref, dateRange)
      .then((points) => {
        if (cancelled) return;
        setAssetRef(ref);
        setAssetPoints(points);
      })
      .catch(() => {
        if (!cancelled) {
          setAssetRef(null);
          setAssetPoints([]);
        }
      })
      .finally(() => {
        if (!cancelled) setAssetLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [assetId, dateRange]);

  const withStandaloneTab = (params: URLSearchParams): URLSearchParams => {
    params.set('tab', 'standalone');
    return params;
  };

  const handleSelect = (series: MacroSeries | null) => {
    setSelected(series);
    setOverlays([]);
    if (series) {
      const params = withStandaloneTab(new URLSearchParams());
      if (assetId) params.set('asset', assetId);
      const qs = params.toString();
      navigate(`/dashboard/macro/${series.series_id}?${qs}`);
    } else {
      const qs = withStandaloneTab(new URLSearchParams()).toString();
      navigate(`/dashboard/macro?${qs}`);
    }
  };

  const handleAssetSelect = (ref: DashboardSeriesRef | null) => {
    setAssetRef(ref);
    if (!seriesId) return;

    const params = withStandaloneTab(new URLSearchParams(searchParams));
    if (ref) {
      params.set('asset', ref.id);
    } else {
      params.delete('asset');
    }
    setSearchParams(params);
  };

  const stepLabel = resolveMacroStep(selected?.frequency, observations);
  const aligned = useMemo(
    () => alignAssetToMacroDates(observations, assetPoints),
    [observations, assetPoints],
  );
  const changeSeries = useMemo(() => buildPeriodChangeSeries(aligned), [aligned]);
  const changeContext = useMemo(
    () => buildPeriodChangeContext(changeSeries, sliderIndex),
    [changeSeries, sliderIndex],
  );

  useEffect(() => {
    if (changeSeries.length === 0) {
      setSliderIndex(0);
      return;
    }
    setSliderIndex(changeSeries.length - 1);
  }, [changeSeries.length, seriesId, assetId]);

  const rangeLabel =
    dateRange.preset === 'MAX' && !dateRange.start
      ? 'MAX'
      : [dateRange.start, dateRange.end].filter(Boolean).join(' → ');

  const chartSubtitle = selected
    ? `${selected.series_id} · ${selected.title} · ${observations.length} observations · ${rangeLabel}`
    : '';

  const handleAddTrend = (result: { type: 'sma' | 'ema'; period: number }) => {
    if (overlays.length >= MAX_TREND_OVERLAYS) return;
    const duplicate = overlays.some(
      (o) => o.type === result.type && o.period === result.period,
    );
    if (duplicate) {
      setTrendModalOpen(false);
      return;
    }
    setOverlays((prev) => [
      ...prev,
      { id: createOverlayId(), type: result.type, period: result.period },
    ]);
    setTrendModalOpen(false);
  };

  const sliderDisabled = changeSeries.length < 1;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <p className="text-xs text-slate-500 mb-1">Macro series (FRED)</p>
          <MacroSeriesSearch selected={selected} onSelect={handleSelect} />
        </div>
        <div>
          <p className="text-xs text-slate-500 mb-1">Compare asset (stock or ETF)</p>
          <UnifiedSeriesSearch
            selected={assetRef}
            onSelect={handleAssetSelect}
            sources={['instrument']}
            instrumentTypes={INSTRUMENT_TYPES}
            placeholder="Stock or ETF, e.g. QQQ"
            disabled={!seriesId}
          />
        </div>
      </div>

      <DateRangeControls value={dateRange} onChange={setDateRange} mode="date" />

      {error && (
        <ErrorAlert message={error}>
          <Link to="/ingestion/fred" className="text-brand-500 underline text-sm mt-1 inline-block">
            Go to FRED Macro Ingestion
          </Link>
        </ErrorAlert>
      )}

      {(loading || assetLoading) && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}

      {!loading && seriesId && observations.length > 0 && selected && (
        <div className="space-y-2">
          <p className="text-xs text-slate-500">{chartSubtitle}</p>
          <MacroStandaloneChart
            observations={observations}
            seriesId={selected.series_id}
            seriesTitle={selected.title}
            overlays={overlays}
            onRemoveOverlay={(id) => setOverlays((prev) => prev.filter((o) => o.id !== id))}
            onAddTrendClick={() => setTrendModalOpen(true)}
            canAddTrend={overlays.length < MAX_TREND_OVERLAYS}
          />
        </div>
      )}

      {!loading && !seriesId && (
        <div className="text-center py-16 text-slate-500 text-sm border border-dashed border-slate-800 rounded-lg">
          Search and select a macro series to view standalone analysis with trend overlays.
        </div>
      )}

      {!loading && seriesId && assetId && changeSeries.length > 0 && (
        <div className="space-y-4 border-t border-slate-800 pt-6">
          <MacroPeriodSlider
            changeSeries={changeSeries}
            sliderIndex={sliderIndex}
            stepLabel={stepLabel}
            macroId={selected?.series_id ?? seriesId}
            assetId={assetId}
            disabled={sliderDisabled}
            onChange={setSliderIndex}
          />

          <div className="grid gap-4 xl:grid-cols-2">
            <MacroRelationshipScatter
              changeSeries={changeSeries}
              selectedIndex={sliderIndex}
              macroId={selected?.series_id ?? 'Macro'}
              assetId={assetId}
            />
            <MacroChangeContextPanel
              context={changeContext}
              macroId={selected?.series_id ?? 'Macro'}
              assetId={assetId}
              stepLabel={stepLabel}
            />
          </div>
        </div>
      )}

      {!loading && seriesId && assetId && changeSeries.length === 0 && !assetLoading && (
        <p className="text-sm text-slate-500">
          Not enough overlapping {stepLabel} history between {selected?.series_id} and {assetId}.
        </p>
      )}

      <AddTrendModal
        open={trendModalOpen}
        onConfirm={handleAddTrend}
        onCancel={() => setTrendModalOpen(false)}
      />
    </div>
  );
}

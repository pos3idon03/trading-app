import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ingestionApi } from '../../api/endpoints';
import type { DashboardSeriesRef, MacroObservation, MacroSeries } from '../../api/types';
import DateRangeControls from '../../components/DateRangeControls';
import ErrorAlert from '../../components/ErrorAlert';
import MacroSeriesSearch from '../../components/MacroSeriesSearch';
import UnifiedSeriesSearch from '../../components/UnifiedSeriesSearch';
import Spinner from '../../components/Spinner';
import MacroTimelineChart from '../../components/charts/MacroTimelineChart';
import {
  type DateRangeValue,
  computePresetRange,
  toApiRange,
} from '../../constants/timeframes';
import {
  type MacroCompareSeries,
  computeMacroCompareMeta,
  formatMacroCompareSubtitle,
} from '../../utils/macroChartData';
import {
  fetchSeriesObservations,
  macroToRef,
  pointsToObservations,
} from '../../utils/seriesData';

const COMPARE_COLOR = '#60a5fa';

function parseCompareKind(param: string | null): 'macro' | 'instrument' {
  return param === 'instrument' ? 'instrument' : 'macro';
}

export default function MacroCompareTab() {
  const { seriesId } = useParams<{ seriesId?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const compareId = searchParams.get('compare')?.toUpperCase() || null;
  const compareKind = parseCompareKind(searchParams.get('compareKind'));
  const navigate = useNavigate();

  const [selected, setSelected] = useState<MacroSeries | null>(null);
  const [compareRef, setCompareRef] = useState<DashboardSeriesRef | null>(null);
  const [observations, setObservations] = useState<MacroObservation[]>([]);
  const [compareObservations, setCompareObservations] = useState<MacroObservation[]>([]);
  const [dateRange, setDateRange] = useState<DateRangeValue>(() => computePresetRange('MAX', 'date'));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!seriesId) {
      setSelected(null);
      setCompareRef(null);
      setObservations([]);
      setCompareObservations([]);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    const primaryId = seriesId.toUpperCase();
    const compareUpper = compareId?.toUpperCase() ?? null;
    const hasCompare = Boolean(compareUpper && compareUpper !== primaryId);

    const loadPrimary = ingestionApi
      .listMacroSeries({ ingestedOnly: true, query: primaryId, limit: 1 })
      .then((catalog) => {
        const match = catalog.find((s) => s.series_id === primaryId);
        setSelected(
          match ?? {
            series_id: primaryId,
            title: primaryId,
            category: 'general',
            is_enabled: false,
          },
        );
        return fetchSeriesObservations(macroToRef(match ?? { series_id: primaryId, title: primaryId, category: 'general', is_enabled: false }), dateRange);
      });

    const loadCompare = async (): Promise<MacroObservation[]> => {
      if (!hasCompare || !compareUpper) return [];

      const ref: DashboardSeriesRef =
        compareKind === 'instrument'
          ? { source: 'instrument', id: compareUpper, label: compareUpper }
          : { source: 'macro', id: compareUpper, label: compareUpper };

      try {
        const points = await fetchSeriesObservations(ref, dateRange);
        if (compareKind === 'macro') {
          const catalog = await ingestionApi.listMacroSeries({
            ingestedOnly: true,
            query: compareUpper,
            limit: 1,
          });
          const match = catalog.find((s) => s.series_id === compareUpper);
          setCompareRef(match ? macroToRef(match) : ref);
        } else {
          setCompareRef({ ...ref, label: compareUpper });
        }
        return pointsToObservations(points);
      } catch {
        setCompareRef(null);
        return [];
      }
    };

    Promise.all([loadPrimary, loadCompare()])
      .then(([primaryPoints, compareObs]) => {
        if (cancelled) return;
        setObservations(pointsToObservations(primaryPoints));
        setCompareObservations(compareObs);
        if (!hasCompare) {
          setCompareRef(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load series data. Backfill from Ingestion.');
          setObservations([]);
          setCompareObservations([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [seriesId, compareId, compareKind, dateRange]);

  const withActiveTab = (params: URLSearchParams): URLSearchParams => {
    const tab = searchParams.get('tab');
    if (tab === 'regression') params.set('tab', 'regression');
    if (tab === 'standalone') params.set('tab', 'standalone');
    return params;
  };

  const handleSelect = (series: MacroSeries | null) => {
    setSelected(series);
    if (series) {
      const params = withActiveTab(new URLSearchParams());
      if (compareId) {
        params.set('compare', compareId);
        if (compareKind === 'instrument') params.set('compareKind', 'instrument');
      }
      const qs = params.toString();
      navigate(`/dashboard/macro/${series.series_id}${qs ? `?${qs}` : ''}`);
    } else {
      const qs = withActiveTab(new URLSearchParams()).toString();
      navigate(`/dashboard/macro${qs ? `?${qs}` : ''}`);
    }
  };

  const handleCompareSelect = (ref: DashboardSeriesRef | null) => {
    setCompareRef(ref);
    if (!seriesId) return;

    const params = withActiveTab(new URLSearchParams(searchParams));
    if (ref) {
      params.set('compare', ref.id);
      params.set('compareKind', ref.source === 'instrument' ? 'instrument' : 'macro');
    } else {
      params.delete('compare');
      params.delete('compareKind');
    }
    setSearchParams(params);
  };

  const compareSeries: MacroCompareSeries | null =
    compareRef && compareObservations.length > 0
      ? {
          seriesId: compareRef.id,
          title: compareRef.label,
          observations: compareObservations,
          color: COMPARE_COLOR,
        }
      : null;

  const rangeLabel =
    dateRange.preset === 'MAX' && !dateRange.start
      ? 'MAX'
      : [dateRange.start, dateRange.end].filter(Boolean).join(' → ');

  const rangeParams = toApiRange(dateRange);
  const compareMeta = computeMacroCompareMeta(
    observations,
    compareObservations.length > 0 ? compareObservations : undefined,
    rangeParams,
  );
  const chartSubtitle =
    compareMeta && selected
      ? formatMacroCompareSubtitle(
          selected.series_id,
          compareMeta,
          compareRef?.id,
          rangeLabel,
        )
      : selected
        ? `${selected.series_id} · ${selected.title} · ${observations.length} observations · ${rangeLabel}`
        : '';

  const compareSelected = compareRef;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <p className="text-xs text-slate-500 mb-1">Primary series (FRED macro)</p>
          <MacroSeriesSearch selected={selected} onSelect={handleSelect} />
        </div>
        <div>
          <p className="text-xs text-slate-500 mb-1">Compare (optional)</p>
          <UnifiedSeriesSearch
            selected={compareSelected}
            onSelect={handleCompareSelect}
            placeholder="Macro, stock, ETF, or crypto"
          />
        </div>
      </div>

      <DateRangeControls value={dateRange} onChange={setDateRange} mode="date" />

      {error && (
        <ErrorAlert message={error}>
          <Link to="/ingestion/fred" className="text-brand-500 underline text-sm mt-1 inline-block">
            Go to FRED Macro Ingestion
          </Link>
          <Link
            to="/ingestion/market"
            className="text-brand-500 underline text-sm mt-1 inline-block ml-3"
          >
            Market Data
          </Link>
        </ErrorAlert>
      )}

      {loading && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}

      {!loading && seriesId && observations.length > 0 && selected && (
        <div className="space-y-2">
          <p className="text-xs text-slate-500">{chartSubtitle}</p>
          <MacroTimelineChart
            observations={observations}
            seriesId={selected.series_id}
            seriesTitle={selected.title}
            compareSeries={compareSeries}
          />
        </div>
      )}

      {!loading && !seriesId && (
        <div className="text-center py-16 text-slate-500 text-sm border border-dashed border-slate-800 rounded-lg">
          Search and select a macro series to view its timeline chart.
        </div>
      )}
    </div>
  );
}

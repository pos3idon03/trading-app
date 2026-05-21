import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ingestionApi } from '../../api/endpoints';
import type { MacroObservation, MacroSeries } from '../../api/types';
import ErrorAlert from '../../components/ErrorAlert';
import MacroSeriesSearch from '../../components/MacroSeriesSearch';
import Spinner from '../../components/Spinner';
import MacroTimelineChart from '../../components/charts/MacroTimelineChart';

export default function MacroDashboardPage() {
  const { seriesId } = useParams<{ seriesId?: string }>();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<MacroSeries | null>(null);
  const [observations, setObservations] = useState<MacroObservation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

    Promise.all([
      ingestionApi.listMacroSeries(),
      ingestionApi.macroObservations(seriesId, { limit: 500, order: 'asc' }),
    ])
      .then(([catalog, data]) => {
        if (cancelled) return;
        const match = catalog.find((s) => s.series_id === seriesId.toUpperCase());
        setSelected(
          match ?? {
            series_id: seriesId.toUpperCase(),
            title: seriesId.toUpperCase(),
            category: 'general',
            is_enabled: false,
          },
        );
        setObservations(data.observations);
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load macro observations. Backfill this series from Ingestion.');
          setObservations([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [seriesId]);

  const handleSelect = (series: MacroSeries | null) => {
    setSelected(series);
    if (series) {
      navigate(`/dashboard/macro/${series.series_id}`);
    } else {
      navigate('/dashboard/macro');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Macro Dashboard</h1>
        <p className="text-slate-400 text-sm mt-1">
          Select a FRED macro series to view its historical timeline.
        </p>
      </div>

      <MacroSeriesSearch selected={selected} onSelect={handleSelect} />

      {error && (
        <ErrorAlert message={error}>
          <Link to="/ingestion/fred" className="text-brand-500 underline text-sm mt-1 inline-block">
            Go to FRED Macro Ingestion
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
          <p className="text-xs text-slate-500">
            {selected.series_id} · {selected.title} · {observations.length} observations
          </p>
          <MacroTimelineChart observations={observations} seriesId={selected.series_id} />
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

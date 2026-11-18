import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { REFRESH_INTERVAL, USE_MOCK_DATA } from '../constants/config';
import { getEvents } from '../services/eventService';
import { getImdWarnings } from '../services/imdWarningService';
import { enrichEvents, summarizeImd } from '../services/riskService';

/**
 * One hook feeds every page:
 *   events  -> backend events, enriched with today's IMD district alerts
 *   imd     -> raw IMD warning list + loading/error state + summary counts
 * IMD failing never blocks events (and vice-versa).
 */
export function useWeatherData() {
  const [rawEvents, setRawEvents] = useState([]);
  const [mode, setMode] = useState(USE_MOCK_DATA ? 'demo' : 'live');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);

  const [imdWarnings, setImdWarnings] = useState([]);
  const [imdLoading, setImdLoading] = useState(!USE_MOCK_DATA);
  const [imdError, setImdError] = useState('');
  const [imdUpdatedAt, setImdUpdatedAt] = useState(null);

  const inFlight = useRef(false);
  const lastUpdatedRef = useRef(null);

  const refresh = useCallback(async (initial = false) => {
    if (inFlight.current) return;
    inFlight.current = true;
    if (initial || !lastUpdatedRef.current) setLoading(true);
    else setRefreshing(true);

    const eventsJob = getEvents();
    const imdJob = USE_MOCK_DATA ? Promise.resolve(null) : getImdWarnings({ limit: 756 });
    setImdLoading(!USE_MOCK_DATA);

    const [eventsResult, imdResult] = await Promise.allSettled([eventsJob, imdJob]);

    if (eventsResult.status === 'fulfilled') {
      setRawEvents(eventsResult.value.events);
      setMode(eventsResult.value.mode);
      setError('');
      const updated = new Date();
      lastUpdatedRef.current = updated;
      setLastUpdated(updated);
    } else {
      setError(eventsResult.reason?.message || 'Could not load events.');
    }

    if (imdResult.status === 'fulfilled') {
      if (imdResult.value) {
        setImdWarnings(imdResult.value.warnings);
        setImdUpdatedAt(new Date());
      }
      setImdError('');
    } else {
      setImdError(imdResult.reason?.message || 'Unable to fetch IMD warnings');
    }

    inFlight.current = false;
    setLoading(false);
    setRefreshing(false);
    setImdLoading(false);
  }, []);

  useEffect(() => {
    refresh(true);
    const id = window.setInterval(() => refresh(false), REFRESH_INTERVAL);
    return () => window.clearInterval(id);
  }, [refresh]);

  const events = useMemo(() => enrichEvents(rawEvents, imdWarnings), [rawEvents, imdWarnings]);
  const imdSummary = useMemo(() => summarizeImd(imdWarnings), [imdWarnings]);

  return {
    events, mode, loading, refreshing, error, lastUpdated,
    imd: { warnings: imdWarnings, loading: imdLoading, error: imdError, updatedAt: imdUpdatedAt, summary: imdSummary },
    refresh: () => refresh(false)
  };
}

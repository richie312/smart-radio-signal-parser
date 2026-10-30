import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Dispatch, ReactNode, SetStateAction } from 'react';
import L from 'leaflet';
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { api, ApiError, classifyReception, makeTimeWindow } from '../api';
import type { AnalyticsSummary, AnalyticsTimeseries, AudioConfig, AircraftSummary, SiteLocation, SystemStatus } from '../contracts';
import { testAircraft, testAudio, testStatus, testSummary, testTimeseries } from '../testData';

type LoadState<T> = { value: T | null; loading: boolean; error: ApiError | null };
const testMode = new URLSearchParams(window.location.search).get('testData') === '1';

function useDashboardData() {
  const [status, setStatus] = useState<LoadState<SystemStatus>>(() => ({ value: testMode ? testStatus : null, loading: !testMode, error: null }));
  const [aircraft, setAircraft] = useState<LoadState<AircraftSummary[]>>(() => ({ value: testMode ? testAircraft : null, loading: !testMode, error: null }));
  const [summary, setSummary] = useState<LoadState<AnalyticsSummary>>(() => ({ value: testMode ? testSummary : null, loading: !testMode, error: null }));
  const [series, setSeries] = useState<LoadState<AnalyticsTimeseries>>(() => ({ value: testMode ? testTimeseries : null, loading: !testMode, error: null }));
  const [audio, setAudio] = useState<LoadState<AudioConfig>>(() => ({ value: testMode ? testAudio : null, loading: !testMode, error: null }));
  const [refreshKey, setRefreshKey] = useState(0);
  const [timeHours, setTimeHours] = useState(1);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState<ApiError | null>(null);

  const refresh = useCallback(() => setRefreshKey((n) => n + 1), []);
  const loadMore = useCallback(async () => {
    if (!nextCursor || testMode) return;
    setLoadingMore(true); setMoreError(null);
    try {
      const page = await api.aircraft(new URLSearchParams({ limit: '50', cursor: nextCursor }));
      setAircraft((current) => ({ ...current, value: [...(current.value ?? []), ...page.items] }));
      setNextCursor(page.next_cursor);
    } catch (error) {
      setMoreError(error instanceof ApiError ? error : new ApiError('Could not load the next page.'));
    } finally { setLoadingMore(false); }
  }, [nextCursor]);
  useEffect(() => {
    if (testMode) return;
    const controller = new AbortController();
    const setStart = <T,>(setter: Dispatch<SetStateAction<LoadState<T>>>) => setter((v) => ({ ...v, loading: true, error: null }));
    const setSuccess = <T,>(setter: Dispatch<SetStateAction<LoadState<T>>>, value: T) => setter({ value, loading: false, error: null });
    const setFailure = <T,>(setter: Dispatch<SetStateAction<LoadState<T>>>, error: unknown) => {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      setter((v) => ({ ...v, loading: false, error: error instanceof ApiError ? error : new ApiError('Unexpected request error.') }));
    };
    const window = makeTimeWindow(timeHours);
    setStart(setStatus); setStart(setAircraft); setStart(setSummary); setStart(setSeries); setStart(setAudio);
    api.status(controller.signal).then((v) => setSuccess(setStatus, v)).catch((e) => setFailure(setStatus, e));
    setNextCursor(null);
    api.aircraft(new URLSearchParams({ limit: '50' }), controller.signal).then((v) => {
      setNextCursor(v.next_cursor);
      setSuccess(setAircraft, v.items);
    }).catch((e) => setFailure(setAircraft, e));
    api.summary(window.from, window.to, controller.signal).then((v) => setSuccess(setSummary, v)).catch((e) => setFailure(setSummary, e));
    api.timeseries(window.from, window.to, Math.max(60, Math.floor(timeHours * 60)), controller.signal).then((v) => setSuccess(setSeries, v)).catch((e) => setFailure(setSeries, e));
    api.audio(controller.signal).then((v) => setSuccess(setAudio, v)).catch((e) => setFailure(setAudio, e));
    return () => controller.abort();
  }, [refreshKey, timeHours]);

  useEffect(() => {
    if (testMode) return;
    const timer = window.setInterval(refresh, 15_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  // Browsers throttle timers and suspend network activity while a laptop sleeps
  // or a tab is in the background. Refresh as soon as the dashboard is visible
  // again instead of waiting for the next throttled interval.
  useEffect(() => {
    if (testMode) return;
    const refreshWhenActive = () => {
      if (document.visibilityState === 'visible') refresh();
    };
    document.addEventListener('visibilitychange', refreshWhenActive);
    window.addEventListener('pageshow', refreshWhenActive);
    window.addEventListener('online', refreshWhenActive);
    return () => {
      document.removeEventListener('visibilitychange', refreshWhenActive);
      window.removeEventListener('pageshow', refreshWhenActive);
      window.removeEventListener('online', refreshWhenActive);
    };
  }, [refresh]);
  return { status, aircraft, summary, series, audio, refresh, timeHours, setTimeHours, nextCursor, loadMore, loadingMore, moreError };
}

function formatTime(value: string | null | undefined): string {
  if (!value) return 'Not available';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Unknown time' : `${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })} · ${date.toLocaleDateString()}`;
}
function relativeAge(value: string | null | undefined): string {
  if (!value) return 'No message received';
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (!Number.isFinite(seconds)) return 'Time unavailable';
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}
function numberOrDash(value: number | null, unit = ''): string { return value === null || !Number.isFinite(value) ? '—' : `${new Intl.NumberFormat().format(value)}${unit}`; }
function safeMediaUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  try {
    const parsed = new URL(value, window.location.origin);
    return parsed.protocol === 'https:' || parsed.origin === window.location.origin ? parsed.href : null;
  } catch { return null; }
}
function stateText(state?: string | null): string { return state ? state.replaceAll('_', ' ') : 'unknown'; }
function StatePill({ state }: { state: string }) { return <span className={`state-pill state-${state}`}><span aria-hidden="true" className="state-dot" />{stateText(state)}</span>; }

const receiverMarkerIcon = L.divIcon({ className: 'map-div-icon', html: '<span class="receiver-marker">⌖</span>', iconSize: [34, 34], iconAnchor: [17, 17] });
function aircraftMarkerIcon(track: number | null) {
  const rotation = track !== null && Number.isFinite(track) ? `transform:rotate(${track}deg)` : '';
  return L.divIcon({ className: 'map-div-icon', html: `<span class="aircraft-marker" style="${rotation}">▲</span>`, iconSize: [28, 28], iconAnchor: [14, 14] });
}

function MapViewport({ points, pointsKey }: { points: [number, number][]; pointsKey: string }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 1) map.setView(points[0], 10, { animate: false });
    else if (points.length > 1) map.fitBounds(L.latLngBounds(points).pad(0.16), { maxZoom: 10, animate: false });
  }, [map, pointsKey]);
  return null;
}

type BrowserLocation = { latitude: number; longitude: number; accuracy_m: number | null };

function useBrowserLocation(): BrowserLocation | null {
  const [location, setLocation] = useState<BrowserLocation | null>(null);
  useEffect(() => {
    if (!navigator.geolocation) return;
    const watchId = navigator.geolocation.watchPosition(
      ({ coords }) => setLocation({ latitude: coords.latitude, longitude: coords.longitude, accuracy_m: Number.isFinite(coords.accuracy) ? coords.accuracy : null }),
      () => { /* Keep GPSD data if browser location is denied or unavailable. */ },
      { enableHighAccuracy: true, maximumAge: 30_000, timeout: 20_000 },
    );
    return () => navigator.geolocation.clearWatch(watchId);
  }, []);
  return location;
}

function FlightMap({ rows, site, browserLocation }: { rows: AircraftSummary[] | null; site: SiteLocation | undefined; browserLocation: BrowserLocation | null }) {
  const serverHasFix = site?.state === 'online' && Number.isFinite(site.latitude) && Number.isFinite(site.longitude);
  const usingBrowserLocation = !serverHasFix && browserLocation !== null;
  const sitePosition: [number, number] | null = serverHasFix
    ? [site!.latitude as number, site!.longitude as number]
    : browserLocation ? [browserLocation.latitude, browserLocation.longitude] : null;
  const locationAccuracy = serverHasFix ? site?.accuracy_m : browserLocation?.accuracy_m;
  const flights = useMemo(() => (rows ?? []).filter((aircraft) => Date.now() - new Date(aircraft.last_seen_at).getTime() <= 15 * 60_000).flatMap((aircraft) => {
    const observation = aircraft.last_observation;
    const lat = observation.latitude_deg;
    const lon = observation.longitude_deg;
    return lat !== null && lon !== null && Number.isFinite(lat) && Number.isFinite(lon)
      ? [{ aircraft, observation, position: [lat, lon] as [number, number] }]
      : [];
  }), [rows]);
  const points = useMemo(() => [...(sitePosition ? [sitePosition] : []), ...flights.map((flight) => flight.position)], [sitePosition?.[0], sitePosition?.[1], flights]);
  const pointsKey = points.map(([lat, lon]) => `${lat.toFixed(4)},${lon.toFixed(4)}`).join('|');
  const fixLabel = usingBrowserLocation
    ? `Laptop location · accuracy ${locationAccuracy == null ? 'unavailable' : `±${Math.round(locationAccuracy)} m`}`
    : site?.state === 'online'
    ? `GPS fix · ${site.satellites_used ?? 0} satellites used`
    : site?.state === 'no_fix'
      ? `GPS has no fix · ${site.satellites_visible ?? 0} visible, ${site.satellites_used ?? 0} used`
      : 'Waiting for GPS fix';

  return <section className="panel map-panel" aria-labelledby="map-heading">
    <div className="map-heading">
      <div><span className="eyebrow">LIVE POSITIONS</span><h2 id="map-heading">Receiver and aircraft map</h2></div>
      <div className="map-legend"><span><i className="map-legend-site" />{usingBrowserLocation ? 'Laptop location' : 'Your receiver'}</span><span><i className="map-legend-aircraft" />Aircraft</span></div>
    </div>
    <div className="map-status"><StatePill state={usingBrowserLocation ? 'online' : site?.state ?? 'offline'} /><span>{fixLabel}</span><span>{flights.length} aircraft with positions in the last 15 minutes</span></div>
    {points.length ? <div className="map-frame">
      <MapContainer center={points[0]} zoom={7} scrollWheelZoom className="flight-map">
        <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>' />
        <MapViewport points={points} pointsKey={pointsKey} />
        {sitePosition && <Marker position={sitePosition} icon={receiverMarkerIcon}><Popup><strong>{usingBrowserLocation ? 'Laptop location' : 'Your receiver'}</strong><br />{locationAccuracy == null ? 'Accuracy unavailable' : `±${locationAccuracy.toFixed(1)} m accuracy`}</Popup></Marker>}
        {flights.map(({ aircraft, observation, position }) => <Marker key={aircraft.icao24} position={position} icon={aircraftMarkerIcon(observation.track_deg)}>
          <Popup><strong>{observation.callsign?.trim() || 'Unknown callsign'}</strong><br />{aircraft.icao24.toUpperCase()}<br />{observation.altitude_ft == null ? 'Altitude unavailable' : `${Math.round(observation.altitude_ft).toLocaleString()} ft`}</Popup>
        </Marker>)}
      </MapContainer>
    </div> : <div className="map-empty"><span className="map-empty-crosshair" aria-hidden="true">⌖</span><strong>No live positions to plot</strong><span>{fixLabel}. Aircraft markers appear when position reports arrive.</span></div>}
    <div className="map-footer"><span>Map data © OpenStreetMap contributors</span><a href="https://www.openstreetmap.org/fixthemap" target="_blank" rel="noreferrer">Report a map issue</a></div>
  </section>;
}

function ErrorNotice({ error, onRetry, compact = false }: { error: ApiError | null; onRetry: () => void; compact?: boolean }) {
  if (!error) return null;
  return <div className={`error-notice ${compact ? 'compact' : ''}`} role="alert">
    <div><strong>{error.code.replaceAll('_', ' ')}</strong><p>{error.message}</p>{error.requestId && <small>Request ID: {error.requestId}</small>}</div>
    <button className="button button-small" onClick={onRetry}>Retry</button>
  </div>;
}
function LoadingLine({ label }: { label: string }) { return <div className="loading-line" role="status"><span className="spinner" aria-hidden="true" />{label}</div>; }
function Empty({ children }: { children: ReactNode }) { return <div className="empty-state"><span className="empty-mark" aria-hidden="true">—</span><p>{children}</p></div>; }

function Header({ status, lastUpdated, refresh, test }: { status: SystemStatus | null; lastUpdated: string; refresh: () => void; test: boolean }) {
  const reception = classifyReception(status);
  return <header className="topbar">
    <a className="brand" href="#top" aria-label="Northstar ADS-B Monitor home"><span className="brand-icon" aria-hidden="true">N</span><span><strong>NORTHSTAR</strong><small>ADS-B MONITOR</small></span></a>
    <div className="topbar-right">
      <div className="global-indicator"><StatePill state={reception.state} /><span className="topbar-time">Updated {lastUpdated}</span></div>
      <button className="icon-button" onClick={refresh} aria-label="Refresh dashboard" title="Refresh dashboard">↻</button>
    </div>
    {test && <div className="test-banner" role="status"><span aria-hidden="true">⚠</span> TEST DATA — NOT LIVE RECEPTION <span className="test-subtitle">Fixtures are enabled by ?testData=1</span></div>}
  </header>;
}

function ReceiverCard({ status, loading, error, refresh }: { status: SystemStatus | null; loading: boolean; error: ApiError | null; refresh: () => void }) {
  const reception = classifyReception(status);
  const owner = status?.receiver.details.owner;
  const decoderName = status?.decoder.details.name;
  return <section className="panel receiver-panel" aria-labelledby="receiver-heading">
    <div className="panel-heading"><div><span className="eyebrow">SYSTEM OVERVIEW</span><h2 id="receiver-heading">Receiver status</h2></div><span className="live-badge"><i aria-hidden="true" /> {status?.operating_mode === 'adsb' ? status.receiver.state.toUpperCase() : 'STANDBY'}</span></div>
    <ErrorNotice error={error} onRetry={refresh} compact />
    {loading && !status ? <LoadingLine label="Connecting to receiver status…" /> : status ? <>
      <div className="receiver-status-row"><StatePill state={reception.state} /><span className="receiver-status-label">{reception.label}</span></div>
      <div className="receiver-grid">
        <div className="receiver-metric"><span className="metric-label">OPERATING MODE</span><strong>{status.operating_mode === 'adsb' ? 'ADS-B' : status.operating_mode === 'aviation_audio' ? 'Airband audio' : 'SDR++ Scanner'}</strong><small>{status.operating_mode === 'adsb' ? 'Decoder owns RTL-SDR' : 'ADS-B reception inactive'}</small></div>
        <div className="receiver-metric"><span className="metric-label">DEVICE OWNER</span><strong>{owner === 'adsb_decoder' ? 'ADS-B decoder' : owner === 'sdrpp_scanner' ? 'SDR++ scanner' : 'None reported'}</strong><small>Exclusive USB access</small></div>
        <div className="receiver-metric"><span className="metric-label">DECODER</span><strong>{typeof decoderName === 'string' ? decoderName : 'Not configured'}</strong><small><StatePill state={status.decoder.state} /></small></div>
        <div className="receiver-metric"><span className="metric-label">LAST MESSAGE</span><strong>{relativeAge(reception.lastMessage)}</strong><small>{formatTime(reception.lastMessage)}</small></div>
      </div>
      <div className="component-strip" aria-label="Service health">
        {[['API', status.api.state], ['Database', status.database.state], ['Ingestion', status.ingestion.state]].map(([name, state]) => <div key={name}><span>{name}</span><StatePill state={state as string} /></div>)}
      </div>
    </> : <Empty>Receiver status is not available yet. The API may still be starting.</Empty>}
  </section>;
}

function StatCard({ label, value, unit, icon, detail, loading, error }: { label: string; value: string; unit?: string; icon: string; detail: string; loading: boolean; error: ApiError | null }) {
  return <article className="stat-card"><div className="stat-top"><span>{label}</span><span className="stat-icon" aria-hidden="true">{icon}</span></div>
    <div className="stat-value">{loading && value === '—' ? <span className="skeleton-value" aria-label="Loading" /> : value}<small>{unit}</small></div>
    <div className="stat-detail">{error ? 'Metric unavailable' : detail}</div>
  </article>;
}

function AnalyticsPanel({ summary, series, loading, error, timeHours, setTimeHours }: { summary: AnalyticsSummary | null; series: AnalyticsTimeseries | null; loading: boolean; error: ApiError | null; timeHours: number; setTimeHours: (hours: number) => void }) {
  const values = (series?.buckets ?? []).map((bucket) => bucket.decoded_frame_count ?? bucket.aircraft_update_count);
  const max = Math.max(1, ...values);
  return <section className="panel analytics-panel" aria-labelledby="analytics-heading">
    <div className="panel-heading analytics-heading"><div><span className="eyebrow">RECEPTION ANALYTICS</span><h2 id="analytics-heading">Traffic summary</h2></div>
      <label className="select-label">Time window <select value={timeHours} onChange={(event) => setTimeHours(Number(event.target.value))}><option value={1}>Last hour</option><option value={6}>Last 6 hours</option><option value={24}>Last 24 hours</option></select></label>
    </div>
    <ErrorNotice error={error} onRetry={() => setTimeHours(timeHours)} compact />
    <div className="analytics-stats">
      <div><span>Aircraft observed</span><strong>{summary ? numberOrDash(summary.aircraft_count) : '—'}</strong><small>Distinct in selected window</small></div>
      <div><span>Decoded messages</span><strong>{summary?.message_count === null || !summary ? '—' : numberOrDash(summary.message_count)}</strong><small>{summary?.message_metrics_available ? `${numberOrDash(summary.message_rate_per_second)} msg/s` : 'Frame metric unavailable'}</small></div>
      <div><span>Aircraft updates</span><strong>{summary ? numberOrDash(summary.aircraft_update_count) : '—'}</strong><small>{summary ? `${numberOrDash(summary.position_update_count)} position updates` : 'Waiting for data'}</small></div>
      <div><span>Minimum observed range</span><strong>{summary?.distance.minimum_observed_m == null ? '—' : `${(summary.distance.minimum_observed_m / 1000).toFixed(1)}`}<small>{summary?.distance.minimum_observed_m == null ? '' : ' km'}</small></strong><small>Sparse samples may miss closest approach</small></div>
    </div>
    <div className="chart-header"><div><strong>Message activity</strong><span> · {series?.bucket_seconds ? `per ${Math.round(series.bucket_seconds / 60)} min` : 'bucketed'}</span></div><small>{summary?.window ? `${formatTime(summary.window.from)} — ${formatTime(summary.window.to)}` : 'Selected time range'}</small></div>
    {loading && !series ? <LoadingLine label="Loading analytics…" /> : series?.data_available && values.length ? <div className="chart-wrap" role="img" aria-label={`Reception activity chart with ${values.length} buckets; values are ${summary?.message_metrics_available ? 'decoded frames' : 'aircraft updates'}`}>
      <div className="bar-chart">{values.map((value, index) => <div className="bar-column" key={`${series.buckets[index]?.bucket_start}-${index}`} title={`${formatTime(series.buckets[index]?.bucket_start)}: ${value}`}><span className="bar-value">{value}</span><div className="bar" style={{ height: `${Math.max(4, (value / max) * 100)}%` }} /><small>{new Date(series.buckets[index]?.bucket_start ?? '').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</small></div>)}</div>
      <div className="chart-footer"><span><i className="legend-dot" />{summary?.message_metrics_available ? 'Decoded frames' : 'Aircraft updates (frame count unavailable)'}</span><span>Distinct aircraft per bucket: shown in API</span></div>
    </div> : <Empty>{error ? 'Analytics are unavailable because the request failed.' : 'No reception data in this time window.'}</Empty>}
    {summary?.signal_metrics?.length ? <div className="signal-list"><strong>Receiver-reported signal metrics</strong>{summary.signal_metrics.map((metric, index) => <span key={`${metric.kind}-${index}`}>{metric.kind}: {numberOrDash(metric.value)} {metric.unit} · {metric.calibration_status ?? 'calibration unspecified'}</span>)}</div> : <div className="muted-footnote">Signal measurements are shown only when reported by the receiver or decoder.</div>}
  </section>;
}

function AircraftTable({ rows, loading, error, refresh, selected, onSelect, status, nextCursor, loadMore, loadingMore, moreError }: { rows: AircraftSummary[] | null; loading: boolean; error: ApiError | null; refresh: () => void; selected: AircraftSummary | null; onSelect: (row: AircraftSummary | null) => void; status: SystemStatus | null; nextCursor: string | null; loadMore: () => void; loadingMore: boolean; moreError: ApiError | null }) {
  const [filter, setFilter] = useState('');
  const [callsign, setCallsign] = useState('');
  const filtered = useMemo(() => (rows ?? []).filter((row) => row.icao24.toLowerCase().includes(filter.trim().toLowerCase()) || (row.last_observation.callsign ?? '').toLowerCase().includes(filter.trim().toLowerCase())).filter((row) => !callsign || (row.last_observation.callsign ?? '').toLowerCase().includes(callsign.toLowerCase())), [rows, filter, callsign]);
  const hasReception = status?.operating_mode === 'adsb' && status.receiver.state === 'online';
  return <section className="panel aircraft-panel" aria-labelledby="aircraft-heading">
    <div className="panel-heading aircraft-heading"><div><span className="eyebrow">LIVE TRAFFIC</span><h2 id="aircraft-heading">Aircraft nearby <span className="count-chip">{rows?.length ?? 0}</span></h2></div><span className="table-note">Most recently observed first</span></div>
    <div className="table-tools"><label className="search-label"><span className="sr-only">Filter by ICAO24 or callsign</span><span aria-hidden="true">⌕</span><input value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Filter ICAO24 or callsign" /></label><label className="callsign-filter"><span className="sr-only">Filter by callsign</span><input value={callsign} onChange={(event) => setCallsign(event.target.value)} placeholder="Calls…" /></label></div>
    <ErrorNotice error={error} onRetry={refresh} />
    {loading && !rows ? <LoadingLine label="Loading aircraft…" /> : rows && filtered.length ? <>
      <div className="table-scroll"><table><thead><tr><th scope="col">AIRCRAFT</th><th scope="col">LAST SEEN</th><th scope="col">ALTITUDE</th><th scope="col">SPEED</th><th scope="col">TRACK</th><th scope="col">POSITION</th><th scope="col"><span className="sr-only">Details</span></th></tr></thead>
        <tbody>{filtered.map((row) => {
          const observation = row.last_observation;
          const position = observation.latitude_deg !== null && observation.longitude_deg !== null;
          const stale = status?.receiver.state === 'degraded' || status?.receiver.state === 'offline';
          return <tr key={row.icao24} className={selected?.icao24 === row.icao24 ? 'selected-row' : ''}>
            <td><button className="aircraft-link" onClick={() => onSelect(selected?.icao24 === row.icao24 ? null : row)} aria-expanded={selected?.icao24 === row.icao24}><strong>{observation.callsign?.trim() || 'Unknown callsign'}</strong><small>{row.icao24.toUpperCase()}</small></button></td>
            <td><span className="last-seen">{relativeAge(row.last_seen_at)}</span><small className="cell-sub">{formatTime(row.last_seen_at)}</small></td>
            <td>{numberOrDash(observation.altitude_ft, ' ft')}</td><td>{numberOrDash(observation.ground_speed_kt, ' kt')}</td><td>{numberOrDash(observation.track_deg, '°')}</td>
            <td><StatePill state={!position ? 'unconfigured' : stale ? 'degraded' : 'online'} /><small className="cell-sub">{!position ? 'No position' : stale ? 'Receiver stale' : `${observation.latitude_deg?.toFixed(2)}, ${observation.longitude_deg?.toFixed(2)}`}</small></td>
            <td><button className="row-action" onClick={() => onSelect(selected?.icao24 === row.icao24 ? null : row)} aria-label={`View details for ${row.icao24}`}>→</button></td>
          </tr>;
        })}</tbody></table></div>
      {selected && <AircraftDetail aircraft={selected} onClose={() => onSelect(null)} />}
    </> : <Empty>{rows?.length === 0 && !hasReception ? `No aircraft currently listed. ${status?.operating_mode === 'sdrpp_scanner' ? 'The scanner owns the receiver, so ADS-B reception is inactive.' : status?.operating_mode === 'aviation_audio' ? 'Airband audio owns the receiver, so ADS-B updates are paused.' : 'Check receiver health and last message time above.'}` : 'No aircraft match these filters.'}</Empty>}
    <ErrorNotice error={moreError} onRetry={loadMore} compact />
    <div className="table-footer"><span>Showing {filtered.length} of {rows?.length ?? 0} loaded aircraft</span><span className="footer-actions">{nextCursor && <button className="text-button" onClick={loadMore} disabled={loadingMore}>{loadingMore ? 'Loading…' : 'Load more'}</button>}<button className="text-button" onClick={refresh}>Refresh <span aria-hidden="true">↻</span></button></span></div>
  </section>;
}

function AircraftDetail({ aircraft, onClose }: { aircraft: AircraftSummary; onClose: () => void }) {
  const observation = aircraft.last_observation;
  const imageUrl = safeMediaUrl(aircraft.image?.data?.image_url);
  const flight = aircraft.flight_info;
  return <aside className="detail-panel" aria-label={`Details for aircraft ${aircraft.icao24}`}>
    <div className="detail-header"><div><span className="eyebrow">OBSERVED AIRCRAFT</span><h3>{observation.callsign?.trim() || 'Unknown callsign'} <span>{aircraft.icao24}</span></h3></div><button className="icon-button close-button" onClick={onClose} aria-label="Close aircraft details">×</button></div>
    <div className="detail-grid"><div><span>Altitude</span><strong>{numberOrDash(observation.altitude_ft, ' ft')}</strong></div><div><span>Ground speed</span><strong>{numberOrDash(observation.ground_speed_kt, ' kt')}</strong></div><div><span>Track</span><strong>{numberOrDash(observation.track_deg, '°')}</strong></div><div><span>Vertical rate</span><strong>{numberOrDash(observation.vertical_rate_fpm, ' fpm')}</strong></div><div><span>Observed time</span><strong>{formatTime(observation.event_time ?? observation.ingested_at)}</strong></div><div><span>Record kind</span><strong>{observation.record_kind.replace('_', ' ')}</strong></div></div>
    <div className="provenance-block"><h4>Flight enrichment <span className="provenance-tag">EXTERNAL · {stateText(flight?.state)}</span></h4>
      {flight?.data ? <><p className="route-line">{flight.data.origin ?? 'Unknown'} <span aria-hidden="true">→</span> {flight.data.destination ?? 'Unknown'}</p><p>Provider: {flight.provider_id ?? 'Not identified'} · Retrieved {formatTime(flight.fetched_at)}</p><p>Match confidence: {flight.match_confidence === null ? 'Unspecified' : `${Math.round(flight.match_confidence * 100)}%`}</p></> : <p>No external flight match available. Local observations remain available independently.</p>}
    </div>
    <div className="provenance-block"><h4>Aircraft image <span className="provenance-tag">EXTERNAL · {stateText(aircraft.image?.state)}</span></h4>
      {imageUrl ? <figure className="aircraft-image"><img src={imageUrl} alt={`External aircraft image for ${aircraft.icao24}`} referrerPolicy="no-referrer" /><figcaption>{aircraft.image.attribution ?? aircraft.image.data?.attribution ?? 'Attribution unavailable'}{aircraft.image.data?.license ? ` · ${aircraft.image.data.license}` : ''}</figcaption></figure> : <p>No verified image available.</p>}
    </div>
    <p className="provenance-footnote">Observed data is from this receiver. Route and image information is external and may be unavailable or ambiguous.</p>
  </aside>;
}

function AudioPanel({ audio, loading, error, refresh }: { audio: AudioConfig | null; loading: boolean; error: ApiError | null; refresh: () => void }) {
  const [selected, setSelected] = useState<string>('');
  const [playing, setPlaying] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(0.75);
  const audioRef = useRef<HTMLAudioElement>(null);
  const station = audio?.stations.find((item) => item.station_id === selected);
  const audioMode = audio?.mode === 'aviation_audio';
  const activeStation = audio?.station_id === selected;
  const stopCurrent = audioMode && (!selected || activeStation);
  useEffect(() => { if (audioRef.current) { audioRef.current.volume = volume; audioRef.current.muted = muted; } }, [volume, muted]);
  useEffect(() => { setPlaying(false); if (audioRef.current) { audioRef.current.pause(); audioRef.current.src = ''; } }, [selected]);
  const play = async () => {
    if (!selected || switching || !audioRef.current) return;
    setSwitching(true); setActionError(null);
    try {
      const result = await api.startAudio(selected);
      audioRef.current.src = result.playback_url;
      await audioRef.current.play();
      setPlaying(true);
      refresh();
    } catch (e) { setPlaying(false); setActionError(e instanceof Error ? e.message : 'Could not start airband audio.'); }
    finally { setSwitching(false); }
  };
  const stop = async () => {
    audioRef.current?.pause();
    if (audioRef.current) audioRef.current.src = '';
    setPlaying(false); setSwitching(true); setActionError(null);
    try { await api.stopAudio(); refresh(); }
    catch (e) { setActionError(e instanceof Error ? e.message : 'Could not restore ADS-B reception.'); }
    finally { setSwitching(false); }
  };
  return <section className="panel audio-panel" aria-labelledby="audio-heading">
    <div className="panel-heading"><div><span className="eyebrow">AVIATION AUDIO</span><h2 id="audio-heading">Station monitor</h2></div><span className="audio-icon" aria-hidden="true">♫</span></div>
    <ErrorNotice error={error} onRetry={refresh} compact />
    {loading && !audio ? <LoadingLine label="Checking audio configuration…" /> : audio?.stations.length ? <>
      <p className="audio-intro">{audio?.airport}. Starting a station pauses ADS-B on this single tuner.</p>
      <label className="station-select">Station<select value={selected} onChange={(event) => setSelected(event.target.value)}><option value="">Choose station</option>{audio.stations.map((item) => <option key={item.station_id} value={item.station_id}>{item.name}{item.frequency_mhz ? ` · ${item.frequency_mhz} MHz` : ''}</option>)}</select></label>
      {station && <div className="station-meta"><StatePill state={station.state} /><span>{station.band ?? 'Band unspecified'} · {station.modulation ?? 'Modulation unspecified'}</span></div>}
      <div className="audio-controls"><button className="listen-button" disabled={switching || (!audioMode && !selected)} onClick={stopCurrent ? stop : play}>{switching ? 'Switching receiver…' : stopCurrent ? 'Stop listening · resume ADS-B' : audioMode ? 'Switch station' : 'Start listening · pause ADS-B'}</button><label className="volume-label"><span>Volume</span><input type="range" min="0" max="1" step="0.05" value={volume} onChange={(event) => setVolume(Number(event.target.value))} aria-label="Audio volume" /></label><button className="mute-button" onClick={() => setMuted((value) => !value)} aria-pressed={muted}>{muted ? 'Unmute' : 'Mute'}</button></div>
      {!selected && !audioMode && <p className="audio-unavailable">Select a station to enable listening. ADS-B reception resumes when you stop audio.</p>}
      {audioMode && !playing && <p className="audio-unavailable">Listening mode is active. Select Play to open the live audio in this browser.</p>}
      {actionError && <p className="audio-unavailable">{actionError}</p>}
      {audio?.source && <p className="audio-unavailable">Frequency reference: <a href={audio.source} target="_blank" rel="noreferrer">AIP India</a></p>}
      <audio ref={audioRef} onEnded={() => setPlaying(false)} onError={() => setPlaying(false)} />
    </> : <div className="audio-empty"><div className="audio-wave" aria-hidden="true"><i /><i /><i /><i /><i /></div><StatePill state={audio?.state ?? 'unconfigured'} /><h3>Audio source not configured</h3><p>Live playback stays unavailable until a legitimate source and browser delivery path are verified.</p><span className="audio-frequency">NO VERIFIED STREAM</span></div>}
  </section>;
}

export default function App() {
  const data = useDashboardData();
  const browserLocation = useBrowserLocation();
  const [selected, setSelected] = useState<AircraftSummary | null>(null);
  const reception = classifyReception(data.status.value);
  const lastUpdated = data.status.value?.api.updated_at ? formatTime(data.status.value.api.updated_at) : 'Waiting';
  return <div id="top" className="app-shell">
    <Header status={data.status.value} lastUpdated={lastUpdated} refresh={data.refresh} test={testMode} />
    <main className="dashboard">
      <div className="page-title"><div><span className="eyebrow">OPERATIONS / RECEIVER 01</span><h1>Airspace overview</h1><p>Local reception, aircraft observations, and system health.</p></div><div className="page-stamp"><span className="stamp-icon" aria-hidden="true">⌖</span><span>RECEIVER STATUS<small>{reception.label}</small></span></div></div>
      <ReceiverCard status={data.status.value} loading={data.status.loading} error={data.status.error} refresh={data.refresh} />
      <section className="stat-grid" aria-label="Reception statistics">
        <StatCard label="AIRCRAFT IN WINDOW" icon="✣" value={data.summary.value ? numberOrDash(data.summary.value.aircraft_count) : '—'} detail={data.summary.value ? `Last ${data.timeHours} ${data.timeHours === 1 ? 'hour' : 'hours'}` : 'Waiting for analytics'} loading={data.summary.loading} error={data.summary.error} />
        <StatCard label="DECODED MESSAGE RATE" icon="⌁" value={data.summary.value?.message_rate_per_second == null ? '—' : data.summary.value.message_rate_per_second.toFixed(1)} unit={data.summary.value?.message_rate_per_second == null ? '' : ' msg/s'} detail={data.summary.value?.message_metrics_available ? 'From decoded frames' : 'Unavailable for current output'} loading={data.summary.loading} error={data.summary.error} />
        <StatCard label="POSITION UPDATES" icon="⌖" value={data.summary.value ? numberOrDash(data.summary.value.position_update_count) : '—'} detail="Valid observed positions" loading={data.summary.loading} error={data.summary.error} />
        <StatCard label="LAST MESSAGE" icon="◷" value={relativeAge(reception.lastMessage)} detail={reception.lastMessage ? formatTime(reception.lastMessage) : 'No message timestamp'} loading={data.status.loading} error={data.status.error} />
      </section>
      <FlightMap rows={data.aircraft.value} site={data.status.value?.site} browserLocation={browserLocation} />
      <div className="main-grid">
        <div className="main-column">
          <AircraftTable rows={data.aircraft.value} loading={data.aircraft.loading} error={data.aircraft.error} refresh={data.refresh} selected={selected} onSelect={setSelected} status={data.status.value} nextCursor={data.nextCursor} loadMore={data.loadMore} loadingMore={data.loadingMore} moreError={data.moreError} />
          <AnalyticsPanel summary={data.summary.value} series={data.series.value} loading={data.summary.loading || data.series.loading} error={data.summary.error ?? data.series.error} timeHours={data.timeHours} setTimeHours={data.setTimeHours} />
        </div>
        <aside className="side-column" aria-label="Receiver details and audio"><AudioPanel audio={data.audio.value} loading={data.audio.loading} error={data.audio.error} refresh={data.refresh} />
          <section className="panel provenance-card"><span className="eyebrow">DATA PROVENANCE</span><h2>Observed here.<br />Enriched elsewhere.</h2><p>Aircraft positions and timestamps come from the local receiver. Flight details and images are external enrichment and may be incomplete.</p><div className="provenance-legend"><span><i className="legend-local" />Local observation</span><span><i className="legend-external" />External information</span></div></section>
          <div className="backend-note"><StatePill state={data.status.value?.database.state ?? 'offline'} /><span>Database connection</span><small>{data.status.value?.database.error_code ? `Error: ${data.status.value.database.error_code}` : 'Status from API'}</small></div>
        </aside>
      </div>
      <footer className="page-footer"><span>NORTHSTAR ADS-B MONITOR <i /> BATCH 1</span><span>Refreshes every 15 seconds · All times local display, UTC API data</span></footer>
    </main>
  </div>;
}

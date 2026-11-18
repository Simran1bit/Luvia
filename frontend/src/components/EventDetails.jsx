import { useEffect, useState } from 'react';
import { X, MapPin, Clock3, ShieldCheck, ExternalLink, FileSearch, AlertTriangle, LoaderCircle } from 'lucide-react';
import { getEventDetails } from '../services/eventService';

function dateLabel(value) {
  if (!value) return 'Timestamp unavailable';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? 'Timestamp unavailable' : d.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
}

export default function EventDetails({ event, onClose, onVerify, mode = 'demo' }) {
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifyMessage, setVerifyMessage] = useState('');

  useEffect(() => {
    let cancelled = false;
    setDetail(null);
    setDetailError('');
    setVerifyMessage('');
    if (!event || mode !== 'live' || event.demo) return () => { cancelled = true; };
    setDetailLoading(true);
    getEventDetails(event.id)
      .then(result => { if (!cancelled) setDetail(result); })
      .catch(error => { if (!cancelled) setDetailError(error?.message || 'Could not load event source details.'); })
      .finally(() => { if (!cancelled) setDetailLoading(false); });
    return () => { cancelled = true; };
  }, [event?.id, mode, event?.demo]);

  if (!event) return <aside className="detail-card detail-empty"><div className="detail-empty-icon"><FileSearch size={24}/></div><h3>Select an incident</h3><p>Choose a map marker or event card to inspect its available details and evidence.</p></aside>;

  // Fresh backend detail fills in missing fields, but the enriched triage fields from the dashboard always win.
  const record = detail?.event
    ? { ...event, ...detail.event, severity: event.severity, verification_status: event.verification_status, risk_reasons: event.risk_reasons, imd_alert: event.imd_alert }
    : event;
  const sources = detail?.sources || [];
  const linkedSources = sources.filter(source => source?.source_url);
  const canVerify = mode === 'live' && !event.demo && typeof onVerify === 'function';
  async function handleVerify() {
    if (!canVerify || verifyLoading) return;
    const confirmed = window.confirm(`Run the backend verification action for event ${event.id}? This sends a POST request to your LUVIA backend.`);
    if (!confirmed) return;
    setVerifyLoading(true);
    setVerifyMessage('');
    try {
      const result = await onVerify(event);
      setVerifyMessage(typeof result === 'string' ? result : 'Verification request completed. Refreshing the event record…');
    } catch (error) {
      setVerifyMessage(`Verification failed: ${error?.message || 'Unknown error'}`);
    } finally {
      setVerifyLoading(false);
    }
  }

  return <aside className="detail-card">
    <div className="detail-top"><span className="eyebrow">INCIDENT INTELLIGENCE</span><button className="icon-button" onClick={onClose} aria-label="Close details"><X size={17}/></button></div>
    <div className="detail-visual"><div className="rain-illustration"><CloudArt/></div><span className="demo-overlay">{record.demo ? 'SYNTHETIC DEMO RECORD' : 'BACKEND EVENT RECORD'}</span></div>
    <div className="detail-title-row"><div><h2>{record.title || record.event_type}</h2><p className="detail-location"><MapPin size={14}/>{record.city || 'Location unavailable'}, {record.state || 'State unavailable'}</p></div><span className={`status-pill ${record.severity || 'unknown'}`}>{record.severity || 'unknown'}</span></div>
    <div className="detail-facts">
      <div><Clock3/><span><small>Reported time</small><strong>{dateLabel(record.timestamp)}</strong></span></div>
      <div><AlertTriangle/><span><small>Event type</small><strong>{record.event_type || 'Not provided'}</strong></span></div>
      <div><ShieldCheck/><span><small>Verification status</small><strong>{(record.verification_status || 'unknown').replaceAll('_', ' ')}</strong></span></div>
      <div><FileSearch/><span><small>Credibility score</small><strong>{record.confidence_score == null ? 'Not available' : record.confidence_score}</strong></span></div>
    </div>
    {(record.risk_reasons?.length > 0 || record.imd_alert) && <div className="risk-block"><div className="evidence-heading"><h3>Why this is flagged</h3>{record.imd_alert && <span className={`imd-pill ${record.imd_alert.color}`}>IMD {record.imd_alert.color}</span>}</div><ul>{record.risk_reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>{record.imd_alert?.description && <p className="risk-desc">{record.imd_alert.description}</p>}<small>Severity and review status are derived from official IMD district warnings and stored backend classification. They are triage signals, not confirmation.</small></div>}
    {record.description && <div className="evidence-block"><div className="evidence-heading"><h3>Description</h3></div><p>{record.description}</p></div>}
    <div className="evidence-block"><div className="evidence-heading"><h3>Evidence & sources</h3><span className="evidence-count">{linkedSources.length || record.source_url || record.evidence_url ? 'Available' : 'None linked'}</span></div>
      {detailLoading && <p className="detail-loading"><LoaderCircle size={14} className="spin"/> Loading source records…</p>}
      {detailError && <p className="detail-error">Could not load additional source details: {detailError}</p>}
      {record.source && <div className="source-row"><span className="source-avatar">S</span><span><strong>{record.source}</strong><small>Source label supplied by data</small></span></div>}
      {record.source_url && <a className="source-link" href={record.source_url} target="_blank" rel="noreferrer">Open original source <ExternalLink size={14}/></a>}
      {record.evidence_url && <a className="source-link" href={record.evidence_url} target="_blank" rel="noreferrer">Open evidence media <ExternalLink size={14}/></a>}
      {sources.map((source, index) => <div className="source-record" key={source.source_id ?? `${source.source_name || 'source'}-${index}`}>
        <strong>{source.source_name || source.source_type || 'Source record'}</strong>
        <small>Source type: {source.source_type || 'Not supplied'}{source.source_timestamp ? ` · ${dateLabel(source.source_timestamp)}` : ''}</small>
        {source.source_url ? <a className="source-link" href={source.source_url} target="_blank" rel="noreferrer">Open original source <ExternalLink size={14}/></a> : <small>No source URL supplied by the backend.</small>}
        {source.raw_content && <p>{source.raw_content}</p>}
      </div>)}
      {!record.source_url && !record.evidence_url && linkedSources.length === 0 && !sources.length && !detailLoading && <div className="no-evidence">No source URL or evidence media is available for this record.</div>}
      <p className="evidence-caveat">A linked post or video is supporting material, not automatic proof of the claimed location or event.</p>
    </div>
    <button className="primary-button full-button" onClick={handleVerify} disabled={!canVerify || verifyLoading}>{verifyLoading ? 'Submitting…' : 'Run backend verification'} {verifyLoading ? <LoaderCircle size={16} className="spin"/> : <ShieldCheck size={16}/>}</button>
    {mode === 'demo' || record.demo ? <small className="disabled-note">Verification actions are disabled for synthetic demo records.</small> : <small className="disabled-note">This sends POST /verify?event_id=… to your backend after confirmation.</small>}
    {verifyMessage && <p className="detail-verify-message" role="status">{verifyMessage}</p>}
  </aside>;
}
function CloudArt(){return <div className="cloud-scene"><span className="cloud c1"/><span className="cloud c2"/><span className="rain-line r1"/><span className="rain-line r2"/><span className="rain-line r3"/><span className="rain-line r4"/><span className="sun-glow"/></div>}

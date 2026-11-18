import { useEffect, useMemo, useState } from 'react';
import { API_BASE_URL } from '../../constants/config';
import { SEVERITY, SEVERITY_ORDER, VERIFICATION, normalizeSeverity } from '../../constants/severity';
const statusColor=(name,i)=>VERIFICATION[String(name).replaceAll(' ','_')]?.color||chartColors[i%chartColors.length];
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
const chartColors=['#3184d8','#f59e0b','#ed6269','#36a783','#a78bfa'];
export default function AnalyticsPage({events}) {
    
const [imdAnalytics, setImdAnalytics] = useState(null);
const [imdError, setImdError] = useState('');

useEffect(() => {
  let cancelled = false;

  async function loadImdAnalytics() {
    try {
      const response = await fetch(
        `${API_BASE_URL}/imd-warnings/analytics`
      );

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }

      const data = await response.json();

      if (!cancelled) {
        setImdAnalytics(data);
        setImdError('');
      }
    } catch (error) {
      if (!cancelled) {
        setImdError('IMD analytics are temporarily unavailable.');
      }
    }
  }

  loadImdAnalytics();

  return () => {
    cancelled = true;
  };
}, []);

const imdWarningCodes = useMemo(
  () =>
    Object.entries(imdAnalytics?.distinct_warning_codes || {})
      .map(([name, count]) => ({ name: `Code ${name}`, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8),
  [imdAnalytics]
);

const imdForecastDays = useMemo(
  () =>
    Object.entries(imdAnalytics?.records_by_forecast_day || {})
      .map(([day, count]) => ({ day: `Day ${day}`, count }))
      .sort((a, b) => Number(a.day.slice(4)) - Number(b.day.slice(4))),
  [imdAnalytics]
);

    const bySeverity=useMemo(()=>{const m=new Map();events.forEach(e=>{const k=normalizeSeverity(e.severity);m.set(k,(m.get(k)||0)+1)});return SEVERITY_ORDER.filter(k=>m.has(k)).map(k=>({name:SEVERITY[k].label,key:k,count:m.get(k)}))},[events]);const byType=useMemo(()=>countBy(events,e=>e.event_type||'Unknown'),[events]);const byState=useMemo(()=>countBy(events,e=>e.state||'Unknown').sort((a,b)=>b.count-a.count).slice(0,8),[events]);const byStatus=useMemo(()=>countBy(events,e=>(e.verification_status||'unknown').replaceAll('_',' ')),[events]);const byHour=useMemo(()=>{const buckets=Array.from({length:6},(_,i)=>({hour:['-24h','-20h','-16h','-12h','-8h','-4h'][i],reports:0}));events.forEach(e=>{const age=(Date.now()-new Date(e.timestamp).getTime())/3600000;if(Number.isFinite(age)&&age>=0&&age<24){ const index=Math.max(0,Math.min(5,Math.floor((24-age)/4)-1)); buckets[index].reports += 1; }});return buckets},[events]);return <div className="page-stack"><div className="page-title"><div><span className="eyebrow">WEATHER INTELLIGENCE</span><h1>Analytics overview</h1><p>Explore patterns in the currently selected event dataset.</p></div><span className="data-tag">{events.some(e=>e.demo)?'DEMO DATA':'API DATA'}</span></div>
    <div className="analytics-grid">
        <section className="panel chart-panel wide">
            <div className="panel-heading">
                <div>
                    <h2>Reports over time</h2>
                    <p>Based on available event timestamps</p>
                </div>
            </div>
            <div className="chart-area">
                <ResponsiveContainer width="100%" height="100%"><LineChart data={byHour}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="hour"/><YAxis allowDecimals={false}/><Tooltip/><Line type="monotone" dataKey="reports" stroke="#3486d9" strokeWidth={3} dot={{r:4}}/></LineChart></ResponsiveContainer>
            </div>
        </section>
        <section className="panel chart-panel">
            <div className="panel-heading">
                <div>
                    <h2>Event categories</h2>
                    <p>Reports by type</p>
                </div>
            </div>
            <div className="chart-area">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={byType} layout="vertical" margin={{left:12,right:10}}>
                        <CartesianGrid strokeDasharray="3 3" horizontal={false}/>
                        <XAxis type="number" allowDecimals={false}/>
                        <YAxis dataKey="name" type="category" width={110} tick={{fontSize:11}}/>
                        <Tooltip/>
                        <Bar dataKey="count" fill="#5a9de2" radius={[0,5,5,0]}/>
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </section>
        <section className="panel chart-panel">
            <div className="panel-heading"><div><h2>Severity mix</h2><p>Backend classification + today's IMD alerts</p></div></div>
            <div className="chart-area">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={bySeverity}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="name"/><YAxis allowDecimals={false}/><Tooltip/><Bar dataKey="count" radius={[5,5,0,0]}>{bySeverity.map(x=><Cell key={x.key} fill={SEVERITY[x.key].color}/>)}</Bar></BarChart>
                </ResponsiveContainer>
            </div>
        </section>
        <section className="panel chart-panel">
            <div className="panel-heading">
                <div>
                    <h2>Verification status</h2>
                    <p>Current record status</p>
                </div>
            </div>
            <div className="chart-area">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <Pie data={byStatus} dataKey="count" nameKey="name" cx="50%" cy="50%" outerRadius={90} innerRadius={54} paddingAngle={3}>
                            {byStatus.map((x,i)=><Cell key={x.name} fill={statusColor(x.name,i)}/>)}
                        </Pie>
                        <Tooltip/>
                    </PieChart>
                </ResponsiveContainer>
            </div>
            <div className="chart-legend">
                {byStatus.map((x,i)=><span key={x.name}><i style={{background:statusColor(x.name,i)}}/>{x.name}: {x.count}</span>)}
            </div>
        </section>
        <section className="panel chart-panel wide">
            <div className="panel-heading">
                <div>
                    <h2>Most active states</h2>
                    <p>Distinct incident IDs</p>
                </div>
            </div>
            <div className="chart-area">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={byState}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false}/>
                        <XAxis dataKey="name" interval={0} angle={-16} textAnchor="end" height={55} tick={{fontSize:10}}/>
                        <YAxis allowDecimals={false}/>
                        <Tooltip/>
                        <Bar dataKey="count" fill="#52b7a1" radius={[5,5,0,0]}/>
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </section>
        <section className="panel chart-panel wide">
        <div className="panel-heading">
            <div>
            <h2>Official IMD Warning Feed</h2>
            <p>Stored district forecasts from the India Meteorological Department</p>
            </div>
        </div>

        {imdError ? (
            <p>{imdError}</p>
        ) : !imdAnalytics ? (
            <p>Loading official warning analytics...</p>
        ) : (
            <>
            <div className="chart-legend">
                <span>
                District records: {imdAnalytics.stored_district_records}
                </span>
                <span>
                Warning codes: {imdWarningCodes.length} shown
                </span>
            </div>

            <div className="chart-area">
                <ResponsiveContainer width="100%" height="100%">
                <BarChart
                    data={imdWarningCodes}
                    layout="vertical"
                    margin={{ left: 12, right: 16 }}
                >
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" allowDecimals={false} />
                    <YAxis
                    dataKey="name"
                    type="category"
                    width={90}
                    tick={{ fontSize: 11 }}
                    />
                    <Tooltip />
                    <Bar
                    dataKey="count"
                    name="Forecast-day entries"
                    fill="#8b78d6"
                    radius={[0, 5, 5, 0]}
                    />
                </BarChart>
                </ResponsiveContainer>
            </div>
            </>
        )}
        </section>

        <section className="panel chart-panel">
        <div className="panel-heading">
            <div>
            <h2>Five-Day Forecast Coverage</h2>
            <p>Stored entries for each forecast day</p>
            </div>
        </div>

        {imdAnalytics && (
            <div className="chart-area">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={imdForecastDays}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="day" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar
                    dataKey="count"
                    name="District forecast entries"
                    fill="#36a783"
                    radius={[5, 5, 0, 0]}
                />
                </BarChart>
            </ResponsiveContainer>
            </div>
        )}
        </section>
    </div>

    <p className="page-footnote">Charts summarize the records currently loaded. They are not an official weather forecast or a claim of verified event totals.</p>

</div>}
function countBy(arr,fn){const m=new Map();arr.forEach(x=>{const name=fn(x);m.set(name,(m.get(name)||0)+1)});return [...m].map(([name,count])=>({name,count}));}
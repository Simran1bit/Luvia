import {
  Activity,
  ShieldCheck,
  Info,
  Map,
  CloudLightning,
  Menu,
  X,
  Wifi,
  WifiOff,
  ExternalLink
} from 'lucide-react';
import { useEffect, useState } from 'react';
import './styles/risk-additions.css';
import { NavLink, Route, Routes, Navigate, useLocation, useNavigate } from 'react-router-dom';
import Brand from './components/Brand';import ThemeControl from './components/ThemeControl';import LiveMapPage from './features/live-map/LiveMapPage';import AnalyticsPage from './features/analytics/AnalyticsPage';import VerificationPage from './features/verification/VerificationPage';import { useWeatherData } from './hooks/useWeatherData';import { themeForHour } from './constants/config';import { verifyEvent } from './services/verificationService';
import Chatbot from '../../Chatbot/frontend/Chatbot.jsx';
export default function App(){const [theme,setTheme]=useState(()=>themeForHour(new Date().getHours()));const [automatic,setAutomatic]=useState(true);const [selected,setSelected]=useState(null);const [mobileNav,setMobileNav]=useState(false);const data=useWeatherData();const location=useLocation();const navigate=useNavigate();useEffect(()=>{const apply=()=>{document.documentElement.dataset.theme=automatic?themeForHour(new Date().getHours()):theme};apply();if(!automatic)return;const id=window.setInterval(apply,60000);return()=>window.clearInterval(id)},[theme,automatic]);useEffect(()=>{setMobileNav(false);window.scrollTo({top:0,behavior:'smooth'})},[location.pathname]);useEffect(()=>{if(selected&&!data.events.some(e=>e.id===selected.id))setSelected(null)},[data.events,selected]);
 const handleVerify=async(event)=>{const result=await verifyEvent(event);await data.refresh();return result};const links=[{to:'/',label:'Live Map',icon:Map},{to:'/analytics',label:'Analytics',icon:Activity},{to:'/verification',label:'Verification',icon:ShieldCheck},{to:'/about',label:'About',icon:Info}];return <div className="app-shell"><header className="site-header"><div className="header-top"><Brand/><button className="mobile-menu" onClick={()=>setMobileNav(!mobileNav)} aria-label="Toggle navigation">{mobileNav?<X/>:<Menu/>}</button><nav className={`main-nav ${mobileNav?'open':''}`}>{links.map(({to,label,icon:Icon})=><NavLink key={to} to={to} end={to==='/'} className={({isActive})=>`nav-link ${isActive?'active':''}`}><Icon size={15}/>{label}</NavLink>)}</nav>
 
<div className="header-right">
  <a
    className="imd-warnings-link"
    href="https://mausam.imd.gov.in/"
    target="_blank"
    rel="noreferrer"
    title="Official India Meteorological Department weather information"
  >
    IMD Warnings <ExternalLink size={13} />
  </a>

  <span
    className={`connection-state ${data.error ? 'offline' : ''}`}
    title={data.error || 'Data service status'}
  >
    {data.error ? <WifiOff size={14} /> : <Wifi size={14} />}
    <span>
      {data.error ? 'Unavailable' : data.mode === 'demo' ? 'Demo mode' : 'API connected'}
    </span>
  </span>

  <ThemeControl
    theme={theme}
    setTheme={setTheme}
    automatic={automatic}
    setAutomatic={setAutomatic}
  />
</div>

</div><div className="header-bottom"><div className="header-copy"><span className="weather-sparkle"><CloudLightning size={17}/></span><span><strong>Weather, understood.</strong> Reports · Geography · Evidence</span></div><span className="header-tagline">A clearer view of weather incidents across India</span></div></header>
 <main className="content-shell"><Routes><Route path="/" element={<LiveMapPage events={data.events} selected={selected} setSelected={setSelected} refreshing={data.refreshing} loading={data.loading} error={data.error} lastUpdated={data.lastUpdated} onRefresh={data.refresh} mode={data.mode} onVerify={handleVerify} imd={data.imd}/>}/><Route path="/analytics" element={<AnalyticsPage events={data.events}/>}/><Route path="/verification" element={<VerificationPage events={data.events} onSelect={e=>{setSelected(e);navigate('/')}}/>}/><Route path="/about" element={<AboutPage mode={data.mode}/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes><footer className="app-footer"><span>© {new Date().getFullYear()} LUVIA Weather Intelligence</span><span><i className="footer-dot"/> {data.mode==='demo'?'Synthetic demo data':'Backend data'} · Updated {data.lastUpdated?data.lastUpdated.toLocaleTimeString('en-IN',{hour:'numeric',minute:'2-digit'}):'not yet'}</span></footer>
 </main> <Chatbot /></div>}
function AboutPage({mode}){return <div className="about-page"><div className="about-hero"><div className="about-symbol"><CloudLightning size={36}/></div><span className="eyebrow">ABOUT LUVIA</span><h1>Weather intelligence,<br/>with context.</h1><p>LUVIA brings weather-related reports, geographic exploration and evidence review into one place, helping people inspect what has been reported and what is known about it.</p><span className="data-tag">{mode==='demo'?'RUNNING IN DEMO MODE':'USING BACKEND DATA'}</span></div><div className="about-cards"><article className="panel"><Map/><h3>See where</h3><p>Explore available reports on an interactive map and compare activity across states.</p></article><article className="panel"><Activity/><h3>Find patterns</h3><p>Review event categories, time patterns and regional activity from the loaded dataset.</p></article><article className="panel"><ShieldCheck/><h3>Inspect evidence</h3><p>Keep source records, automated classifications and verification status distinct.</p></article></div><div className="notice-card"><Info size={18}/><p><strong>Responsible interpretation.</strong> A report is not automatically a confirmed incident. LUVIA displays the information supplied by its current data source and does not independently certify every claim. Demo records are synthetic.</p></div></div>}
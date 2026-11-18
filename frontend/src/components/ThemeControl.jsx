import { useEffect, useState } from 'react';
import { Moon, Sun, Sunrise, Sunset, ChevronDown } from 'lucide-react';
import { themeForHour } from '../constants/config';
const meta = { dawn:{label:'Dawn',icon:Sunrise}, morning:{label:'Morning',icon:Sun}, evening:{label:'Evening',icon:Sunset}, night:{label:'Night',icon:Moon} };
export default function ThemeControl({ theme, setTheme, automatic, setAutomatic }) {
 const [clock,setClock]=useState(new Date());
 useEffect(()=>{const id=setInterval(()=>setClock(new Date()),60000);return()=>clearInterval(id)},[]);
 const current=automatic?themeForHour(clock.getHours()):theme; const Icon=meta[current].icon;
 return <div className="theme-control"><div className="theme-clock-icon"><Icon size={18}/></div><div className="theme-clock"><strong>{clock.toLocaleTimeString('en-IN',{hour:'numeric',minute:'2-digit'})}</strong><span>{meta[current].label}{automatic?' · Auto':''}</span></div><ChevronDown size={14}/><select aria-label="Choose dashboard theme" value={automatic?'auto':theme} onChange={e=>{if(e.target.value==='auto')setAutomatic(true);else{setAutomatic(false);setTheme(e.target.value)}}}><option value="auto">Automatic theme</option><option value="dawn">Dawn</option><option value="morning">Morning / Afternoon</option><option value="evening">Evening</option><option value="night">Night</option></select></div>;
}
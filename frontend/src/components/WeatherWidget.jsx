import { useState, useEffect } from "react";

const CIRCUIT_COORDS = {
  "Australian Grand Prix":     { lat: -37.8497, lon: 144.9680, tz: "Australia/Melbourne" },
  "Bahrain Grand Prix":        { lat: 26.0325,  lon: 50.5106,  tz: "Asia/Bahrain" },
  "Saudi Arabian Grand Prix":  { lat: 21.6319,  lon: 39.1044,  tz: "Asia/Riyadh" },
  "Japanese Grand Prix":       { lat: 34.8431,  lon: 136.5410, tz: "Asia/Tokyo" },
  "Chinese Grand Prix":        { lat: 31.3389,  lon: 121.2200, tz: "Asia/Shanghai" },
  "Miami Grand Prix":          { lat: 25.9581,  lon: -80.2389, tz: "America/New_York" },
  "Emilia Romagna Grand Prix": { lat: 44.3439,  lon: 11.7167,  tz: "Europe/Rome" },
  "Monaco Grand Prix":         { lat: 43.7347,  lon: 7.4205,   tz: "Europe/Monaco" },
  "Canadian Grand Prix":       { lat: 45.5000,  lon: -73.5228, tz: "America/Toronto" },
  "Spanish Grand Prix":        { lat: 41.5700,  lon: 2.2611,   tz: "Europe/Madrid" },
  "Austrian Grand Prix":       { lat: 47.2197,  lon: 14.7647,  tz: "Europe/Vienna" },
  "British Grand Prix":        { lat: 52.0786,  lon: -1.0169,  tz: "Europe/London" },
  "Hungarian Grand Prix":      { lat: 47.5789,  lon: 19.2486,  tz: "Europe/Budapest" },
  "Belgian Grand Prix":        { lat: 50.4372,  lon: 5.9714,   tz: "Europe/Brussels" },
  "Dutch Grand Prix":          { lat: 52.3888,  lon: 4.5409,   tz: "Europe/Amsterdam" },
  "Italian Grand Prix":        { lat: 45.6156,  lon: 9.2811,   tz: "Europe/Rome" },
  "Azerbaijan Grand Prix":     { lat: 40.3725,  lon: 49.8533,  tz: "Asia/Baku" },
  "Singapore Grand Prix":      { lat: 1.2914,   lon: 103.8641, tz: "Asia/Singapore" },
  "United States Grand Prix":  { lat: 30.1328,  lon: -97.6411, tz: "America/Chicago" },
  "Mexico City Grand Prix":    { lat: 19.4042,  lon: -99.0907, tz: "America/Mexico_City" },
  "São Paulo Grand Prix":      { lat: -23.7036, lon: -46.6997, tz: "America/Sao_Paulo" },
  "Las Vegas Grand Prix":      { lat: 36.1147,  lon: -115.1728,tz: "America/Los_Angeles" },
  "Qatar Grand Prix":          { lat: 25.4900,  lon: 51.4536,  tz: "Asia/Qatar" },
  "Abu Dhabi Grand Prix":      { lat: 24.4672,  lon: 54.6031,  tz: "Asia/Dubai" },
};

const WMO = {
  0:  { icon: "☀️",  label: "Clear" },
  1:  { icon: "🌤️", label: "Mostly clear" },
  2:  { icon: "⛅",  label: "Partly cloudy" },
  3:  { icon: "☁️",  label: "Overcast" },
  45: { icon: "🌫️", label: "Foggy" },
  48: { icon: "🌫️", label: "Icy fog" },
  51: { icon: "🌦️", label: "Light drizzle" },
  53: { icon: "🌦️", label: "Drizzle" },
  55: { icon: "🌧️", label: "Heavy drizzle" },
  61: { icon: "🌧️", label: "Light rain" },
  63: { icon: "🌧️", label: "Rain" },
  65: { icon: "🌧️", label: "Heavy rain" },
  80: { icon: "🌦️", label: "Light showers" },
  81: { icon: "🌧️", label: "Showers" },
  82: { icon: "⛈️",  label: "Heavy showers" },
  95: { icon: "⛈️",  label: "Thunderstorm" },
  96: { icon: "⛈️",  label: "Storm + hail" },
  99: { icon: "⛈️",  label: "Heavy storm" },
};

function findCoords(raceName) {
  if (!raceName) return null;
  const entry = Object.entries(CIRCUIT_COORDS).find(([key]) =>
    raceName.toLowerCase().includes(key.split(" ")[0].toLowerCase())
  );
  return entry?.[1] ?? null;
}

export default function WeatherWidget({ nextRace }) {
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);

  const raceName = nextRace?.race_name;
  const raceDate = nextRace?.race_date;

  useEffect(() => {
    const coords = findCoords(raceName);
    if (!coords || !raceDate) return;

    setLoading(true);
    setForecast(null);

    const url = `https://api.open-meteo.com/v1/forecast?latitude=${coords.lat}&longitude=${coords.lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,windspeed_10m_max,weathercode&timezone=${encodeURIComponent(coords.tz)}&forecast_days=16`;

    fetch(url)
      .then(r => r.json())
      .then(data => {
        const base = new Date(raceDate);
        const days = [-2, -1, 0].map((offset, i) => {
          const d = new Date(base);
          d.setDate(base.getDate() + offset);
          const dateStr = d.toISOString().split("T")[0];
          const idx = data.daily.time.indexOf(dateStr);
          if (idx === -1) return null;
          return {
            label: ["FRI", "SAT", "SUN"][i],
            isRaceDay: i === 2,
            maxTemp: data.daily.temperature_2m_max[idx],
            minTemp: data.daily.temperature_2m_min[idx],
            rainPct: data.daily.precipitation_probability_max[idx] ?? 0,
            windKph: data.daily.windspeed_10m_max[idx],
            code: data.daily.weathercode[idx],
          };
        }).filter(Boolean);
        setForecast(days);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [raceName, raceDate]);

  if (!findCoords(raceName)) return null;

  const SESSION_LABEL = { FRI: "FRI PRACTICE", SAT: "SAT QUALIFYING", SUN: "SUN RACE" };

  return (
    <div className="pw-hairgrid grid grid-cols-3 gap-px border border-[#ff5c5c]/15">
      {loading && (
        <p className="col-span-3 text-pw-muted text-xs text-center py-6 bg-pw-panel">Loading forecast…</p>
      )}

      {!loading && forecast && forecast.map(day => {
        const rainColor = day.rainPct >= 40 ? "text-pw-red" : "text-pw-rain";
        return (
          <div
            key={day.label}
            className={`bg-pw-panel px-3 py-3.5 text-center ${day.isRaceDay ? "border-b-2 border-pw-red bg-[#1a0f0f]" : ""}`}
          >
            <p className="text-[9.5px] text-pw-muted tracking-[0.06em] mb-1">{SESSION_LABEL[day.label] || day.label}</p>
            <p className="text-white font-extrabold text-xl leading-none">{Math.round(day.maxTemp)}°C</p>
            <p className={`text-[10px] font-medium mt-1 ${rainColor}`}>RAIN {day.rainPct}%</p>
          </div>
        );
      })}
    </div>
  );
}

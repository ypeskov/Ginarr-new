#!/usr/bin/env python3
"""Fetch weather forecast from Open-Meteo API and print formatted output in Russian.

Usage:
  python3 scripts/forecast.py [--lat LAT --lon LON --city CITY --country COUNTRY] [--days N]

Defaults: Sofia, Bulgaria (lat=42.6977, lon=23.3219), 3 days forecast.

If --city is provided without --lat/--lon, geocodes via Open-Meteo geocoding API.

Output: formatted text ready to send to Telegram (plain text, no MarkdownV2).
Exit codes: 0 = success, 1 = fetch error, 2 = invalid arguments.
"""

import urllib.request
import json
import sys
import argparse


def geocode(city_name):
    """Geocode city name to lat/lon via Open-Meteo."""
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=15).read())
    if not data.get("results"):
        print(f"Error: city '{city_name}' not found.", file=sys.stderr)
        sys.exit(2)
    r = data["results"][0]
    return r["latitude"], r["longitude"], r["name"], r.get("country", "")


def emoji(code):
    code = int(code)
    if code == 0: return "☀️"
    if code in (1, 2): return "⛅"
    if code == 3: return "☁️"
    if code in (45, 48): return "🌫"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82): return "🌧"
    if code in (71, 73, 75, 77, 85, 86): return "🌨"
    if code in (95, 96, 99): return "⛈"
    return "🌤"


def wmo_desc(code):
    code = int(code)
    descs = {
        0: "Ясно", 1: "Малооблачно", 2: "Переменная облачность", 3: "Пасмурно",
        45: "Туман", 48: "Изморозь", 51: "Морось слабая", 53: "Морось", 55: "Морось сильная",
        56: "Ледяная морось", 57: "Ледяная морось сильная",
        61: "Дождь слабый", 63: "Дождь", 65: "Дождь сильный",
        66: "Ледяной дождь", 67: "Ледяной дождь сильный",
        71: "Снег слабый", 73: "Снег", 75: "Снег сильный", 77: "Снежные зёрна",
        80: "Ливень слабый", 81: "Ливень", 82: "Ливень сильный",
        85: "Снегопад слабый", 86: "Снегопад сильный",
        95: "Гроза", 96: "Гроза с градом", 99: "Гроза с сильным градом",
    }
    return descs.get(code, "Неизвестно")


MONTHS_RU = {1:"янв",2:"фев",3:"мар",4:"апр",5:"май",6:"июн",7:"июл",8:"авг",9:"сен",10:"окт",11:"ноя",12:"дек"}


def fetch_and_format(lat, lon, city_name, country, days):
    forecast_days = days + 1

    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode,sunrise,sunset"
        f"&hourly=temperature_2m,weathercode,precipitation_probability"
        f"&current=temperature_2m,apparent_temperature,weathercode,windspeed_10m,relativehumidity_2m"
        f"&timezone=auto&forecast_days={forecast_days}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())

    curr = data["current"]
    daily = data["daily"]
    hourly = data["hourly"]

    lines = []
    lines.append(f"📍 {city_name}, {country}")
    lines.append(f'Сейчас: {emoji(curr["weathercode"])} {curr["temperature_2m"]}°C, ощущается {curr["apparent_temperature"]}°C')
    lines.append(f'💨 {curr["windspeed_10m"]} км/ч  💧 {curr["relativehumidity_2m"]}%')
    lines.append("")

    now_str = curr["time"]
    today_date = daily["time"][0]
    future_hours = []
    for i, t in enumerate(hourly["time"]):
        if not t.startswith(today_date):
            continue
        if t <= now_str:
            continue
        hour = t[11:16]
        temp = hourly["temperature_2m"][i]
        wcode = hourly["weathercode"][i]
        rain = hourly["precipitation_probability"][i]
        e_h = emoji(wcode)
        rain_str = f"  💧{rain}%" if rain and int(rain) > 0 else ""
        future_hours.append(f"  {hour} {e_h} {temp}°C{rain_str}")

    if future_hours:
        lines.append("🕐 По часам сегодня:")
        lines.extend(future_hours)
        lines.append("")

    for i in range(1, forecast_days):
        d = daily["time"][i]
        parts = d.split("-")
        day_num = int(parts[2])
        mon = MONTHS_RU[int(parts[1])]
        maxt = daily["temperature_2m_max"][i]
        mint = daily["temperature_2m_min"][i]
        wcode = daily["weathercode"][i]
        rain = daily["precipitation_probability_max"][i]

        morning_t = evening_t = midday_t = ""
        for j, t in enumerate(hourly["time"]):
            if t == f"{d}T09:00":
                morning_t = f'{hourly["temperature_2m"][j]}'
            elif t == f"{d}T12:00":
                midday_t = f'{hourly["temperature_2m"][j]}'
            elif t == f"{d}T18:00":
                evening_t = f'{hourly["temperature_2m"][j]}'

        e = emoji(wcode)
        desc = wmo_desc(wcode)
        lines.append("━━━━━━━━━━━━━━━━━━")
        lines.append(f"📅 {day_num} {mon}")
        lines.append(f"{e} {desc}")
        lines.append(f"🌡 {mint}°C … {maxt}°C")
        if morning_t and midday_t and evening_t:
            lines.append(f"🌅 утро {morning_t}°C  🏙 день {midday_t}°C  🌆 вечер {evening_t}°C")
        if rain and int(rain) > 0:
            lines.append(f"🌧 Вероятность осадков: {rain}%")
        lines.append("")

    sunrise = daily["sunrise"][0][11:16]
    sunset = daily["sunset"][0][11:16]
    lines.append(f"🌅 Восход {sunrise}  🌇 Закат {sunset}")

    return "\n".join(lines)


def fetch_wttr_fallback(city_name, days):
    """Fallback: fetch forecast from wttr.in when Open-Meteo is down."""
    city_query = city_name if city_name != "София" else "Sofia"
    url = f"https://wttr.in/{city_query}?format=j1&lang=ru"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=20).read())

    curr = data["current_condition"][0]
    lines = []
    lines.append(f"📍 {city_name} (wttr.in fallback)")
    lines.append(f'{emoji_from_wttr(curr["weatherCode"])} {curr["temp_C"]}°C, ощущается {curr["FeelsLikeC"]}°C')
    lines.append(f'💨 {curr["windspeedKmph"]} км/ч  💧 {curr["humidity"]}%')
    lines.append("")

    for i, day in enumerate(data["weather"][:days]):
        parts = day["date"].split("-")
        day_num = int(parts[2])
        mon = MONTHS_RU[int(parts[1])]
        maxt = day["maxtempC"]
        mint = day["mintempC"]

        hourly = day.get("hourly", [])
        morning_t = hourly[3]["tempC"] if len(hourly) > 3 else ""  # 09:00
        midday_t = hourly[4]["tempC"] if len(hourly) > 4 else ""   # 12:00
        evening_t = hourly[6]["tempC"] if len(hourly) > 6 else ""  # 18:00

        if i == 0:
            lines.append("🕐 По часам сегодня:")
            for h in hourly:
                hour = int(h["time"]) // 100
                if hour < 7:
                    continue
                rain = h.get("chanceofrain", "0")
                rain_str = f"  💧{rain}%" if int(rain) > 0 else ""
                lines.append(f'  {hour:02d}:00 {emoji_from_wttr(h["weatherCode"])} {h["tempC"]}°C{rain_str}')
            lines.append("")
        else:
            lines.append("━━━━━━━━━━━━━━━━━━")
            lines.append(f"📅 {day_num} {mon}")
            lines.append(f"🌡 {mint}°C … {maxt}°C")
            if morning_t and midday_t and evening_t:
                lines.append(f"🌅 утро {morning_t}°C  🏙 день {midday_t}°C  🌆 вечер {evening_t}°C")
            rain = max((int(h.get("chanceofrain", "0")) for h in hourly), default=0)
            if rain > 0:
                lines.append(f"🌧 Вероятность осадков: {rain}%")
            lines.append("")

    astronomy = data["weather"][0].get("astronomy", [{}])[0]
    if astronomy:
        lines.append(f'🌅 Восход {astronomy.get("sunrise", "?")}  🌇 Закат {astronomy.get("sunset", "?")}')

    return "\n".join(lines)


def emoji_from_wttr(code):
    """Map wttr.in weather codes to emoji (same WMO-like codes)."""
    return emoji(code)


def fetch_compact(lat, lon, city_name, country, days):
    """Compact forecast: one line per day, no hourly details."""
    forecast_days = days + 1
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,weathercode,precipitation_probability_max"
        f"&current=temperature_2m,weathercode"
        f"&timezone=auto&forecast_days={forecast_days}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())

    curr = data["current"]
    daily = data["daily"]

    lines = []
    # Today-only mode: single line with current temp and today's range
    if days == 1:
        mint = daily["temperature_2m_min"][0]
        maxt = daily["temperature_2m_max"][0]
        rain = daily["precipitation_probability_max"][0]
        rain_str = f" 💧{rain}%" if rain and int(rain) > 20 else ""
        lines.append(f"📍 {city_name}: {emoji(curr['weathercode'])} {curr['temperature_2m']}°C  ↕ {mint}°…{maxt}°{rain_str}")
    else:
        lines.append(f"📍 {city_name}: {emoji(curr['weathercode'])} {curr['temperature_2m']}°C")
        for i in range(1, forecast_days):
            d = daily["time"][i]
            parts = d.split("-")
            day_num = int(parts[2])
            mon = MONTHS_RU[int(parts[1])]
            maxt = daily["temperature_2m_max"][i]
            mint = daily["temperature_2m_min"][i]
            wcode = daily["weathercode"][i]
            rain = daily["precipitation_probability_max"][i]
            rain_str = f" 💧{rain}%" if rain and int(rain) > 20 else ""
            lines.append(f"  {day_num} {mon}: {emoji(wcode)} {mint}°…{maxt}°{rain_str}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fetch weather forecast from Open-Meteo")
    parser.add_argument("--lat", type=float, help="Latitude")
    parser.add_argument("--lon", type=float, help="Longitude")
    parser.add_argument("--city", default="Sofia", help="City name (default: Sofia)")
    parser.add_argument("--country", default="", help="Country name")
    parser.add_argument("--days", type=int, default=7, help="Number of forecast days (default: 7, max: 7)")
    parser.add_argument("--compact", action="store_true", help="Compact output (one line per day)")
    args = parser.parse_args()

    if args.days < 1 or args.days > 7:
        print("Error: --days must be between 1 and 7.", file=sys.stderr)
        sys.exit(2)

    if args.lat is not None and args.lon is not None:
        lat, lon, city_name, country = args.lat, args.lon, args.city, args.country
    elif args.city == "Sofia":
        lat, lon, city_name, country = 42.6977, 23.3219, "София", "Болгария"
    else:
        lat, lon, city_name, country = geocode(args.city)

    # Try Open-Meteo first (3 attempts), then fall back to wttr.in
    last_error = None
    for attempt in range(3):
        try:
            if args.compact:
                result = fetch_compact(lat, lon, city_name, country, args.days)
            else:
                result = fetch_and_format(lat, lon, city_name, country, args.days)
            print(result)
            return
        except Exception as e:
            last_error = e
            import time
            if attempt < 2:
                time.sleep(5)

    # Fallback to wttr.in
    try:
        print(f"[Open-Meteo недоступен, использую wttr.in]", file=sys.stderr)
        result = fetch_wttr_fallback(city_name, args.days)
        print(result)
    except Exception as e2:
        print(f"Error: Open-Meteo: {last_error}; wttr.in: {e2}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

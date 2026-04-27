import requests
import pandas as pd
import os
from datetime import datetime
import pytz

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")

VJAZDY = {
    "Zelenec": "48.3615,17.5855",
    "Bučany": "48.3932,17.6105",
    "Zavar": "48.3735,17.6255",
    "B. Kostol": "48.3711,17.5512",
    "Suchá": "48.3885,17.5312",
    "Špačince": "48.4055,17.6012",
    "Ružindol": "48.3585,17.5355",
    "Boleráz": "48.4025,17.5511",
    "Nitrianska": "48.3725,17.6055",
    "Hrnčiarovce": "48.3555,17.5755"
}

YR_ICON_MAP = {
    "clearsky": "bi-sun", "fair": "bi-cloud-sun", "partlycloudy": "bi-cloud-sun",
    "cloudy": "bi-clouds", "rain": "bi-cloud-rain", "heavyrain": "bi-cloud-rain-heavy",
    "snow": "bi-snow", "fog": "bi-cloud-fog", "lightrain": "bi-cloud-drizzle"
}

def ziskaj_plynulost(suradnice):
    try:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/12/json?key={TOMTOM_KEY}&point={suradnice}"
        res = requests.get(url, timeout=10).json()
        flow = res.get('flowSegmentData', {})
        return round((flow.get('currentSpeed', 1) / flow.get('freeFlowSpeed', 1)) * 100, 1)
    except: return 100

def ziskaj_pocasi_yr():
    try:
        headers = {'User-Agent': 'TrnavaPulse/1.0'}
        res = requests.get("https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=48.37&lon=17.58", headers=headers, timeout=10).json()
        data = res['properties']['timeseries'][0]['data']
        return data['instant']['details']['air_temperature'], data['next_1_hours']['summary']['symbol_code'].split('_')[0]
    except: return 0, "cloudy"

def ziskaj_parkovanie():
    res = {"Rybníková": "N/A", "Hospodárska": "N/A", "Kollárova": "N/A"}
    try:
        data = requests.get("https://opendata.trnava.sk/api/v1/parkings", timeout=10).json()
        for p in data['features']:
            name = p['properties']['name']
            val = p['properties']['free_places']
            if "Rybníková" in name: res["Rybníková"] = val
            elif "Hospodárska" in name: res["Hospodárska"] = val
            elif "Kollárova" in name: res["Kollárova"] = val
        return res
    except: return res

def zber_dat():
    zona = pytz.timezone('Europe/Bratislava')
    teraz = datetime.now(zona)
    teplota, symbol = ziskaj_pocasi_yr()
    park = ziskaj_parkovanie()
    
    novy_riadok = {"Čas": teraz.strftime("%Y-%m-%d %H:%M:%S"), "Teplota": teplota, "Symbol": symbol}
    for n, s in VJAZDY.items(): novy_riadok[n] = ziskaj_plynulost(s)
    for n, v in park.items(): novy_riadok[f"P_{n}"] = v

    excel_file = "data_trnava_komplet.xlsx"
    try:
        df = pd.read_excel(excel_file)
        df = pd.concat([df, pd.DataFrame([novy_riadok])], ignore_index=True)
    except: 
        df = pd.DataFrame([novy_riadok])
    
    df.to_excel(excel_file, index=False)

    df_last = df.tail(10).copy()
    rows_html = ""
    for _, r in df_last.iterrows():
        cas_val = str(r['Čas'])
        t_short = cas_val.split(" ")[1][:5] if " " in cas_val else cas_val[:5]
        icon = YR_ICON_MAP.get(r['Symbol'], "bi-cloud")
        
        traffic_cells = ""
        for n in VJAZDY.keys():
            val = r[n] if pd.notnull(r[n]) else 100
            status_class = "status-green" if val > 85 else "status-orange" if val > 60 else "status-red"
            status_text = "Plynulá" if val > 85 else "Zdržanie" if val > 60 else "Zápcha"
            traffic_cells += f'<td><span class="status-pill {status_class}">{status_text} ({val}%)</span></td>'
        
        park_cells = "".join([f'<td><span class="text-dark fw-bold">{r[f"P_{n}"] if pd.notnull(r[f"P_{n}"]) else "N/A"}</span></td>' for n in ["Rybníková", "Hospodárska", "Kollárova"]])
        
        rows_html += f'<tr><td class="time-col">{t_short}</td><td class="fw-bold">{r["Teplota"]}°C</td><td><i class="bi {icon}"></i></td>{traffic_cells}{park_cells}</tr>'

    html_content = f"""
    <!DOCTYPE html>
    <html lang="sk">
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <title>TrnavaPulse - Smart Dashboard</title>
        <style>
            body {{ background-color: #ffffff; font-family: -apple-system, system-ui, sans-serif; color: #111; }}
            .sidebar {{ width: 260px; height: 100vh; background: #f9f9f9; position: fixed; padding: 40px 20px; border-right: 1px solid #eee; display: flex; flex-direction: column; }}
            .main {{ margin-left: 260px; padding: 50px; }}
            .logo {{ font-weight: 800; font-size: 1.5rem; margin-bottom: 40px; color: #1a73e8; letter-spacing: -1px; }}
            .nav-item {{ padding: 12px 15px; border-radius: 10px; color: #555; text-decoration: none; display: block; margin-bottom: 5px; font-weight: 500; transition: 0.2s; }}
            .nav-item:hover {{ background: #f0f0f0; }}
            .nav-item.active {{ background: #e8f0fe; color: #1a73e8; }}
            .nav-item i {{ margin-right: 12px; }}
            
            .greeting {{ font-size: 2.2rem; font-weight: 800; margin-bottom: 10px; letter-spacing: -1px; }}
            .sub-greeting {{ color: #777; margin-bottom: 35px; display: flex; gap: 20px; font-weight: 500; font-size: 0.9rem; }}
            
            .legend-box {{ background: #fff; border: 1px solid #eee; border-radius: 15px; padding: 20px; margin-bottom: 30px; }}
            .legend-title {{ font-size: 0.75rem; font-weight: 800; text-transform: uppercase; color: #aaa; letter-spacing: 1px; margin-bottom: 15px; display: block; }}
            
            .table-container {{ border: 1px solid #eee; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }}
            .custom-table {{ width: 100%; border-collapse: collapse; }}
            .custom-table th {{ background: #fafafa; padding: 18px 12px; text-align: center; font-size: 0.7rem; color: #999; text-transform: uppercase; border-bottom: 1px solid #eee; letter-spacing: 0.5px; }}
            .custom-table td {{ padding: 16px 12px; text-align: center; border-bottom: 1px solid #eee; font-size: 0.85rem; color: #333; }}
            .time-col {{ text-align: left !important; padding-left: 25px !important; font-weight: 600; color: #1a73e8 !important; }}
            
            .status-pill {{ padding: 5px 12px; border-radius: 8px; font-size: 0.75rem; font-weight: 700; display: inline-block; min-width: 110px; }}
            .status-green {{ background: #e6f7ed; color: #1db45a; }}
            .status-orange {{ background: #fff4e5; color: #ff9800; }}
            .status-red {{ background: #fdeaea; color: #f44336; }}
            
            .source-links {{ margin-top: auto; padding-top: 20px; border-top: 1px solid #eee; font-size: 0.75rem; color: #aaa; }}
            .source-links a {{ color: #777; text-decoration: none; display: block; margin-bottom: 8px; }}
            .source-links a:hover {{ text-decoration: underline; color: #1a73e8; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="logo"><i class="bi bi-broadcast-pin"></i> TT-Pulse</div>
            <a href="#" class="nav-item active"><i class="bi bi-grid-1x2"></i> Dashboard</a>
            <a href="#" class="nav-item"><i class="bi bi-map"></i> Mapa mesta</a>
            <a href="#" class="nav-item"><i class="bi bi-calendar3"></i> Analýzy</a>
            
            <div class="source-links">
                <span style="font-weight: 700; color: #555; display: block; margin-bottom: 10px;">ZDROJE DÁT</span>
                <a href="https://www.yr.no/en/forecast/daily-table/2-3057140/Slovakia/Trnava/Trnava" target="_blank"><i class="bi bi-cloud-sun"></i> Počasie: YR.no</a>
                <a href="https://www.tomtom.com/en_gb/traffic-index/trnava-traffic/" target="_blank"><i class="bi bi-car-front"></i> Doprava: TomTom</a>
                <a href="https://opendata.trnava.sk/" target="_blank"><i class="bi bi-database"></i> Parkovanie: OpenData TT</a>
            </div>
        </div>

        <div class="main">
            <div class="greeting">Prehľad Trnavy</div>
            <div class="sub-greeting">
                <span><i class="bi bi-clock-history"></i> Posledná aktualizácia: {teraz.strftime("%H:%M:%S")}</span>
                <span><i class="bi bi-geo-alt"></i> Lokalita: Trnava, SK</span>
            </div>

            <div class="legend-box">
                <span class="legend-title">Legenda plynulosti vjazdov</span>
                <div class="d-flex gap-4">
                    <div class="d-flex align-items-center gap-2">
                        <span class="status-pill status-green" style="min-width: 20px; padding: 4px 8px;">Plynulá</span>
                        <span class="small text-muted">> 85% rýchlosti</span>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <span class="status-pill status-orange" style="min-width: 20px; padding: 4px 8px;">Zdržanie</span>
                        <span class="small text-muted">60% - 85% rýchlosti</span>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <span class="status-pill status-red" style="min-width: 20px; padding: 4px 8px;">Zápcha</span>
                        <span class="small text-muted">< 60% rýchlosti</span>
                    </div>
                </div>
            </div>

            <div class="table-container">
                <table class="custom-table">
                    <thead>
                        <tr>
                            <th style="text-align:left; padding-left:25px;">Čas</th>
                            <th>Tep.</th>
                            <th>Obloha</th>
                            {"".join([f"<th>{n}</th>" for n in VJAZDY.keys()])}
                            <th>Rybníková</th><th>Hosp.</th><th>Kollár.</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    zber_dat()

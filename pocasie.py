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
    "clearsky": "bi-sun-fill", "fair": "bi-cloud-sun-fill", "partlycloudy": "bi-cloud-sun-fill",
    "cloudy": "bi-clouds-fill", "rain": "bi-cloud-rain-fill", "heavyrain": "bi-cloud-rain-heavy-fill",
    "snow": "bi-snow", "fog": "bi-cloud-fog-fill", "lightrain": "bi-cloud-drizzle-fill"
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
        headers = {'User-Agent': 'TrnavaMonitor/1.0'}
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

    # --- HTML GENERÁCIA ---
    df_last = df.tail(8).copy()
    rows_html = ""
    for _, r in df_last.iterrows():
        # OPRAVA: Prevod na string a ošetrenie NaN hodnôt
        cas_str = str(r['Čas'])
        try:
            # Skúsime vybrať len čas HH:MM
            t_short = cas_str.split(" ")[1][:5] if " " in cas_str else cas_str[:5]
        except:
            t_short = "??:??"

        icon = Y_ICON_MAP.get(r['Symbol'], "bi-cloud-fill")
        
        # Plynulosť dopravy
        traffic_cells = ""
        for n in VJAZDY.keys():
            val = r[n] if pd.notnull(r[n]) else 100
            color = "#2ecc71" if val > 85 else "#f1c40f" if val > 60 else "#e74c3c"
            traffic_cells += f'<td><div class="traffic-val" style="color:{color}">{val}%</div></td>'
        
        # Parkovanie
        park_cells = "".join([f'<td><span class="park-num">{r[f"P_{n}"] if pd.notnull(r[f"P_{n}"]) else "N/A"}</span></td>' for n in ["Rybníková", "Hospodárska", "Kollárova"]])
        
        rows_html += f'<tr><td class="time-col">{t_short}</td><td>{r["Teplota"]}°</td><td><i class="bi {icon}"></i></td>{traffic_cells}{park_cells}</tr>'

    html_content = f"""
    <!DOCTYPE html>
    <html lang="sk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <title>Crextio Trnava Dashboard</title>
        <style>
            body {{ 
                background: linear-gradient(135deg, #e0eafc 0%, #cfdef3 100%); 
                min-height: 100vh; font-family: 'Inter', sans-serif; padding: 40px 20px; color: #444;
            }}
            .glass-shell {{
                background: rgba(255, 255, 255, 0.7);
                backdrop-filter: blur(15px);
                border-radius: 40px;
                border: 1px solid rgba(255, 255, 255, 0.4);
                max-width: 1200px; margin: auto; padding: 40px;
                box-shadow: 0 25px 50px rgba(0,0,0,0.05);
            }}
            .nav-bar {{ display: flex; justify-content: center; gap: 15px; margin-bottom: 40px; flex-wrap: wrap; }}
            .nav-item {{ background: #fff; padding: 10px 20px; border-radius: 100px; font-weight: 600; font-size: 0.8rem; box-shadow: 0 4px 10px rgba(0,0,0,0.03); border: none; }}
            .nav-item.active {{ background: #222; color: #fff; }}
            .hero-title {{ font-size: 2.5rem; font-weight: 800; letter-spacing: -1.5px; margin-bottom: 40px; color: #222; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 40px; }}
            .info-card {{ background: #fff; border-radius: 30px; padding: 25px; border: 1px solid rgba(255,255,255,0.8); }}
            .card-label {{ font-size: 0.75rem; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: 1px; }}
            .card-val {{ font-size: 2rem; font-weight: 800; display: block; margin: 10px 0; }}
            .table-wrap {{ background: rgba(255,255,255,0.5); border-radius: 30px; padding: 20px; overflow-x: auto; }}
            .glass-table {{ width: 100%; border-collapse: collapse; min-width: 800px; }}
            .glass-table th {{ padding: 15px; font-size: 0.65rem; text-transform: uppercase; color: #999; font-weight: 800; text-align: center; }}
            .glass-table td {{ padding: 18px 10px; text-align: center; border-bottom: 1px solid rgba(0,0,0,0.03); font-size: 0.9rem; font-weight: 600; }}
            .time-col {{ color: #000; font-weight: 800 !important; text-align: left !important; padding-left: 20px !important; }}
            .park-num {{ background: #eee; padding: 5px 12px; border-radius: 10px; font-size: 0.8rem; }}
            .traffic-val {{ font-family: 'Monaco', monospace; font-weight: 800; }}
        </style>
    </head>
    <body>
        <div class="glass-shell">
            <div class="nav-bar">
                <button class="nav-item active">Dashboard</button>
                <button class="nav-item">Doprava</button>
                <button class="nav-item">Parkovanie</button>
                <button class="nav-item">System</button>
            </div>

            <h1 class="hero-title text-center text-md-start">Welcome in, Trnava</h1>

            <div class="stats-grid text-center text-md-start">
                <div class="info-card">
                    <span class="card-label">Počasie teraz</span>
                    <span class="card-val">{teplota}°C <i class="bi {YR_ICON_MAP.get(symbol, 'bi-cloud-fill')}"></i></span>
                    <span class="badge bg-dark rounded-pill p-2 px-3">{teraz.strftime("%H:%M")}</span>
                </div>
                <div class="info-card">
                    <span class="card-label">Rybníková voľné</span>
                    <span class="card-val" style="color: #4a90e2;">{park['Rybníková']}</span>
                    <div class="progress" style="height: 6px; border-radius: 10px;"><div class="progress-bar" style="width: 60%"></div></div>
                </div>
                <div class="info-card">
                    <span class="card-label">Status</span>
                    <span class="card-val" style="font-size: 1.2rem; margin-top: 20px;">ONLINE</span>
                    <span style="font-size: 0.7rem; font-weight: 700; color: #2ecc71;"><i class="bi bi-circle-fill"></i> REÁLNY ČAS</span>
                </div>
            </div>

            <div class="table-wrap">
                <table class="glass-table">
                    <thead>
                        <tr>
                            <th>Čas</th><th>Teplota</th><th>Obloha</th>
                            {"".join([f"<th>{n}</th>" for n in VJAZDY.keys()])}
                            <th>Ryb.</th><th>Hosp.</th><th>Koll.</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
            <p class="text-center mt-4 small text-muted">Dáta: MET Norway, TomTom, OpenData Trnava</p>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    zber_dat()

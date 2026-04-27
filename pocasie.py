import requests
import pandas as pd
import os
from datetime import datetime
import pytz
import json

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY")

# Tvoje spresnené súradnice
VJAZDY = {
    "Zelenec": "48.355515,17.589294", "Bučany": "48.389916,17.612661", "Zavar": "48.375651,17.621178",
    "B. Kostol": "48.376036,17.565585", "Suchá": "48.389582,17.557863", "Špačince": "48.402741,17.600505",
    "Ružindol": "48.382533,17.562232", "Boleráz": "48.393661,17.562692", "Nitrianska": "48.362222,17.602526",
    "Hrnčiarovce": "48.351978,17.574577"
}

YR_ICON_MAP = {
    "clearsky": "bi-sun", "fair": "bi-cloud-sun", "partlycloudy": "bi-cloud-sun",
    "cloudy": "bi-clouds", "rain": "bi-cloud-rain", "heavyrain": "bi-cloud-rain-heavy",
    "snow": "bi-snow", "fog": "bi-cloud-fog", "lightrain": "bi-cloud-drizzle"
}

# --- FUNKCIE (Zber dát) ---

def ziskaj_plynulost(suradnice):
    try:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/12/json?key={TOMTOM_KEY}&point={suradnice}"
        res = requests.get(url, timeout=10).json()
        flow = res.get('flowSegmentData', {})
        return round((flow.get('currentSpeed', 1) / flow.get('freeFlowSpeed', 1)) * 100, 1)
    except: return 100

def ziskaj_pocasi_yr():
    try:
        headers = {'User-Agent': 'TrnavaPulse/1.0 (https://github.com/vas-repo)'}
        res = requests.get("https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=48.37&lon=17.58", headers=headers).json()
        data = res['properties']['timeseries'][0]['data']
        return data['instant']['details']['air_temperature'], data['next_1_hours']['summary']['symbol_code'].split('_')[0]
    except: return 0, "cloudy"

def ziskaj_parkovanie():
    res = {"Rybníková": "N/A", "Hospodárska": "N/A", "Kollárova": "N/A"}
    try:
        data = requests.get("https://opendata.trnava.sk/api/v1/parkings").json()
        for p in data['features']:
            name = p['properties']['name']
            val = p['properties']['free_places']
            for k in res.keys():
                if k in name: res[k] = val
        return res
    except: return res

# --- HLAVNÁ LOGIKA ---

def zber_dat():
    zona = pytz.timezone('Europe/Bratislava')
    teraz = datetime.now(zona)
    teplota, symbol = ziskaj_pocasi_yr()
    park = ziskaj_parkovanie()
    
    # Zápis dát do Excelu
    novy_riadok = {"Čas": teraz.strftime("%Y-%m-%d %H:%M:%S"), "Teplota": teplota, "Symbol": symbol}
    for n, s in VJAZDY.items(): novy_riadok[n] = ziskaj_plynulost(s)
    for n, v in park.items(): novy_riadok[f"P_{n}"] = v

    excel_file = "data_trnava_komplet.xlsx"
    try:
        df = pd.read_excel(excel_file)
        df = pd.concat([df, pd.DataFrame([novy_riadok])], ignore_index=True)
    except: df = pd.DataFrame([novy_riadok])
    df.to_excel(excel_file, index=False)

    # Príprava HTML výstupu
    df_chart = df.tail(20)
    chart_labels = [str(c).split(" ")[1][:5] if " " in str(c) else str(c)[:5] for c in df_chart['Čas']]
    chart_data = [round(df_chart[list(VJAZDY.keys())].iloc[i].mean(), 1) for i in range(len(df_chart))]

    rows_html = ""
    for _, r in df.tail(15).iloc[::-1].iterrows():
        cas = str(r['Čas']).split(" ")[1][:5] if " " in str(r['Čas']) else str(r['Čas'])[:5]
        traffic = "".join([f'<td><span class="status-pill {"status-green" if r[n]>85 else "status-orange" if r[n]>60 else "status-red"}">{r[n]}%</span></td>' for n in VJAZDY.keys()])
        rows_html += f'<tr><td class="time-col">{cas}</td><td class="fw-bold">{r["Teplota"]}°C</td><td><i class="bi {YR_ICON_MAP.get(r["Symbol"], "bi-cloud")}"></i></td>{traffic}<td>{r.get("P_Rybníková","N/A")}</td><td>{r.get("P_Hospodárska","N/A")}</td><td>{r.get("P_Kollárova","N/A")}</td></tr>'

    html_content = f"""
    <!DOCTYPE html>
    <html lang="sk">
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <title>TT-Pulse | Smart City Dashboard</title>
        <style>
            :root {{ --primary: #1a73e8; --sidebar: #f8f9fa; }}
            body {{ background: #ffffff; font-family: 'Inter', -apple-system, sans-serif; display: flex; margin: 0; }}
            .sidebar {{ width: 280px; height: 100vh; background: var(--sidebar); position: fixed; border-right: 1px solid #eee; padding: 30px 20px; display: flex; flex-direction: column; }}
            .main {{ margin-left: 280px; width: 100%; min-height: 100vh; background: #fff; }}
            .top-bar {{ height: 70px; border-bottom: 1px solid #eee; display: flex; align-items: center; justify-content: space-between; padding: 0 40px; }}
            .content {{ padding: 40px; }}
            .nav-link {{ padding: 12px 15px; border-radius: 10px; color: #555; text-decoration: none; display: flex; align-items: center; gap: 12px; margin-bottom: 5px; cursor: pointer; transition: 0.2s; }}
            .nav-link.active {{ background: #e8f0fe; color: var(--primary); font-weight: 600; }}
            .nav-link:hover:not(.active) {{ background: #f1f3f4; }}
            .card-custom {{ background: #fff; border: 1px solid #eee; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); overflow: hidden; }}
            .status-pill {{ padding: 5px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; display: inline-block; min-width: 65px; text-align: center; }}
            .status-green {{ background: #e6f4ea; color: #1e8e3e; }}
            .status-orange {{ background: #fef7e0; color: #f9ab00; }}
            .status-red {{ background: #fce8e6; color: #d93025; }}
            .time-col {{ font-weight: 700; color: var(--primary); padding-left: 25px !important; text-align: left !important; }}
            .legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 0.8rem; color: #666; }}
            .view-section {{ display: none; }}
            .view-section.active {{ display: block; }}
            .source-box {{ margin-top: auto; padding-top: 20px; border-top: 1px solid #ddd; }}
            .source-link {{ font-size: 0.75rem; color: #888; text-decoration: none; display: block; margin-bottom: 8px; }}
            .source-link:hover {{ color: var(--primary); }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h3 class="text-primary fw-bold mb-4"><i class="bi bi-broadcast-pin"></i> TT-Pulse</h3>
            <div class="nav-link active" onclick="show('dash', this)"><i class="bi bi-grid-1x2"></i> Dashboard</div>
            <div class="nav-link" onclick="show('map', this)"><i class="bi bi-map"></i> Mapa mesta</div>
            <div class="nav-link" onclick="show('stats', this)"><i class="bi bi-graph-up"></i> Analýzy</div>

            <div class="source-box">
                <p class="small fw-bold text-uppercase text-muted mb-2" style="font-size: 0.65rem;">Zdroje dát</p>
                <a href="https://www.yr.no/en/forecast/daily-table/2-3057140/Slovakia/Trnava/Trnava" target="_blank" class="source-link"><i class="bi bi-cloud-sun"></i> Počasie: YR.no</a>
                <a href="https://www.tomtom.com/traffic-index/trnava-traffic/" target="_blank" class="source-link"><i class="bi bi-car-front"></i> Doprava: TomTom</a>
                <a href="https://opendata.trnava.sk/" target="_blank" class="source-link"><i class="bi bi-database"></i> Parkovanie: OpenData TT</a>
            </div>
        </div>

        <div class="main">
            <div class="top-bar">
                <div class="d-flex align-items-center gap-3">
                    <span class="badge bg-primary">LIVE</span>
                    <span class="fw-bold">Monitoring Trnava</span>
                </div>
                <div class="text-muted small">
                    <i class="bi bi-clock me-1"></i> Posledná aktualizácia: {teraz.strftime("%H:%M")}
                </div>
            </div>

            <div class="content">
                <div id="dash" class="view-section active">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <h2 class="fw-bold m-0">Prehľad vjazdov</h2>
                        <div class="d-flex gap-3 card-custom px-3 py-2">
                            <div class="legend-item"><span class="status-pill status-green"></span> Plynulá</div>
                            <div class="legend-item"><span class="status-pill status-orange"></span> Zhustená</div>
                            <div class="legend-item"><span class="status-pill status-red"></span> Zápcha</div>
                        </div>
                    </div>
                    
                    <div class="card-custom">
                        <div class="table-responsive">
                            <table class="table table-hover mb-0">
                                <thead class="table-light">
                                    <tr>
                                        <th class="time-col">Čas</th><th>Tep.</th><th>Obloha</th>
                                        {"".join([f"<th>{n}</th>" for n in VJAZDY.keys()])}
                                        <th class="bg-light">Ryb.</th><th class="bg-light">Hosp.</th><th class="bg-light">Koll.</th>
                                    </tr>
                                </thead>
                                <tbody>{rows_html}</tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div id="map" class="view-section">
                    <h2 class="fw-bold mb-4">Živá dopravná mapa Trnavy</h2>
                    <div class="card-custom">
                        <iframe
                            width="100%"
                            height="600"
                            style="border:0"
                            loading="lazy"
                            allowfullscreen
                            referrerpolicy="no-referrer-when-downgrade"
                            src=f"https://www.google.com/maps/embed/v1/directions?key={GOOGLE_MAPS_KEY}&origin=Trnava,Slovakia&destination=Trnava,Slovakia&mode=driving"
                        </iframe>
                    </div>
                    <p class="mt-2 small text-muted">
                        <i class="bi bi-info-circle me-1"></i> Režim trás automaticky aktivuje vrstvu premávky (zelená/oranžová/červená).
                    </p>
                </div>

                <div id="stats" class="view-section">
                    <h2 class="fw-bold mb-4">Trend plynulosti dopravy</h2>
                    <div class="card-custom p-4">
                        <canvas id="trafficChart" height="100"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function show(id, el) {{
                document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));
                document.getElementById(id).classList.add('active');
                document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
                el.classList.add('active');
            }}

            new Chart(document.getElementById('trafficChart'), {{
                type: 'line',
                data: {{
                    labels: {json.dumps(chart_labels)},
                    datasets: [{{
                        label: 'Priemerná priepustnosť (%)',
                        data: {json.dumps(chart_data)},
                        borderColor: '#1a73e8',
                        backgroundColor: 'rgba(26, 115, 232, 0.1)',
                        fill: true,
                        tension: 0.4,
                        borderWidth: 3
                    }}]
                }},
                options: {{ 
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{ y: {{ min: 0, max: 100, ticks: {{ callback: v => v + '%' }} }} }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    zber_dat()

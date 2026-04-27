import requests
import pandas as pd
import os
from datetime import datetime
import pytz
import json

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")

VJAZDY = {
    "Zelenec": "48.3615,17.5855", "Bučany": "48.3932,17.6105", "Zavar": "48.3735,17.6255",
    "B. Kostol": "48.3711,17.5512", "Suchá": "48.3885,17.5312", "Špačince": "48.4055,17.6012",
    "Ružindol": "48.3585,17.5355", "Boleráz": "48.4025,17.5511", "Nitrianska": "48.3725,17.6055",
    "Hrnčiarovce": "48.3555,17.5755"
}

KAPACITY = {"Rybníková": 150, "Hospodárska": 100, "Kollárova": 120}

YR_ICON_MAP = {
    "clearsky": "bi-sun", "fair": "bi-cloud-sun", "partlycloudy": "bi-cloud-sun",
    "cloudy": "bi-clouds", "rain": "bi-cloud-rain", "heavyrain": "bi-cloud-rain-heavy",
    "snow": "bi-snow", "fog": "bi-cloud-fog", "lightrain": "bi-cloud-drizzle"
}

def ziskaj_plynulost(suradnice):
    try:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/12/json?key={TOMTOM_KEY}&point={suradnice}"
        res = requests.get(url, timeout=10).json()
        return round((res['flowSegmentData'].get('currentSpeed', 1) / res['flowSegmentData'].get('freeFlowSpeed', 1)) * 100, 1)
    except: return 100

def ziskaj_pocasi_yr():
    try:
        headers = {'User-Agent': 'TrnavaPulse/1.0'}
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
    except: df = pd.DataFrame([novy_riadok])
    df.to_excel(excel_file, index=False)

    # Príprava dát pre graf (Analýzy) - posledných 20 záznamov
    df_chart = df.tail(20)
    chart_labels = [str(c).split(" ")[1][:5] for c in df_chart['Čas']]
    chart_data = {n: df_chart[n].tolist() for n in VJAZDY.keys()}

    # Generovanie riadkov tabuľky
    rows_html = ""
    for _, r in df.tail(15).iloc[::-1].iterrows(): # Posledných 15 od najnovšieho
        cas = str(r['Čas']).split(" ")[1][:5] if " " in str(r['Čas']) else str(r['Čas'])[:5]
        traffic = "".join([f'<td><span class="status-pill {"status-green" if r[n]>85 else "status-orange" if r[n]>60 else "status-red"}">{r[n]}%</span></td>' for n in VJAZDY.keys()])
        park_vals = "".join([f'<td><span class="fw-bold">{r[f"P_{n}"]}</span></td>' for n in KAPACITY.keys()])
        rows_html += f'<tr><td class="time-col">{cas}</td><td class="fw-bold">{r["Teplota"]}°</td><td><i class="bi {YR_ICON_MAP.get(r["Symbol"], "bi-cloud")}"></i></td>{traffic}{park_vals}</tr>'

    # HTML s JavaScriptom pre menu a grafy
    html_content = f"""
    <!DOCTYPE html>
    <html lang="sk">
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <title>TrnavaPulse v2</title>
        <style>
            body {{ background: #fff; font-family: sans-serif; display: flex; }}
            .sidebar {{ width: 260px; height: 100vh; background: #f9f9f9; position: fixed; border-right: 1px solid #eee; padding: 40px 20px; z-index: 1000; }}
            .main-content {{ margin-left: 260px; padding: 50px; width: 100%; }}
            .nav-item {{ padding: 12px 15px; border-radius: 10px; color: #555; text-decoration: none; display: block; margin-bottom: 5px; cursor: pointer; }}
            .nav-item.active {{ background: #e8f0fe; color: #1a73e8; font-weight: 600; }}
            .nav-item:hover:not(.active) {{ background: #f0f0f0; }}
            .view-section {{ display: none; }}
            .view-section.active {{ display: block; }}
            .status-pill {{ padding: 4px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 700; }}
            .status-green {{ background: #e6f7ed; color: #1db45a; }}
            .status-orange {{ background: #fff4e5; color: #ff9800; }}
            .status-red {{ background: #fdeaea; color: #f44336; }}
            .time-col {{ color: #1a73e8; font-weight: 600; }}
            #map {{ width: 100%; height: 600px; border-radius: 20px; border: 1px solid #eee; }}
            .chart-container {{ background: #fff; border: 1px solid #eee; border-radius: 20px; padding: 20px; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="h4 fw-bold text-primary mb-4">TT-Pulse</div>
            <div class="nav-item active" onclick="showSection('dashboard', this)"><i class="bi bi-grid-1x2 me-2"></i> Dashboard</div>
            <div class="nav-item" onclick="showSection('mapa', this)"><i class="bi bi-map me-2"></i> Mapa mesta</div>
            <div class="nav-item" onclick="showSection('analyzy', this)"><i class="bi bi-bar-chart me-2"></i> Analýzy</div>
            <div class="mt-auto pt-4 border-top small text-muted">
                Dáta: YR, TomTom, OpenData TT
            </div>
        </div>

        <div class="main-content">
            <div id="dashboard" class="view-section active">
                <h1 class="fw-bold mb-4">Dashboard</h1>
                <div class="table-responsive border rounded-4 shadow-sm">
                    <table class="table table-hover mb-0">
                        <thead class="table-light">
                            <tr>
                                <th class="ps-4">Čas</th><th>Tep.</th><th>Obloha</th>
                                {"".join([f"<th>{n}</th>" for n in VJAZDY.keys()])}
                                <th>Ryb.</th><th>Hosp.</th><th>Koll.</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
            </div>

            <div id="mapa" class="view-section">
                <h1 class="fw-bold mb-4">Mapa premávky v reálnom čase</h1>
                <iframe id="map" src="https://www.google.com/maps/embed?pb=!1m14!1m12!1m3!1d42436.52441618641!2d17.58!3d48.37!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!5e0!3m2!1ssk!2ssk!4v1700000000000!5m2!1ssk!2ssk&layer=t" allowfullscreen="" loading="lazy"></iframe>
                <p class="mt-3 text-muted">Poznámka: Google Mapy zobrazujú vrstvu premávky automaticky.</p>
            </div>

            <div id="analyzy" class="view-section">
                <h1 class="fw-bold mb-4">Analýza plynulosti dopravy</h1>
                <div class="chart-container">
                    <canvas id="trafficChart"></canvas>
                </div>
            </div>
        </div>

        <script>
            function showSection(sectionId, element) {{
                document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                document.getElementById(sectionId).classList.add('active');
                element.classList.add('active');
            }}

            // Chart.js inicializácia
            const ctx = document.getElementById('trafficChart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(chart_labels)},
                    datasets: [
                        {{
                            label: 'Plynulosť (priemer vjazdov %)',
                            data: {json.dumps([round(sum(v)/len(v), 1) for v in zip(*chart_data.values())] if chart_data else [])},
                            borderColor: '#1a73e8',
                            backgroundColor: 'rgba(26, 115, 232, 0.1)',
                            fill: true,
                            tension: 0.4
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    plugins: {{ legend: {{ display: true }} }},
                    scales: {{ y: {{ min: 0, max: 100 }} }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html_content)

if __name__ == "__main__": zber_dat()

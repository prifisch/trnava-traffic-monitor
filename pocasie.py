import requests
import pandas as pd
import os
from datetime import datetime
import pytz
import json
import math

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY")

VJAZDY = {
    "Zelenec": ["48.355516,17.589261", "48.356335,17.589057", "48.356964,17.588853"], 
    "Bučany": ["48.389916,17.612661", "48.388458,17.610547", "48.386428,17.607608"],
    "Zavar": ["48.375676,17.621206", "48.375335,17.620377", "48.374291,17.618204"]
    "B.Kostol": ["48.375448,17.564437", "48.376036,17.565585", "48.376354,17.566283"]
    "Suchá": ["48.388409,17.561065", "48.387410,17.563852", "48.386561,17.566270"]
    "Špačince": ["48.399354,17.599193", "48.398165,17.600461", "48.396505,17.598135"]
    "Ružindol": ["48.382510,17.562209", "48.382751,17.563569", "48.383202,17.565539"]
    "Boleráz": ["48.393661,17.562692", "48.392051,17.564344", "48.390284,17.566275"]
    "Nitrianska": ["48.360615,17.603516", "48.362222,17.602526", "48.363505,17.601650"]
    "Hrnčiarovce": ["48.351978,17.574577", "48.355227,17.576304", "48.357388,17.577477"]
}

YR_ICON_MAP = {
    "clearsky": "bi-sun", "fair": "bi-cloud-sun", "partlycloudy": "bi-cloud-sun",
    "cloudy": "bi-clouds", "rain": "bi-cloud-rain", "heavyrain": "bi-cloud-rain-heavy",
    "snow": "bi-snow", "fog": "bi-cloud-fog", "lightrain": "bi-cloud-drizzle"
}

# --- FUNKCIE (Zber dát) ---

import time # Nezabudni pridať import na začiatok súboru

def ziskaj_plynulost(zoznam_suradnic):
    # Ak by si poslal len jeden bod (string), premeníme ho na list, aby kód nezlyhal
    if isinstance(zoznam_suradnic, str):
        zoznam_suradnic = [zoznam_suradnic]
        
    hodnoty = []
    for bod in zoznam_suradnic:
        try:
            url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/12/json?key={TOMTOM_KEY}&point={bod}"
            res = requests.get(url, timeout=10).json()
            flow = res.get('flowSegmentData', {})
            
            # Výpočet: aktuálna rýchlosť / voľná rýchlosť
            current = flow.get('currentSpeed', 1)
            free = flow.get('freeFlowSpeed', 1)
            pomer = (current / free) * 100
            
            hodnoty.append(pomer)
            time.sleep(0.5) # Malá pauza pre stabilitu
        except Exception as e:
            print(f"Chyba pri bode {bod}: {e}")
            continue
    
    # Ak máme dáta, vrátime priemer, inak 100
    if hodnoty:
        return round(sum(hodnoty) / len(hodnoty), 1)
    return 100.0

def ziskaj_pocasi_yr():
    try:
        headers = {'User-Agent': 'TrnavaPulse/1.0 (https://github.com/prifisch/trnava-traffic-monitor)'}
        res = requests.get("https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=48.37&lon=17.58", headers=headers).json()
        data = res['properties']['timeseries'][0]['data']
        return data['instant']['details']['air_temperature'], data['next_1_hours']['summary']['symbol_code'].split('_')[0]
    except: return 0, "cloudy"

def ziskaj_parkovanie():
    url = "https://opendata.trnava.sk/api/v1/parkoviska"
    vysledok = {"Rybníková": None, "Hospodárska": None, "Kollárova": None}
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            data = response.json()
            for p in data:
                nazov = p.get('nazov', '')
                volne = p.get('volne_miesta')
                if "Rybníková" in nazov: vysledok["Rybníková"] = volne
                elif "Hospodárska" in nazov: vysledok["Hospodárska"] = volne
                elif "Kollárova" in nazov: vysledok["Kollárova"] = volne
        return vysledok
    except:
        return vysledok

# --- HLAVNÁ LOGIKA ---

def zber_dat():
    zona = pytz.timezone('Europe/Bratislava')
    teraz = datetime.now(zona)
    teplota, symbol = ziskaj_pocasi_yr()
    park = ziskaj_parkovanie()
    
    # 1. Zápis dát do Excelu
    novy_riadok = {"Čas": teraz.strftime("%Y-%m-%d %H:%M:%S"), "Teplota": teplota, "Symbol": symbol}
    for n, s in VJAZDY.items(): 
        novy_riadok[n] = ziskaj_plynulost(s)
    for n, v in park.items(): 
        novy_riadok[f"P_{n}"] = v

    excel_file = "data_trnava_komplet.xlsx"
    try:
        df = pd.read_excel(excel_file)
        df = pd.concat([df, pd.DataFrame([novy_riadok])], ignore_index=True)
    except: 
        df = pd.DataFrame([novy_riadok])
    
    df = df.dropna(subset=['Čas'])
    df.to_excel(excel_file, index=False)

    # 2. Príprava dát pre HTML
    df_chart = df.tail(20)
    chart_labels = [str(c).split(" ")[1][:5] if " " in str(c) else str(c)[:5] for c in df_chart['Čas']]
    chart_data = [round(df_chart[list(VJAZDY.keys())].iloc[i].mean(), 1) for i in range(len(df_chart))]

    rows_html = ""
    for _, r in df.tail(15).iloc[::-1].iterrows():
        cas = str(r['Čas']).split(" ")[1][:5] if " " in str(r['Čas']) else str(r['Čas'])[:5]
        
        traffic = ""
        for n in VJAZDY.keys():
            val = r.get(n, 0)
            if pd.isna(val):
                traffic += '<td>-</td>'
            else:
                pill_class = "status-green" if val > 85 else "status-orange" if val > 60 else "status-red"
                traffic += f'<td><span class="status-pill {pill_class}">{int(val)}%</span></td>'

        def fmt_p(val):
            try: return str(int(val)) if pd.notna(val) else "-"
            except: return "-"

        p_ryb = fmt_p(r.get('P_Rybníková'))
        p_hos = fmt_p(r.get('P_Hospodárska'))
        p_kol = fmt_p(r.get('P_Kollárova'))

        rows_html += f"""
        <tr>
            <td class="time-col">{cas}</td>
            <td class="fw-bold">{r.get('Teplota', '-')}°C</td>
            <td><i class="bi {YR_ICON_MAP.get(r.get('Symbol'), 'bi-cloud')}"></i></td>
            {traffic}
            <td>{p_ryb}</td>
            <td>{p_hos}</td>
            <td>{p_kol}</td>
        </tr>"""

# --- NOVÁ SEKCIA: PARKING INSIGHTS (Google Live Busyness) ---
    parking_insights = f"""
    <div class="row mt-5">
        <div class="col-12"><h3 class="fw-bold mb-4">Live vyťaženosť parkovísk (Google)</h3></div>
        
        <div class="col-md-4 mb-4">
            <div class="card-custom h-100 p-0">
                <div class="p-3 fw-bold border-bottom d-flex justify-content-between align-items-center">
                    Rybníková
                    <a href="https://www.google.com/maps/search/?api=1&query=Parkovisko+Rybnikova+Trnava" target="_blank" class="btn btn-sm btn-outline-primary py-0" style="font-size: 10px;">LIVE GRAF</a>
                </div>
                <iframe width="100%" height="200" style="border:0" allowfullscreen loading="lazy"
                    src="https://www.google.com/maps/embed/v1/place?key={GOOGLE_MAPS_KEY}&q=Parkovisko+Rybnikova+Trnava">
                </iframe>
            </div>
        </div>

        <div class="col-md-4 mb-4">
            <div class="card-custom h-100 p-0">
                <div class="p-3 fw-bold border-bottom d-flex justify-content-between align-items-center">
                    Hospodárska
                    <a href="https://www.google.com/maps/search/?api=1&query=Parkovisko+Hospodarska+Trnava" target="_blank" class="btn btn-sm btn-outline-primary py-0" style="font-size: 10px;">LIVE GRAF</a>
                </div>
                <iframe width="100%" height="200" style="border:0" allowfullscreen loading="lazy"
                    src="https://www.google.com/maps/embed/v1/place?key={GOOGLE_MAPS_KEY}&q=Parkovisko+Hospodarska+Trnava">
                </iframe>
            </div>
        </div>

        <div class="col-md-4 mb-4">
            <div class="card-custom h-100 p-0">
                <div class="p-3 fw-bold border-bottom d-flex justify-content-between align-items-center">
                    Kollárova
                    <a href="https://www.google.com/maps/search/?api=1&query=Parkovisko+Kollarova+Trnava" target="_blank" class="btn btn-sm btn-outline-primary py-0" style="font-size: 10px;">LIVE GRAF</a>
                </div>
                <iframe width="100%" height="200" style="border:0" allowfullscreen loading="lazy"
                    src="https://www.google.com/maps/embed/v1/place?key={GOOGLE_MAPS_KEY}&q=Parkovisko+Kollarova+Trnava">
                </iframe>
            </div>
        </div>
    </div>
    """

    # 3. HTML Content
    html_content = f"""
    <!DOCTYPE html>
    <html lang="sk">
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <title>TT-Pulse | Smart City</title>
        <style>
            :root {{ --primary: #1a73e8; --sidebar: #f8f9fa; }}
            body {{ background: #fff; font-family: 'Inter', sans-serif; display: flex; margin: 0; }}
            .sidebar {{ width: 280px; height: 100vh; background: var(--sidebar); position: fixed; border-right: 1px solid #eee; padding: 30px 20px; display: flex; flex-direction: column; }}
            .main {{ margin-left: 280px; width: 100%; min-height: 100vh; }}
            .top-bar {{ height: 70px; border-bottom: 1px solid #eee; display: flex; align-items: center; justify-content: space-between; padding: 0 40px; }}
            .content {{ padding: 40px; }}
            .nav-link {{ padding: 12px 15px; border-radius: 10px; color: #555; text-decoration: none; display: flex; align-items: center; gap: 12px; margin-bottom: 5px; cursor: pointer; }}
            .nav-link.active {{ background: #e8f0fe; color: var(--primary); font-weight: 600; }}
            .card-custom {{ background: #fff; border: 1px solid #eee; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); overflow: hidden; }}
            .status-pill {{ padding: 5px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; display: inline-block; min-width: 65px; text-align: center; }}
            .status-green {{ background: #e6f4ea; color: #1e8e3e; }}
            .status-orange {{ background: #fef7e0; color: #f9ab00; }}
            .status-red {{ background: #fce8e6; color: #d93025; }}
            .time-col {{ font-weight: 700; color: var(--primary); padding-left: 25px !important; text-align: left !important; }}
            .view-section {{ display: none; }}
            .view-section.active {{ display: block; }}
            .source-box {{ margin-top: auto; padding-top: 20px; border-top: 1px solid #ddd; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h3 class="text-primary fw-bold mb-4"><i class="bi bi-broadcast-pin"></i> TT-Pulse</h3>
            <div class="nav-link active" onclick="show('dash', this)"><i class="bi bi-grid-1x2"></i> Dashboard</div>
            <div class="nav-link" onclick="show('map', this)"><i class="bi bi-map"></i> Mapa mesta</div>
            <div class="nav-link" onclick="show('stats', this)"><i class="bi bi-graph-up"></i> Analýzy</div>
            <div class="source-box">
                <p class="small fw-bold text-muted mb-2">ZDROJE</p>
                <div class="small text-muted">YR.no, TomTom, OpenData TT</div>
            </div>
        </div>

        <div class="main">
            <div class="top-bar">
                <span class="fw-bold text-primary"><i class="bi bi-circle-fill small me-2"></i> LIVE MONITORING</span>
                <span class="text-muted small">Aktualizované: {teraz.strftime("%H:%M")}</span>
            </div>
            
            <div class="content">
                <div id="dash" class="view-section active">
                    <h2 class="fw-bold mb-4">Vjazdy do mesta</h2>
                    <div class="card-custom">
                        <table class="table table-hover mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th class="time-col">Čas</th><th>Tep.</th><th>Obloha</th>
                                    {"".join([f"<th>{n}</th>" for n in VJAZDY.keys()])}
                                    <th>Ryb.</th><th>Hosp.</th><th>Koll.</th>
                                </tr>
                            </thead>
                            <tbody>{rows_html}</tbody>
                        </table>
                    </div>

                    {parking_insights}
                </div>

                <div id="map" class="view-section">
                    <h2 class="fw-bold mb-4">Dopravná mapa Trnavy</h2>
                    <div class="card-custom">
                        <iframe 
                            width="100%" 
                            height="600" 
                            style="border:0" 
                            loading="lazy" 
                            allowfullscreen 
                            src="https://www.google.com/maps/embed?pb=!1m14!1m12!1m3!1d42456.456!2d17.58!3d48.37!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!5e0!3m2!1ssk!2ssk!4v123456789&layer=t4{GOOGLE_MAPS_KEY}&q=Trnava+Slovakia&layer=t">
                        </iframe>
                    </div>
                </div>

                <div id="stats" class="view-section">
                    <h2 class="fw-bold mb-4">Trend plynulosti</h2>
                    <div class="card-custom p-4">
                        <canvas id="trafficChart" height="100"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function show(id, el) {{
                document.querySelectorAll('.view-section').forEach(function(s) {{
                    s.classList.remove('active');
                }});
                document.getElementById(id).classList.add('active');
                document.querySelectorAll('.nav-link').forEach(function(l) {{
                    l.classList.remove('active');
                }});
                el.classList.add('active');
            }}

            new Chart(document.getElementById('trafficChart'), {{
                type: 'line',
                data: {{
                    labels: {json.dumps(chart_labels)},
                    datasets: [{{
                        label: 'Priemer plynulosti (%)',
                        data: {json.dumps(chart_data)},
                        borderColor: '#1a73e8',
                        fill: true,
                        backgroundColor: 'rgba(26, 115, 232, 0.1)',
                        tension: 0.4
                    }}]
                }},
                options: {{ scales: {{ y: {{ min: 0, max: 100 }} }} }}
            }});
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    zber_dat()

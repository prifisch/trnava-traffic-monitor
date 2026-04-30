import requests
import pandas as pd
import os
from datetime import datetime
import pytz
import json
import time

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY")

VJAZDY = {
    "Zelenec": ["48.355516,17.589261", "48.356335,17.589057", "48.356964,17.588853"], 
    "Bučany": ["48.389916,17.612661", "48.388458,17.610547", "48.386428,17.607608"],
    "Zavar": ["48.375676,17.621206", "48.375335,17.620377", "48.374291,17.618204"],
    "B.Kostol": ["48.375448,17.564437", "48.376036,17.565585", "48.376354,17.566283"],
    "Suchá": ["48.388409,17.561065", "48.387410,17.563852", "48.386561,17.566270"],
    "Špačince": ["48.399354,17.599193", "48.398165,17.600461", "48.396505,17.598135"],
    "Ružindol": ["48.382510,17.562209", "48.382751,17.563569", "48.383202,17.565539"],
    "Boleráz": ["48.393661,17.562692", "48.392051,17.564344", "48.390284,17.566275"],
    "Nitrianska": ["48.360615,17.603516", "48.362222,17.602526", "48.363505,17.601650"],
    "Hrnčiarovce": ["48.351978,17.574577", "48.355227,17.576304", "48.357388,17.577477"]
}

YR_ICON_MAP = {
    "clearsky": "bi-sun", "fair": "bi-cloud-sun", "partlycloudy": "bi-cloud-sun",
    "cloudy": "bi-clouds", "rain": "bi-cloud-rain", "heavyrain": "bi-cloud-rain-heavy",
    "snow": "bi-snow", "fog": "bi-cloud-fog", "lightrain": "bi-cloud-drizzle"
}

# --- FUNKCIE ---

def ziskaj_plynulost(zoznam_suradnic):
    if isinstance(zoznam_suradnic, str):
        zoznam_suradnic = [zoznam_suradnic]
    hodnoty = []
    for bod in zoznam_suradnic:
        try:
            url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/12/json?key={TOMTOM_KEY}&point={bod}"
            res = requests.get(url, timeout=10).json()
            flow = res.get('flowSegmentData', {})
            current = flow.get('currentSpeed', 1)
            free = flow.get('freeFlowSpeed', 1)
            pomer = (current / free) * 100
            hodnoty.append(pomer)
            time.sleep(0.3)
        except:
            continue
    return round(sum(hodnoty) / len(hodnoty), 1) if hodnoty else 100.0

def vypocitaj_historicke_normy(df):
    try:
        temp_df = df.copy()
        temp_df['dt'] = pd.to_datetime(temp_df['Čas'])
        temp_df['weekday'] = temp_df['dt'].dt.weekday
        temp_df['time_slot'] = temp_df['dt'].dt.strftime('%H:%M')
        
        vjazdy_cols = [col for col in VJAZDY.keys() if col in temp_df.columns]
        if not vjazdy_cols: return {}

        # Priemerná plynulosť mesta pre daný čas v týždni
        normy = temp_df.groupby(['weekday', 'time_slot'])[vjazdy_cols].mean().mean(axis=1)
        
        normy_dict = {}
        for (wd, ts), val in normy.items():
            wd_str = str(int(wd))
            if wd_str not in normy_dict: normy_dict[wd_str] = {}
            normy_dict[wd_str][ts] = round(val, 1)
        return normy_dict
    except Exception as e:
        print(f"Chyba normy: {e}")
        return {}

def ziskaj_pocasi_yr():
    try:
        headers = {'User-Agent': 'TrnavaPulse/1.0'}
        res = requests.get("https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=48.37&lon=17.58", headers=headers).json()
        data = res['properties']['timeseries'][0]['data']
        return data['instant']['details']['air_temperature'], data['next_1_hours']['summary']['symbol_code'].split('_')[0]
    except: return 0, "cloudy"

def ziskaj_parkovanie():
    url = "https://opendata.trnava.sk/api/v1/parkoviska"
    vysledok = {"Rybníková": None, "Hospodárska": None, "Kollárova": None}
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        data = response.json()
        for p in data:
            nazov = p.get('nazov', '')
            volne = p.get('volne_miesta')
            if "Rybníková" in nazov: vysledok["Rybníková"] = volne
            elif "Hospodárska" in nazov: vysledok["Hospodárska"] = volne
            elif "Kollárova" in nazov: vysledok["Kollárova"] = volne
        return vysledok
    except: return vysledok

# --- HLAVNÁ LOGIKA ---

def zber_dat():
    zona = pytz.timezone('Europe/Bratislava')
    teraz = datetime.now(zona)
    teplota, symbol = ziskaj_pocasi_yr()
    park = ziskaj_parkovanie()
    
    # 1. Zber aktuálnych dát
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

    # 2. Výpočet noriem a príprava dát pre graf
    historicke_normy = vypocitaj_historicke_normy(df)
    
    df_chart = df.tail(24) # Posledných 12 hodín (pri 30min intervale)
    chart_labels = [str(c).split(" ")[1][:5] if " " in str(c) else str(c)[:5] for c in df_chart['Čas']]
    chart_data = [round(df_chart[list(VJAZDY.keys())].iloc[i].mean(), 1) for i in range(len(df_chart))]

    rows_html = ""
    for _, r in df.tail(15).iloc[::-1].iterrows():
        cas = str(r['Čas']).split(" ")[1][:5] if " " in str(r['Čas']) else str(r['Čas'])[:5]
        traffic = ""
        for n in VJAZDY.keys():
            val = r.get(n, 0)
            pill_class = "status-green" if val > 85 else "status-orange" if val > 60 else "status-red"
            traffic += f'<td><span class="status-pill {pill_class}">{int(val) if pd.notna(val) else "-"}%</span></td>'

        rows_html += f"""
        <tr>
            <td class="time-col">{cas}</td>
            <td class="fw-bold">{r.get('Teplota', '-')}°C</td>
            <td><i class="bi {YR_ICON_MAP.get(r.get('Symbol'), 'bi-cloud')}"></i></td>
            {traffic}
            <td>{int(r.get('P_Rybníková')) if pd.notna(r.get('P_Rybníková')) else "-"}</td>
            <td>{int(r.get('P_Hospodárska')) if pd.notna(r.get('P_Hospodárska')) else "-"}</td>
            <td>{int(r.get('P_Kollárova')) if pd.notna(r.get('P_Kollárova')) else "-"}</td>
        </tr>"""

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
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h3 class="text-primary fw-bold mb-4"><i class="bi bi-broadcast-pin"></i> TT-Pulse</h3>
            <div class="nav-link active" onclick="show('dash', this)"><i class="bi bi-grid-1x2"></i> Dashboard</div>
            <div class="nav-link" onclick="show('map', this)"><i class="bi bi-map"></i> Mapa mesta</div>
            <div class="nav-link" onclick="show('stats', this)"><i class="bi bi-graph-up"></i> Analýzy</div>
            <div class="mt-auto small text-muted border-top pt-3">YR.no, TomTom, OpenData TT</div>
        </div>

        <div class="main">
            <div class="top-bar">
                <span class="fw-bold text-primary"><i class="bi bi-circle-fill small me-2"></i> LIVE MONITORING</span>
                <span class="text-muted small">Dnes: {teraz.strftime("%d.%m.%Y %H:%M")}</span>
            </div>
            
            <div class="content">
                <div id="dash" class="view-section active">
                    <h2 class="fw-bold mb-4">Vjazdy do mesta</h2>
                    <div class="card-custom">
                        <table class="table table-hover mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th class="time-col">Čas</th><th>Tep.</th><th>Oblač.</th>
                                    {"".join([f"<th>{n}</th>" for n in VJAZDY.keys()])}
                                    <th>Ryb.</th><th>Hosp.</th><th>Koll.</th>
                                </tr>
                            </thead>
                            <tbody>{rows_html}</tbody>
                        </table>
                    </div>
                </div>

                <div id="map" class="view-section">
                    <h2 class="fw-bold mb-4">Dopravná mapa Trnavy</h2>
                    <div class="card-custom">
                        <iframe width="100%" height="600" style="border:0" src="https://www.google.com/maps/embed/v1/place?key={GOOGLE_MAPS_KEY}&q=Trnava+Slovakia&layer=t"></iframe>
                    </div>
                </div>

                <div id="stats" class="view-section">
                    <h2 class="fw-bold mb-4">Aktuálna plynulosť vs. Historický priemer</h2>
                    <div class="card-custom p-4">
                        <canvas id="trafficChart" height="100"></canvas>
                        <p class="mt-3 small text-muted">Historický priemer sa vypočítava z tvojich doteraz zozbieraných dát pre rovnaký deň v týždni a čas.</p>
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

            const todayWD = new Date().getDay() === 0 ? 6 : new Date().getDay() - 1;
            const normy = {json.dumps(historicke_normy)};
            const labels = {json.dumps(chart_labels)};
            const histData = labels.map(l => (normy[todayWD] && normy[todayWD][l]) ? normy[todayWD][l] : null);

            new Chart(document.getElementById('trafficChart'), {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [
                        {{
                            label: 'Dnešná plynulosť (%)',
                            data: {json.dumps(chart_data)},
                            borderColor: '#1a73e8',
                            backgroundColor: 'rgba(26, 115, 232, 0.1)',
                            fill: true, tension: 0.4
                        }},
                        {{
                            label: 'Historický priemer (%)',
                            data: histData,
                            borderColor: '#adb5bd',
                            borderDash: [5, 5],
                            fill: false, tension: 0.4
                        }}
                    ]
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

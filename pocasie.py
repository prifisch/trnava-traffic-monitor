import requests
import pandas as pd
import os
from datetime import datetime
import pytz
import json

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")

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

# --- POMOCNÉ FUNKCIE ---

def ziskaj_plynulost(suradnice):
    try:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/12/json?key={TOMTOM_KEY}&point={suradnice}"
        res = requests.get(url, timeout=10).json()
        return round((res['flowSegmentData'].get('currentSpeed', 1) / res['flowSegmentData'].get('freeFlowSpeed', 1)) * 100, 1)
    except:
        return 100

def ziskaj_pocasi_yr():
    try:
        headers = {'User-Agent': 'TrnavaPulse/1.0 (https://github.com/vas-repo)'}
        res = requests.get("https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=48.37&lon=17.58", headers=headers, timeout=10).json()
        data = res['properties']['timeseries'][0]['data']
        temp = data['instant']['details']['air_temperature']
        sym = data['next_1_hours']['summary']['symbol_code'].split('_')[0]
        return temp, sym
    except Exception as e:
        print(f"Chyba pocasia: {e}")
        return 0, "cloudy"

def ziskaj_parkovanie():
    res = {"Rybníková": "N/A", "Hospodárska": "N/A", "Kollárova": "N/A"}
    try:
        data = requests.get("https://opendata.trnava.sk/api/v1/parkings", timeout=10).json()
        for p in data['features']:
            name = p['properties']['name']
            val = p['properties']['free_places']
            for k in res.keys():
                if k in name: res[k] = val
        return res
    except:
        return res

# --- HLAVNÁ FUNKCIA ZBERU ---

def zber_dat():
    zona = pytz.timezone('Europe/Bratislava')
    teraz = datetime.now(zona)
    teplota, symbol = ziskaj_pocasi_yr()
    park = ziskaj_parkovanie()
    
    # Príprava riadku
    novy_riadok = {"Čas": teraz.strftime("%Y-%m-%d %H:%M:%S"), "Teplota": teplota, "Symbol": symbol}
    for n, s in VJAZDY.items(): 
        novy_riadok[n] = ziskaj_plynulost(s)
    for n, v in park.items(): 
        novy_riadok[f"P_{n}"] = v

    # Uloženie do Excelu
    excel_file = "data_trnava_komplet.xlsx"
    try:
        df = pd.read_excel(excel_file)
        df = pd.concat([df, pd.DataFrame([novy_riadok])], ignore_index=True)
    except: 
        df = pd.DataFrame([novy_riadok])
    df.to_excel(excel_file, index=False)

    # Príprava dát pre Dashboard
    df_chart = df.tail(20)
    chart_labels = []
    for c in df_chart['Čas']:
        s = str(c)
        chart_labels.append(s.split(" ")[1][:5] if " " in s else s[:5])
    
    chart_data = {n: df_chart[n].fillna(100).tolist() for n in VJAZDY.keys()}
    priemer_plynulosti = [round(sum(v)/len(v), 1) for v in zip(*chart_data.values())]

    rows_html = ""
    for _, r in df.tail(15).iloc[::-1].iterrows():
        s_cas = str(r['Čas'])
        cas_short = s_cas.split(" ")[1][:5] if " " in s_cas else s_cas[:5]
        traffic = "".join([f'<td><span class="status-pill {"status-green" if r[n]>85 else "status-orange" if r[n]>60 else "status-red"}">{r[n]}%</span></td>' for n in VJAZDY.keys()])
        p_ryb = r.get('P_Rybníková', 'N/A')
        p_hosp = r.get('P_Hospodárska', 'N/A')
        p_koll = r.get('P_Kollárova', 'N/A')
        rows_html += f'<tr><td class="time-col">{cas_short}</td><td class="fw-bold text-center">{r["Teplota"]}°</td><td class="text-center"><i class="bi {YR_ICON_MAP.get(r["Symbol"], "bi-cloud")}"></i></td>{traffic}<td>{p_ryb}</td><td>{p_hosp}</td><td>{p_koll}</td></tr>'

    # Generovanie HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="sk">
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <title>TrnavaPulse</title>
        <style>
            :root {{ --primary: #1a73e8; --bg: #f8f9fa; }}
            body {{ background: var(--bg); font-family: 'Inter', sans-serif; display: flex; }}
            .sidebar {{ width: 260px; height: 100vh; background: #fff; position: fixed; border-right: 1px solid #e0e0e0; padding: 32px 16px; }}
            .main-content {{ margin-left: 260px; width: 100%; }}
            .top-bar {{ height: 64px; background: #fff; border-bottom: 1px solid #e0e0e0; display: flex; align-items: center; justify-content: space-between; padding: 0 40px; }}
            .data-card {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); overflow: hidden; margin: 40px; }}
            .status-pill {{ padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; }}
            .status-green {{ background: #e6f4ea; color: #1e8e3e; }}
            .status-orange {{ background: #fef7e0; color: #f9ab00; }}
            .status-red {{ background: #fce8e6; color: #d93025; }}
            .time-col {{ font-weight: 700; color: var(--primary); padding-left: 24px !important; }}
            .nav-item {{ padding: 12px; border-radius: 8px; color: #5f6368; cursor: pointer; text-decoration: none; display: block; }}
            .nav-item.active {{ background: #e8f0fe; color: var(--primary); font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="h4 fw-bold text-primary mb-4"><i class="bi bi-geo-alt-fill"></i> TT-Pulse</div>
            <div class="nav-item active" onclick="showSection('dashboard', this)"><i class="bi bi-grid-1x2 me-2"></i> Dashboard</div>
            <div class="nav-item" onclick="showSection('mapa', this)"><i class="bi bi-map me-2"></i> Mapa mesta</div>
        </div>
        <div class="main-content">
            <div class="top-bar">
                <span class="fw-bold">Trnava, SR</span>
                <span class="text-muted small">{teraz.strftime("%d. %m. %Y %H:%M")}</span>
            </div>
            <div id="dashboard" class="view-section">
                <div class="data-card">
                    <table class="table table-hover mb-0">
                        <thead class="table-light">
                            <tr>
                                <th class="time-col">Čas</th><th>Tepl.</th><th>Obloha</th>
                                {"".join([f"<th>{n}</th>" for n in VJAZDY.keys()])}
                                <th>Ryb.</th><th>Hosp.</th><th>Koll.</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
            </div>
            <div id="mapa" class="view-section d-none">
                <div class="data-card p-0">
                    <iframe width="100%" height="600" src="https://www.google.com/maps/embed?pb=!1m14!1m12!1m3!1d42484.73357591605!2d17.58!3d48.37!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!5e0!3m2!1ssk!2ssk!4v1700000000000!5m2!1ssk!2ssk&layer=t" style="border:0;" allowfullscreen=""></iframe>
                </div>
            </div>
        </div>
        <script>
            function showSection(id, el) {{
                document.querySelectorAll('.view-section').forEach(s => s.classList.add('d-none'));
                document.getElementById(id).classList.remove('d-none');
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                el.classList.add('active');
            }}
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    zber_dat()

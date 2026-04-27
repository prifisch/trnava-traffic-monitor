import requests
import pandas as pd
import os
from datetime import datetime
import pytz
import json

# --- KONFIGURÁCIA & FUNKCIE (zostávajú rovnaké) ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")
VJAZDY = {
    "Zelenec": "48.3615,17.5855", "Bučany": "48.3932,17.6105", "Zavar": "48.3735,17.6255",
    "B. Kostol": "48.3711,17.5512", "Suchá": "48.3885,17.5312", "Špačince": "48.4055,17.6012",
    "Ružindol": "48.3585,17.5355", "Boleráz": "48.4025,17.5511", "Nitrianska": "48.3725,17.6055",
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
        return round((res['flowSegmentData'].get('currentSpeed', 1) / res['flowSegmentData'].get('freeFlowSpeed', 1)) * 100, 1)
    except: return 100

# ... (ostatné funkcie ziskaj_pocasi_yr a ziskaj_parkovanie ponechaj)

def zber_dat():
    zona = pytz.timezone('Europe/Bratislava')
    teraz = datetime.now(zona) # TU SA DEFINUJE 'teraz'
    teplota, symbol = ziskaj_pocasi_yr()
    park = ziskaj_parkovanie()
    
    # 1. Uloženie dát do Excelu
    novy_riadok = {"Čas": teraz.strftime("%Y-%m-%d %H:%M:%S"), "Teplota": teplota, "Symbol": symbol}
    for n, s in VJAZDY.items(): novy_riadok[n] = ziskaj_plynulost(s)
    for n, v in park.items(): novy_riadok[f"P_{n}"] = v

    excel_file = "data_trnava_komplet.xlsx"
    try:
        df = pd.read_excel(excel_file)
        df = pd.concat([df, pd.DataFrame([novy_riadok])], ignore_index=True)
    except: df = pd.DataFrame([novy_riadok])
    df.to_excel(excel_file, index=False)

    # 2. Príprava dát pre HTML (všetko musí byť pod definíciou 'teraz')
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
        park_vals = "".join([f'<td><span class="fw-bold">{r[f"P_{n}"]}</span></td>' for n in ["Rybníková", "Hospodárska", "Kollárova"]])
        rows_html += f'<tr><td class="time-col">{cas_short}</td><td class="fw-bold">{r["Teplota"]}°</td><td><i class="bi {YR_ICON_MAP.get(r["Symbol"], "bi-cloud")}"></i></td>{traffic}{park_vals}</tr>'

    # 3. HTML kód s vložením premennej 'teraz'
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
            /* Tu vlož tie moderné CSS štýly, ktoré sme ladili minule */
            :root {{ --sidebar-bg: #f8f9fa; --primary-color: #1a73e8; }}
            body {{ background: #fff; font-family: sans-serif; display: flex; }}
            .sidebar {{ width: 260px; height: 100vh; background: var(--sidebar-bg); position: fixed; border-right: 1px solid #e0e0e0; padding: 32px 16px; }}
            .main-content {{ margin-left: 260px; width: 100%; }}
            .top-bar {{ height: 64px; border-bottom: 1px solid #e0e0e0; display: flex; align-items: center; justify-content: space-between; padding: 0 40px; }}
            .status-pill {{ padding: 5px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; display: inline-block; }}
            .status-green {{ background: #e6f4ea; color: #1e8e3e; }}
            .status-orange {{ background: #fef7e0; color: #f9ab00; }}
            .status-red {{ background: #fce8e6; color: #d93025; }}
            .time-col {{ font-weight: 700; color: #1a73e8; padding-left: 24px !important; text-align: left !important; }}
            .data-card {{ background: white; border: 1px solid #e0e0e0; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); overflow: hidden; margin: 40px; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="h4 fw-bold text-primary mb-4">TT-Pulse</div>
            <div class="nav-item active"><i class="bi bi-grid-1x2 me-2"></i> Dashboard</div>
        </div>
        <div class="main-content">
            <div class="top-bar">
                <span class="fw-bold">Trnava, Slovakia</span>
                <span class="small text-muted">{teraz.strftime("%d. %m. %Y %H:%M")}</span>
            </div>
            <div class="p-5">
                <h1 class="fw-bold mb-4">Dashboard</h1>
                <div class="data-card">
                    <table class="table table-hover mb-0">
                        <thead>
                            <tr>
                                <th class="time-col">Čas</th><th>Tep.</th><th>Obloha</th>
                                {"".join([f"<th>{n}</th>" for n in VJAZDY.keys()])}
                                <th>Ryb.</th><th>Hosp.</th><th>Koll.</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    zber_dat()

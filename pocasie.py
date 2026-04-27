import requests
import pandas as pd
import os
from datetime import datetime
import pytz

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")

VJAZDY = {
    "Zdrzanie_Zelenec (min)": "48.3615,17.5855",
    "Zdrzanie_Bucany (min)": "48.3932,17.6105",
    "Zdrzanie_Zavar (min)": "48.3735,17.6255",
    "Zdrzanie_Biely_Kostol (min)": "48.3711,17.5512",
    "Zdrzanie_Sucha (min)": "48.3885,17.5312",
    "Zdrzanie_Spacince (min)": "48.4055,17.6012",
    "Zdrzanie_Ruzindol (min)": "48.3585,17.5355",
    "Zdrzanie_Boleraz (min)": "48.4025,17.5511",
    "Zdrzanie_Nitrianska (min)": "48.3725,17.6055",
    "Zdrzanie_Hrnciarovce (min)": "48.3555,17.5755"
}

YR_ICON_MAP = {
    "clearsky": "bi-sun", "fair": "bi-cloud-sun", "partlycloudy": "bi-cloud-sun",
    "cloudy": "bi-clouds", "rain": "bi-cloud-rain", "heavyrain": "bi-cloud-rain-heavy",
    "rainshowers": "bi-cloud-drizzle", "thunder": "bi-cloud-lightning",
    "snow": "bi-snow", "fog": "bi-cloud-fog", "sleet": "bi-cloud-hail",
    "lightrain": "bi-cloud-drizzle", "lightrainshowers": "bi-cloud-drizzle"
}

YR_PREKLAD = {
    "clearsky": "Jasno", "fair": "Skoro jasno", "partlycloudy": "Polooblačno",
    "cloudy": "Oblačno", "rain": "Dážď", "heavyrain": "Silný dážď",
    "rainshowers": "Prehánky", "thunder": "Búrky", "snow": "Sneženie",
    "fog": "Hmla", "sleet": "Dážď so snehom", "lightrain": "Slabý dážď"
}

def ziskaj_plynulost(nazov, suradnice):
    try:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/12/json?key={TOMTOM_KEY}&point={suradnice}"
        res = requests.get(url, timeout=10).json()
        flow = res.get('flowSegmentData', {})
        current = flow.get('currentSpeed', 1)
        free = flow.get('freeFlowSpeed', 1)
        return round((current / free) * 100, 2)
    except: return 100

def ziskaj_pocasi_yr():
    try:
        lat, lon = 48.3775, 17.5883
        url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"
        headers = {'User-Agent': 'TrnavaMonitor/1.0'}
        res = requests.get(url, headers=headers, timeout=10).json()
        current = res['properties']['timeseries'][0]['data']
        teplota = current['instant']['details']['air_temperature']
        symbol_kod = current['next_1_hours']['summary']['symbol_code']
        cisty_symbol = symbol_kod.split('_')[0]
        popis = YR_PREKLAD.get(cisty_symbol, cisty_symbol.capitalize())
        return teplota, cisty_symbol, popis
    except: return 0, "cloudy", "Neznáme"

def ziskaj_vsetky_parkoviska():
    vysledok = {"Rybníková": "N/A", "Hospodárska": "N/A", "Kollárova": "N/A"}
    try:
        url = "https://opendata.trnava.sk/api/v1/parkings"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10).json()
        for p in res.get('features', []):
            prop = p.get('properties', {})
            meno = prop.get('name', '')
            volne = prop.get('free_places')
            if "Rybníková" in meno: vysledok["Rybníková"] = volne if volne is not None else "N/A"
            elif "Hospodárska" in meno: vysledok["Hospodárska"] = volne if volne is not None else "N/A"
            elif "Kollárova" in meno: vysledok["Kollárova"] = volne if volne is not None else "N/A"
        return vysledok
    except: return vysledok

def zber_dat():
    zona = pytz.timezone('Europe/Bratislava')
    cas_dt = datetime.now(zona)
    cas_zberu = cas_dt.strftime("%Y-%m-%d %H:%M:%S")
    
    teplota, symbol, popis = ziskaj_pocasi_yr()
    novy_riadok = {"Čas zberu": cas_zberu, "Teplota (°C)": teplota, "Počasie": popis, "Ikona": symbol}

    for nazov, suradnice in VJAZDY.items():
        novy_riadok[nazov] = ziskaj_plynulost(nazov, suradnice)

    parkoviska = ziskaj_vsetky_parkoviska()
    novy_riadok["P_Rybnikova"] = parkoviska["Rybníková"]
    novy_riadok["P_Hospodarska"] = parkoviska["Hospodárska"]
    novy_riadok["P_Kollarova"] = parkoviska["Kollárova"]

    try:
        df = pd.read_excel("data_trnava_komplet.xlsx")
        df = pd.concat([df, pd.DataFrame([novy_riadok])], ignore_index=True)
    except:
        df = pd.DataFrame([novy_riadok])

    df.to_excel("data_trnava_komplet.xlsx", index=False)
    
    df_web = df.tail(10).copy()
    vjazdy_cols = [c for c in df_web.columns if "Zdrzanie_" in c]
    ciste_nazvy_vjazdy = [c.replace("Zdrzanie_", "").replace(" (min)", "") for c in vjazdy_cols]
    park_cols = ["P_Rybnikova", "P_Hospodarska", "P_Kollarova"]

    def ofarbi_dot(val):
        if isinstance(val, (int, float)):
            if val >= 90: return "#4fd1c5" # Teal
            elif val >= 60: return "#f6ad55" # Orange
            return "#f56565" # Red
        return "#e2e8f0"

    rows_html = ""
    for _, row in df_web.iterrows():
        icon_class = YR_ICON_MAP.get(row['Ikona'], "bi-cloud")
        t = datetime.strptime(row['Čas zberu'], "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
        
        rows_html += f"""
        <tr>
            <td style="font-weight:600; color:#2d3748;">{t}</td>
            <td style="font-weight:700;">{row['Teplota (°C)']}°C</td>
            <td><i class="bi {icon_class}" style="font-size:1.2rem;"></i></td>
            {"".join([f'<td><span class="status-dot" style="background:{ofarbi_dot(row[col])}"></span>{row[col]}%</td>' for col in vjazdy_cols])}
            {"".join([f'<td><span class="park-pill">{row[col]}</span></td>' for col in park_cols])}
        </tr>"""

    html_content = f"""
    <!DOCTYPE html>
    <html lang="sk">
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <title>Trnava Logip Dashboard</title>
        <style>
            body {{ background-color: #f7f9fc; font-family: 'Inter', sans-serif; color: #1a202c; }}
            .sidebar {{ width: 240px; height: 100vh; background: #fff; position: fixed; padding: 30px 20px; border-right: 1px solid #e2e8f0; }}
            .main-content {{ margin-left: 240px; padding: 40px; }}
            .logo {{ font-weight: 800; font-size: 1.5rem; display: flex; align-items: center; gap: 10px; margin-bottom: 50px; }}
            .nav-link {{ color: #718096; font-weight: 500; padding: 12px 15px; border-radius: 12px; margin-bottom: 5px; display: block; text-decoration: none; }}
            .nav-link.active {{ background: #f7f9fc; color: #1a202c; }}
            .nav-link i {{ margin-right: 12px; }}
            
            .header-flex {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
            .card-stat {{ background: #fff; border-radius: 20px; padding: 25px; border: 1px solid #e2e8f0; height: 100%; }}
            .stat-label {{ color: #718096; font-size: 0.85rem; font-weight: 600; margin-bottom: 10px; display: block; }}
            .stat-value {{ font-size: 1.8rem; font-weight: 800; }}
            
            .table-card {{ background: #fff; border-radius: 24px; padding: 30px; border: 1px solid #e2e8f0; margin-top: 30px; }}
            .custom-table {{ width: 100%; border-collapse: collapse; }}
            .custom-table th {{ color: #a0aec0; font-size: 0.75rem; text-transform: uppercase; padding: 15px 10px; font-weight: 700; text-align: center; border-bottom: 1px solid #edf2f7; }}
            .custom-table td {{ padding: 20px 10px; border-bottom: 1px solid #edf2f7; font-size: 0.85rem; text-align: center; }}
            
            .status-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 8px; }}
            .park-pill {{ background: #edf2f7; padding: 5px 12px; border-radius: 8px; font-weight: 700; font-size: 0.8rem; }}
            .upgrade-box {{ background: #edf2f7; border-radius: 20px; padding: 20px; margin-top: auto; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="sidebar d-none d-lg-block">
            <div class="logo"><i class="bi bi-grid-fill text-primary"></i> TT-Logip</div>
            <a href="#" class="nav-link active"><i class="bi bi-house"></i> Dashboard</a>
            <a href="#" class="nav-link"><i class="bi bi-map"></i> Mapa mesta</a>
            <a href="#" class="nav-link"><i class="bi bi-bar-chart"></i> Analýzy</a>
            <a href="#" class="nav-link"><i class="bi bi-gear"></i> Nastavenia</a>
            
            <div class="upgrade-box" style="margin-top: 150px;">
                <p style="font-weight:700; font-size:0.9rem; margin-bottom:5px;">Trnava Monitor</p>
                <p style="font-size:0.75rem; color:#718096;">Live dáta z mestskej infraštruktúry</p>
            </div>
        </div>

        <div class="main-content">
            <div class="header-flex">
                <div>
                    <h2 style="font-weight:800;">Ahoj, Trnava! 👋</h2>
                    <p style="color:#718096; margin:0;">Tu je aktuálny stav tvojich ulíc a parkovísk.</p>
                </div>
                <div style="text-align:right;">
                    <span style="font-weight:700;">{cas_dt.strftime("%d. %B %Y")}</span><br>
                    <span class="badge bg-light text-dark border">{cas_zberu}</span>
                </div>
            </div>

            <div class="row g-4">
                <div class="col-md-4">
                    <div class="card-stat">
                        <span class="stat-label">AKTUÁLNA TEPLOTA</span>
                        <div class="d-flex align-items-center gap-3">
                            <div class="stat-value">{teplota}°C</div>
                            <i class="bi {YR_ICON_MAP.get(symbol, 'bi-cloud')}" style="font-size:2rem; color:#4a5568;"></i>
                        </div>
                        <span style="color:#4fd1c5; font-size:0.8rem; font-weight:700;">{popis}</span>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card-stat">
                        <span class="stat-label">PARKOVISKO RYBNÍKOVÁ</span>
                        <div class="stat-value text-primary">{parkoviska['Rybníková']}</div>
                        <span style="color:#718096; font-size:0.8rem;">voľných miest</span>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card-stat">
                        <span class="stat-label">NAJHORŠÍ VJAZD</span>
                        <div class="stat-value" style="color:#f56565;">{min(novy_riadok[c] for c in vjazdy_cols)}%</div>
                        <span style="color:#718096; font-size:0.8rem;">minimálna plynulosť</span>
                    </div>
                </div>
            </div>

            <div class="table-card">
                <h5 style="font-weight:800; margin-bottom:25px;">História monitoringu</h5>
                <div class="table-responsive">
                    <table class="custom-table">
                        <thead>
                            <tr>
                                <th>Čas</th><th>Teplota</th><th>Obloha</th>
                                {"".join([f"<th>{n}</th>" for n in ciste_nazvy_vjazdy])}
                                <th>Rybníková</th><th>Hosp.</th><th>Kollár.</th>
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
    with open("index.html", "w", encoding="utf-8") as f: f.write(html_content)

if __name__ == "__main__": zber_dat()

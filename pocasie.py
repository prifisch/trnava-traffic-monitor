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
    cas_zberu = datetime.now(zona).strftime("%Y-%m-%d %H:%M:%S")
    
    teplota, symbol, popis = ziskaj_pocasi_yr()
    novy_riadok = {"Čas zberu": cas_zberu, "Teplota (°C)": teplota, "Počasie": popis, "Ikona": symbol}

    for nazov, suradnice in VJAZDY.items():
        novy_riadok[nazov] = ziskaj_plynulost(nazov, suradnice)

    parkoviska = ziskaj_vsetky_parkoviska()
    novy_riadok["P_Rybnikova"] = parkoviska["Rybníková"]
    novy_riadok["P_Hospodarska"] = parkoviska["Hospodárska"]
    novy_riadok["P_Kollarova"] = parkoviska["Kollárova"]

    poradie = [
        "Čas zberu", "Teplota (°C)", "Počasie", "Ikona",
        "Zdrzanie_Zelenec (min)", "Zdrzanie_Bucany (min)", "Zdrzanie_Zavar (min)",
        "Zdrzanie_Nitrianska (min)", "Zdrzanie_Hrnciarovce (min)", "Zdrzanie_Biely_Kostol (min)",
        "Zdrzanie_Sucha (min)", "Zdrzanie_Spacince (min)", "Zdrzanie_Ruzindol (min)",
        "Zdrzanie_Boleraz (min)", "P_Rybnikova", "P_Hospodarska", "P_Kollarova"
    ]

    try:
        df = pd.read_excel("data_trnava_komplet.xlsx")
        df = pd.concat([df, pd.DataFrame([novy_riadok])], ignore_index=True)
    except:
        df = pd.DataFrame([novy_riadok])

    df = df[poradie]
    df.to_excel("data_trnava_komplet.xlsx", index=False)
    
    df_web = df.tail(12).copy()
    vjazdy_cols = [c for c in df_web.columns if "Zdrzanie_" in c]
    ciste_nazvy_vjazdy = [c.replace("Zdrzanie_", "").replace(" (min)", "") for c in vjazdy_cols]
    park_cols = ["P_Rybnikova", "P_Hospodarska", "P_Kollarova"]

    def ofarbi_plynulost_dark(val):
        if isinstance(val, (int, float)):
            if val >= 90: color = "#00ffa3" # Neónová zelená
            elif val >= 60: color = "#ffea00" # Neónová žltá
            else: color = "#ff0055" # Neónová červená
            return f'<span style="color: {color}; font-weight: 800;">{val}%</span>'
        return val

    rows_html = ""
    for _, row in df_web.iterrows():
        icon_class = YR_ICON_MAP.get(row['Ikona'], "bi-cloud")
        time_display = datetime.strptime(row['Čas zberu'], "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
        
        rows_html += f"""<tr>
            <td class="time-cell">{time_display}</td>
            <td class="temp-cell">{row["Teplota (°C)"]}°</td>
            <td class="weather-cell"><i class="bi {icon_class}"></i></td>
            {"".join([f"<td>{ofarbi_plynulost_dark(row[col])}</td>" for col in vjazdy_cols])}
            {"".join([f"<td><span class='park-val'>{row[col]}</span></td>" for col in park_cols])}
        </tr>"""

    html_content = f"""
    <!DOCTYPE html>
    <html lang="sk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <title>Trnava Dark Hub</title>
        <style>
            :root {{
                --bg: #0b0e14;
                --card: #161b22;
                --accent: #7b42ff;
                --text: #e6edf3;
                --muted: #8b949e;
            }}
            body {{ 
                background-color: var(--bg); 
                color: var(--text); 
                font-family: 'Inter', -apple-system, sans-serif;
                padding: 20px;
            }}
            .glass-card {{
                background: var(--card);
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 24px;
                padding: 30px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.4);
            }}
            .header-zone {{ margin-bottom: 30px; }}
            .brand {{ font-weight: 900; letter-spacing: -1px; font-size: 1.8rem; background: linear-gradient(90deg, #fff, #7b42ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
            .status-chip {{ background: rgba(123, 66, 255, 0.1); border: 1px solid var(--accent); color: var(--accent); padding: 6px 16px; border-radius: 100px; font-size: 0.75rem; font-weight: 700; }}
            
            .main-table {{ width: 100%; border-collapse: separate; border-spacing: 0 8px; }}
            .main-table thead th {{ color: var(--muted); font-size: 0.65rem; text-transform: uppercase; letter-spacing: 1px; padding: 10px; border: 0; text-align: center; }}
            .main-table tbody tr {{ background: rgba(255,255,255,0.02); transition: 0.3s; }}
            .main-table tbody tr:hover {{ background: rgba(255,255,255,0.05); transform: scale(1.005); }}
            .main-table tbody td {{ padding: 16px 10px; border: 0; font-size: 0.85rem; text-align: center; color: var(--text); }}
            .main-table tbody td:first-child {{ border-top-left-radius: 12px; border-bottom-left-radius: 12px; }}
            .main-table tbody td:last-child {{ border-top-right-radius: 12px; border-bottom-right-radius: 12px; }}
            
            .time-cell {{ color: var(--accent) !important; font-weight: 800; }}
            .temp-cell {{ font-weight: 700; font-size: 1rem; }}
            .weather-cell i {{ font-size: 1.4rem; color: #fff; }}
            .park-val {{ background: #21262d; padding: 4px 10px; border-radius: 6px; font-weight: 700; color: #58a6ff; }}
            
            .footer {{ margin-top: 30px; color: var(--muted); font-size: 0.7rem; }}
            .legend-item {{ display: inline-flex; align-items: center; margin-right: 20px; }}
            .dot {{ width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }}
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <div class="glass-card">
                <div class="header-zone d-flex justify-content-between align-items-center flex-wrap gap-3">
                    <div>
                        <h1 class="brand">STAKENT® TRNAVA HUB</h1>
                        <p style="color: var(--muted); margin: 0; font-size: 0.8rem;">Live traffic and infrastructure monitoring</p>
                    </div>
                    <div class="status-chip">
                        <i class="bi bi-broadcast me-2"></i>LIVE: {cas_zberu}
                    </div>
                </div>

                <div class="table-responsive">
                    <table class="main-table">
                        <thead>
                            <tr>
                                <th class="text-start ps-4">Time</th>
                                <th>Temp</th>
                                <th>Sky</th>
                                {"".join([f"<th>{n}</th>" for n in ciste_nazvy_vjazdy])}
                                <th>Rybníková</th><th>Hospodárska</th><th>Kollárova</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>

                <div class="footer d-flex justify-content-between align-items-center flex-wrap">
                    <div>
                        <span class="legend-item"><span class="dot" style="background:#00ffa3"></span> Optimal</span>
                        <span class="legend-item"><span class="dot" style="background:#ffea00"></span> Busy</span>
                        <span class="legend-item"><span class="dot" style="background:#ff0055"></span> Jam</span>
                    </div>
                    <div>Powered by MET Norway & TomTom API</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html_content)

if __name__ == "__main__": zber_dat()

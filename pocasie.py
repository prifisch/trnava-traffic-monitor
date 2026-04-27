import requests
import pandas as pd
import os
from datetime import datetime
import pytz

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")

# Definícia vjazdov do Trnavy
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

# Mapovanie YR.no symbolov na Bootstrap Icons (monochromatické)
YR_ICON_MAP = {
    "clearsky": "bi-sun", "fair": "bi-cloud-sun", "partlycloudy": "bi-cloud-sun",
    "cloudy": "bi-clouds", "rain": "bi-cloud-rain", "heavyrain": "bi-cloud-rain-heavy",
    "rainshowers": "bi-cloud-drizzle", "thunder": "bi-cloud-lightning",
    "snow": "bi-snow", "fog": "bi-cloud-fog", "sleet": "bi-cloud-hail",
    "lightrain": "bi-cloud-drizzle", "lightrainshowers": "bi-cloud-drizzle"
}

# Prekladový slovník pre YR.no
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
    except:
        return 100

def ziskaj_pocasi_yr():
    try:
        lat, lon = 48.3775, 17.5883
        url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"
        headers = {'User-Agent': 'TrnavaMonitor/1.0 github.com/user'}
        res = requests.get(url, headers=headers, timeout=10).json()
        current = res['properties']['timeseries'][0]['data']
        teplota = current['instant']['details']['air_temperature']
        symbol_kod = current['next_1_hours']['summary']['symbol_code']
        cisty_symbol = symbol_kod.split('_')[0]
        popis = YR_PREKLAD.get(cisty_symbol, cisty_symbol.capitalize())
        return teplota, cisty_symbol, popis
    except:
        return 0, "cloudy", "Neznáme"

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
    except:
        return vysledok

def zber_dat():
    zona = pytz.timezone('Europe/Bratislava')
    cas_zberu = datetime.now(zona).strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Počasie
    teplota, symbol, popis = ziskaj_pocasi_yr()
    novy_riadok = {"Čas zberu": cas_zberu, "Teplota (°C)": teplota, "Počasie": popis, "Ikona": symbol}

    # 2. Doprava
    for nazov, suradnice in VJAZDY.items():
        novy_riadok[nazov] = ziskaj_plynulost(nazov, suradnice)

    # 3. Parkovanie
    parkoviska = ziskaj_vsetky_parkoviska()
    novy_riadok["P_Rybnikova"] = parkoviska["Rybníková"]
    novy_riadok["P_Hospodarska"] = parkoviska["Hospodárska"]
    novy_riadok["P_Kollarova"] = parkoviska["Kollárova"]

    # --- DATAFRAME A EXCEL ---
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
    
    # --- DASHBOARD GENERÁCIA (Moderný štýl) ---
    df_web = df.tail(15).copy()
    vjazdy_cols = [c for c in df_web.columns if "Zdrzanie_" in c]
    ciste_nazvy_vjazdy = [c.replace("Zdrzanie_", "").replace(" (min)", "") for c in vjazdy_cols]
    park_cols = ["P_Rybnikova", "P_Hospodarska", "P_Kollarova"]

    def ofarbi_plynulost_v2(val):
        if isinstance(val, (int, float)):
            if val >= 90: color, text = "rgba(40, 167, 69, 0.1)", "#1e7e34"
            elif val >= 60: color, text = "rgba(255, 193, 7, 0.15)", "#856404"
            else: color, text = "rgba(220, 53, 69, 0.1)", "#bd2130"
            return f'<span class="traffic-badge" style="background-color: {color}; color: {text};">{val}%</span>'
        return val

    rows_html = ""
    for _, row in df_web.iterrows():
        icon_class = YR_ICON_MAP.get(row['Ikona'], "bi-cloud")
        time_obj = datetime.strptime(row['Čas zberu'], "%Y-%m-%d %H:%M:%S")
        time_display = time_obj.strftime("%H:%M")
        
        rows_html += f"""<tr>
            <td class="time-cell">{time_display}</td>
            <td class="temp-cell">{row["Teplota (°C)"]}°C</td>
            <td class="weather-cell"><i class="bi {icon_class}"></i> {row["Počasie"]}</td>
            {"".join([f"<td>{ofarbi_plynulost_v2(row[col])}</td>" for col in vjazdy_cols])}
            {"".join([f"<td><span class='park-badge'>{row[col]}</span></td>" for col in park_cols])}
        </tr>"""

    html_table = f"""
    <table class="table table-hover app-table">
        <thead>
            <tr class="header-main">
                <th rowspan="2" class="align-middle text-start ps-4">Čas</th>
                <th rowspan="2" class="align-middle">Teplota</th>
                <th rowspan="2" class="align-middle">Obloha</th>
                <th colspan="{len(vjazdy_cols)}" class="traffic-header">Plynulosť dopravy (%)</th>
                <th colspan="3" class="park-header">Voľné miesta</th>
            </tr>
            <tr class="subheader">
                {"".join([f"<th>{n}</th>" for n in ciste_nazvy_vjazdy])}
                <th>Rybníková</th><th>Hospodárska</th><th>Kollárova</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>"""

    html_content = f"""
    <!DOCTYPE html>
    <html lang="sk">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <title>Trnava Smart Monitor</title>
        <style>
            :root {{ --bg: #f4f7fa; --card: #ffffff; --text: #2d3748; --primary: #1a365d; }}
            body {{ background-color: var(--bg); font-family: 'Segoe UI', system-ui, sans-serif; color: var(--text); padding-top: 20px; }}
            .main-card {{ 
                background: var(--card); border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); 
                margin: 0 auto; max-width: 98%; overflow: hidden; border: 1px solid #e2e8f0;
            }}
            .app-header {{ padding: 25px 30px; border-bottom: 1px solid #edf2f7; background: #fff; }}
            .app-title {{ font-weight: 800; color: var(--primary); letter-spacing: -0.5px; margin: 0; font-size: 1.5rem; }}
            .update-badge {{ background: #edf2f7; color: #4a5568; font-weight: 600; font-size: 0.75rem; padding: 8px 14px; border-radius: 8px; }}
            .app-table {{ margin: 0; width: 100%; }}
            .app-table thead {{ background: #f8fafc; }}
            .header-main th {{ font-size: 0.65rem; text-transform: uppercase; letter-spacing: 1px; color: #718096; padding: 15px 10px; border: 0; }}
            .subheader th {{ font-size: 0.6rem; color: #a0aec0; border-bottom: 1px solid #edf2f7; padding-bottom: 10px; }}
            .app-table tbody td {{ padding: 14px 10px; font-size: 0.8rem; border-bottom: 1px solid #f1f5f9; vertical-align: middle; text-align: center; }}
            .time-cell {{ text-align: left !important; padding-left: 30px !important; font-weight: 700; color: var(--primary); }}
            .temp-cell {{ font-weight: 700; color: #2d3748; }}
            .weather-cell {{ color: #4a5568; white-space: nowrap; }}
            .weather-cell i {{ font-size: 1.2rem; margin-right: 6px; vertical-align: middle; }}
            .traffic-badge {{ font-weight: 700; font-size: 0.75rem; padding: 5px 10px; border-radius: 6px; display: inline-block; min-width: 50px; }}
            .park-badge {{ background: #f1f5f9; color: var(--primary); font-weight: 700; padding: 5px 10px; border-radius: 6px; display: inline-block; min-width: 45px; }}
            .app-footer {{ padding: 20px 30px; background: #f8fafc; color: #718096; font-size: 0.75rem; }}
            .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px; }}
        </style>
    </head>
    <body>
        <div class="main-card">
            <div class="app-header d-flex justify-content-between align-items-center">
                <div>
                    <h2 class="app-title text-uppercase">Trnava Monitor</h2>
                    <span class="text-muted small">Mestský dashboard v reálnom čase</span>
                </div>
                <span class="update-badge"><i class="bi bi-arrow-repeat me-1"></i> {cas_zberu}</span>
            </div>
            <div class="table-responsive">
                {html_table}
            </div>
            <div class="app-footer d-flex justify-content-between align-items-center flex-wrap">
                <div class="d-flex gap-4">
                    <span><span class="legend-dot" style="background:#28a745"></span>Plynulá</span>
                    <span><span class="legend-dot" style="background:#ffc107"></span>Zhustená</span>
                    <span><span class="legend-dot" style="background:#dc3545"></span>Zápcha</span>
                </div>
                <div class="small">Zdroje: MET Norway, TomTom, Opendata Trnava</div>
            </div>
        </div>
    </body>
    </html>"""
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    zber_dat()

import requests
import pandas as pd
import os
from datetime import datetime
import pytz

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")
# OpenWeather kľúč už pre počasie nepotrebujeme, ale necháme ho tu, ak ho máš v Secrets
WEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")

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

# Mapovanie YR.no symbolov na Bootstrap Icons
YR_ICON_MAP = {
    "clearsky": "bi-sun", "fair": "bi-cloud-sun", "partlycloudy": "bi-cloud-sun",
    "cloudy": "bi-clouds", "rain": "bi-cloud-rain", "heavyrain": "bi-cloud-rain-heavy",
    "rainshowers": "bi-cloud-drizzle", "thunder": "bi-cloud-lightning",
    "snow": "bi-snow", "fog": "bi-cloud-fog", "sleet": "bi-cloud-hail",
    "lightrain": "bi-cloud-drizzle", "lightrainshowers": "bi-cloud-drizzle"
}

# Pomocný preklad YR.no stavov
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
        # Súradnice Trnavy pre YR.no
        lat, lon = 48.3775, 17.5883
        url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"
        headers = {'User-Agent': 'TrnavaTrafficMonitor/1.0 github.com/tvoj-user-tu'}
        res = requests.get(url, headers=headers, timeout=10).json()
        
        current = res['properties']['timeseries'][0]['data']
        teplota = current['instant']['details']['air_temperature']
        symbol_kod = current['next_1_hours']['summary']['symbol_code']
        
        # Očistíme symbol od prípony _day/_night
        cisty_symbol = symbol_kod.split('_')[0]
        popis = YR_PREKLAD.get(cisty_symbol, cisty_symbol.capitalize())
        
        return teplota, cisty_symbol, popis
    except Exception as e:
        print(f"Chyba YR.no: {e}")
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
    
    # 1. Počasie z YR.no
    teplota, symbol, popis = ziskaj_pocasi_yr()

    novy_riadok = {
        "Čas zberu": cas_zberu,
        "Teplota (°C)": teplota,
        "Počasie": popis,
        "Ikona": symbol # Tu ukladáme nórsky kód symbolu
    }

    # 2. Doprava
    for nazov, suradnice in VJAZDY.items():
        novy_riadok[nazov] = ziskaj_plynulost(nazov, suradnice)

    # 3. Parkovanie
    parkoviska = ziskaj_vsetky_parkoviska()
    novy_riadok["P_Rybnikova"] = parkoviska["Rybníková"]
    novy_riadok["P_Hospodarska"] = parkoviska["Hospodárska"]
    novy_riadok["P_Kollarova"] = parkoviska["Kollárova"]

    # --- PORADIE ---
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

    for col in poradie:
        if col not in df.columns: df[col] = None
            
    df = df[poradie]
    df.to_excel("data_trnava_komplet.xlsx", index=False)
    
    # --- DASHBOARD (HTML) ---
    df_web = df.tail(20).copy()

    vjazdy_cols = [c for c in df_web.columns if "Zdrzanie_" in c]
    park_cols = ["P_Rybnikova", "P_Hospodarska", "P_Kollarova"]
    ciste_nazvy_vjazdy = [c.replace("Zdrzanie_", "").replace(" (min)", "") for c in vjazdy_cols]

    def ofarbi_plynulost(val):
        if isinstance(val, (int, float)):
            if val >= 90: color = "success"
            elif val >= 60: color = "warning text-dark"
            else: color = "danger"
            return f'<span class="badge bg-{color}">{val}%</span>'
        return val

    rows_html = ""
    for _, row in df_web.iterrows():
        # Monochromatická ikona podľa YR.no symbolu
        icon_class = YR_ICON_MAP.get(row['Ikona'], "bi-cloud")
        icon_html = f'<i class="bi {icon_class}" style="font-size: 1.4rem; color: #333;"></i>'

        rows_html += "<tr>"
        rows_html += f"<td>{row['Čas zberu']}</td>"
        rows_html += f"<td>{row['Teplota (°C)']}°C</td>"
        rows_html += f"<td>{icon_html}<br><span style='font-size: 0.7rem;'>{row['Počasie']}</span></td>"
        
        for col in vjazdy_cols:
            rows_html += f"<td>{ofarbi_plynulost(row[col])}</td>"
        for col in park_cols:
            p_val = row[col]
            p_display = f'<span class="badge bg-light text-dark border">{p_val}</span>' if p_val != "N/A" else '<span class="text-muted small">N/A</span>'
            rows_html += f"<td>{p_display}</td>"
        rows_html += "</tr>"

    html_table = f"""
    <table class="table table-hover table-striped border text-center align-middle mb-0">
        <thead class="table-dark">
            <tr>
                <th rowspan="2" class="align-middle">Čas zberu</th>
                <th rowspan="2" class="align-middle">Teplota</th>
                <th rowspan="2" class="align-middle">Počasie</th>
                <th colspan="{len(vjazdy_cols)}" class="border-bottom">Plynulosť dopravy (%)</th>
                <th colspan="3" class="border-bottom">Voľné miesta</th>
            </tr>
            <tr>
                {"".join([f"<th>{n}</th>" for n in ciste_nazvy_vjazdy])}
                <th>Rybníková</th><th>Hospodárska</th><th>Kollárova</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """

    html_content = f"""
    <html>
    <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <title>Trnava Smart Dashboard</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ background-color: #f0f2f5; font-family: 'Segoe UI', sans-serif; }}
            .container-fluid {{ background: white; padding: 20px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); margin-top: 20px; max-width: 99%; }}
            h2 {{ color: #1a2a6c; font-weight: 800; }}
            .table {{ font-size: 0.72rem; }}
            th {{ font-weight: 700; font-size: 0.6rem; text-transform: uppercase; }}
            .badge {{ font-weight: 600; width: 45px; }}
            .badge.bg-light {{ width: auto; min-width: 25px; }}
            .legend-item {{ font-size: 0.7rem; font-weight: 600; }}
        </style>
    </head>
    <body class="p-1 p-md-3">
        <div class="container-fluid">
            <div class="d-flex flex-column flex-md-row justify-content-between align-items-center mb-3">
                <div class="text-center text-md-start">
                    <h2 class="mb-0">🚗 Trnava Smart Dashboard</h2>
                    <p class="text-muted small">Dáta: MET Norway, TomTom, OpenData Trnava</p>
                </div>
                <div class="mt-3 mt-md-0 d-flex flex-column align-items-center align-items-md-end">
                    <span class="badge bg-dark w-auto p-2 mb-2">Aktualizácia: {cas_zberu}</span>
                    <div class="d-flex gap-2">
                        <span class="legend-item"><span class="badge bg-success" style="width:10px; height:10px; padding:0;">&nbsp;</span> 90%+</span>
                        <span class="legend-item"><span class="badge bg-warning text-dark" style="width:10px; height:10px; padding:0;">&nbsp;</span> 60-89%</span>
                        <span class="legend-item"><span class="badge bg-danger" style="width:10px; height:10px; padding:0;">&nbsp;</span> < 60%</span>
                    </div>
                </div>
            </div>
            <div class="table-responsive">
                {html_table}
            </div>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    zber_dat()

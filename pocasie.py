import requests
import pandas as pd
import os
from datetime import datetime
import pytz

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")
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

def ziskaj_parkovanie():
    try:
        url = "https://opendata.trnava.sk/api/v1/parkings"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10).json()
        for p in res.get('features', []):
            prop = p.get('properties', {})
            if "Rybníková" in prop.get('name', ''):
                val = prop.get('free_places')
                return val if val is not None else 0
        return 0
    except:
        return 0

def zber_dat():
    zona = pytz.timezone('Europe/Bratislava')
    cas_zberu = datetime.now(zona).strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Počasie
    w_url = f"http://api.openweathermap.org/data/2.5/weather?q=Trnava&appid={WEATHER_API_KEY}&units=metric"
    w_data = requests.get(w_url).json()
    
    novy_riadok = {
        "Čas zberu": cas_zberu,
        "Teplota (°C)": w_data['main']['temp'] if 'main' in w_data else 0,
        "Počasie": w_data['weather'][0]['description'] if 'weather' in w_data else "neznáme"
    }

    # 2. Doprava
    for nazov, suradnice in VJAZDY.items():
        novy_riadok[nazov] = ziskaj_plynulost(nazov, suradnice)

    # 3. Parkovanie
    novy_riadok["volne_rybnikova"] = ziskaj_parkovanie()

    # --- DEFINÍCIA PORADIA ---
    poradie = [
        "Čas zberu", "Teplota (°C)", "Počasie",
        "Zdrzanie_Zelenec (min)", "Zdrzanie_Bucany (min)", "Zdrzanie_Zavar (min)",
        "Zdrzanie_Nitrianska (min)", "Zdrzanie_Hrnciarovce (min)", "Zdrzanie_Biely_Kostol (min)",
        "Zdrzanie_Sucha (min)", "Zdrzanie_Spacince (min)", "Zdrzanie_Ruzindol (min)",
        "Zdrzanie_Boleraz (min)", "volne_rybnikova"
    ]

    try:
        df = pd.read_excel("data_trnava_komplet.xlsx")
        stare_zle = ['cas', 'teplota', 'pocasie', 'zdrzanie_min']
        df = df.drop(columns=[c for c in stare_zle if c in df.columns], errors='ignore')
        df = pd.concat([df, pd.DataFrame([novy_riadok])], ignore_index=True)
    except:
        df = pd.DataFrame([novy_riadok])

    for col in poradie:
        if col not in df.columns:
            df[col] = None
            
    df = df[poradie]
    df.to_excel("data_trnava_komplet.xlsx", index=False)
    
# --- VIZUÁLNY TUNING (HTML) ---
    df_web = df.tail(20).copy()

    # Funkcia na farbičky
    def ofarbi_plynulost(val):
        if isinstance(val, (int, float)):
            if val >= 90: color = "success"
            elif val >= 60: color = "warning text-dark"
            else: color = "danger"
            return f'<span class="badge bg-{color}">{val}%</span>'
        return val

    # Definujeme stĺpce, ktoré budeme upravovať
    vjazdy_cols = [c for c in df_web.columns if "Zdrzanie_" in c]
    
    # 1. Vyčistíme názvy miest pre podhlavičku (napr. "Zdrzanie_Zelenec (min)" -> "Zelenec")
    ciste_nazvy = []
    for col in df_web.columns:
        if "Zdrzanie_" in col:
            mesto = col.replace("Zdrzanie_", "").replace(" (min)", "")
            ciste_nazvy.append(mesto)
        else:
            ciste_nazvy.append(col)

    # 2. Aplikujeme farby na dáta
    for col in vjazdy_cols:
        df_web[col] = df_web[col].apply(ofarbi_plynulost)

    # 3. Vygenerujeme HTML s dvojitou hlavičkou
    # Rozdelíme stĺpce na tie pred "zdržaním", samotné zdržania a tie po nich
    cols_count = len(vjazdy_cols)
    
    html_table = f"""
    <table class="table table-hover table-striped border text-center">
        <thead class="table-dark">
            <tr>
                <th rowspan="2" class="align-middle">Čas zberu</th>
                <th rowspan="2" class="align-middle">Teplota</th>
                <th rowspan="2" class="align-middle">Počasie</th>
                <th colspan="{cols_count}" class="border-bottom">Zdržanie (Plynulosť dopravy %)</th>
                <th rowspan="2" class="align-middle">Parkovisko</th>
            </tr>
            <tr>
                {"".join([f"<th>{n}</th>" for n in ciste_nazvy if n not in ["Čas zberu", "Teplota (°C)", "Počasie", "volne_rybnikova"]])}
            </tr>
        </thead>
        <tbody>
            {df_web.to_html(index=False, header=False, escape=False, border=0)}
        </tbody>
    </table>
    """

    html_content = f"""
    <html>
    <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <title>Trnava Traffic Dashboard</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ background-color: #f8f9fa; font-family: sans-serif; }}
            .container-fluid {{ background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-top: 20px; }}
            h2 {{ color: #2c3e50; font-weight: bold; }}
            .table {{ font-size: 0.82rem; vertical-align: middle; }}
            th {{ font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; }}
        </style>
    </head>
    <body class="p-2 p-md-4">
        <div class="container-fluid">
            <div class="d-flex flex-column flex-md-row justify-content-between align-items-center mb-4">
                <div>
                    <h2>🚗 Trnava Traffic Dashboard</h2>
                </div>
                <span class="badge bg-secondary p-2">Posledná aktualizácia: {cas_zberu}</span>
            </div>
            <div class="table-responsive">
                {html_table}
            </div>
            <div class="mt-4 p-3 bg-light border rounded">
                <div class="d-flex gap-3 flex-wrap justify-content-center">
                    <span class="badge bg-success">90-100% Plynulá</span>
                    <span class="badge bg-warning text-dark">60-89% Zhustená</span>
                    <span class="badge bg-danger">pod 60% Zápcha</span>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Zber a dashboard hotový: {cas_zberu}")

if __name__ == "__main__":
    zber_dat()

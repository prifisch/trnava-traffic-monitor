import requests
import pandas as pd
import os
from datetime import datetime
import pytz

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")
WEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")

# Presne kalibrované body na hlavných cestách (vjazdy do TT)
VJAZDY = {
    "Zdrzanie_Zelenec (min)": "48.3582,17.5831",
    "Zdrzanie_Bucany (min)": "48.4014,17.6212",
    "Zdrzanie_Zavar (min)": "48.3758,17.6465",
    "Zdrzanie_Biely_Kostol (min)": "48.3711,17.5512",
    "Zdrzanie_Sucha (min)": "48.3885,17.5312",
    "Zdrzanie_Spacince (min)": "48.4055,17.6012",
    "Zdrzanie_Ruzindol (min)": "48.3585,17.5355",
    "Zdrzanie_Boleraz (min)": "48.4215,17.5311"
}

def ziskaj_zdrzanie(nazov, suradnice):
    try:
        # Pridali sme zoom level 12 a potvrdili absolute flow
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/12/json?key={TOMTOM_KEY}&point={suradnice}"
        res = requests.get(url, timeout=10).json()
        
        # DEBUG VÝPIS - uvidíš ho v Actions
        flow = res.get('flowSegmentData', {})
        current_speed = flow.get('currentSpeed', 0)
        free_flow = flow.get('freeFlowSpeed', 0)
        delay = flow.get('delaySeconds', 0) / 60
        
        print(f"DEBUG {nazov}: Rýchlosť {current_speed}/{free_flow}, Zdržanie: {delay} min")
        
        return round(delay, 2)
    except Exception as e:
        print(f"Chyba TomTom ({nazov}): {e}")
        return 0

def ziskaj_parkovanie():
    try:
        url = "https://opendata.trnava.sk/api/v1/parkings"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10).json()
        for p in res.get('features', []):
            prop = p.get('properties', {})
            if "Rybníková" in prop.get('name', ''):
                return prop.get('free_places', 0)
        return 0
    except:
        return 0

def zber_dat():
    zona = pytz.timezone('Europe/Bratislava')
    cas_zberu = datetime.now(zona).strftime("%Y-%m-%d %H:%M:%S")
    
    # Načítanie existujúceho Excelu
    try:
        df = pd.read_excel("data_trnava_komplet.xlsx")
    except:
        df = pd.DataFrame()

    # 1. Počasie
    w_url = f"http://api.openweathermap.org/data/2.5/weather?q=Trnava&appid={WEATHER_API_KEY}&units=metric"
    w_data = requests.get(w_url).json()
    
    # Vytvorenie nového riadku (dbáme na VEĽKÉ/malé písmená v názvoch stĺpcov)
    novy_riadok = {
        "Čas zberu": cas_zberu,
        "Teplota (°C)": w_data['main']['temp'],
        "Počasie": w_data['weather'][0]['description']
    }

    # 2. Doprava - pre každý smer
    for nazov, suradnice in VJAZDY.items():
        novy_riadok[nazov] = ziskaj_zdrzanie(nazov, suradnice)

    # 3. Parkovanie
    novy_riadok["volne_rybnikova"] = ziskaj_parkovanie()

    # Pridanie riadku do DataFrame
    df = pd.concat([df, pd.DataFrame([novy_riadok])], ignore_index=True)
    
    # UPRATOVANIE: Ak existujú stĺpce z minula, ktoré nechceme, vymažeme ich
    zbytocne_stlpce = ['cas', 'teplota', 'pocasie', 'zdrzanie_min']
    df = df.drop(columns=[c for c in zbytocne_stlpce if c in df.columns], errors='ignore')

    df.to_excel("data_trnava_komplet.xlsx", index=False)
    print(f"Zber úspešne dokončený o {cas_zberu}")

if __name__ == "__main__":
    zber_dat()

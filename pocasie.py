import requests
import pandas as pd
import os
from datetime import datetime
import pytz

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")
WEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")

# Skalibrované body bližšie k mestu (semafory/kruháče)
VJAZDY = {
    "Zdrzanie_Zelenec (min)": "48.3615,17.5855",
    "Zdrzanie_Bucany (min)": "48.3932,17.6105",
    "Zdrzanie_Zavar (min)": "48.3735,17.6255",
    "Zdrzanie_Biely_Kostol (min)": "48.3711,17.5512",
    "Zdrzanie_Sucha (min)": "48.3885,17.5312",
    "Zdrzanie_Spacince (min)": "48.4055,17.6012",
    "Zdrzanie_Ruzindol (min)": "48.3585,17.5355",
    "Zdrzanie_Boleraz (min)": "48.4025,17.5511"
}

def ziskaj_plynulost(nazov, suradnice):
    try:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/12/json?key={TOMTOM_KEY}&point={suradnice}"
        res = requests.get(url, timeout=10).json()
        flow = res.get('flowSegmentData', {})
        current = flow.get('currentSpeed', 1)
        free = flow.get('freeFlowSpeed', 1)
        # 100% = voľná cesta, menej = zápcha
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
    
    # Príprava riadku - PRESNÉ NÁZVY STĹPCOV
    novy_riadok = {
        "Čas zberu": cas_zberu,
        "Teplota (°C)": w_data['main']['temp'],
        "Počasie": w_data['weather'][0]['description']
    }

    # 2. Doprava (Index plynulosti v %)
    for nazov, suradnice in VJAZDY.items():
        novy_riadok[nazov] = ziskaj_plynulost(nazov, suradnice)

    # 3. Parkovanie
    novy_riadok["volne_rybnikova"] = ziskaj_parkovanie()

    # Načítanie a zápis
    try:
        df = pd.read_excel("data_trnava_komplet.xlsx")
        # Automatické premazanie stĺpcov, ktoré tam nechceme
        df = df.drop(columns=['cas', 'teplota', 'pocasie', 'zdrzanie_min'], errors='ignore')
        df = pd.concat([df, pd.DataFrame([novy_riadok])], ignore_index=True)
    except:
        df = pd.DataFrame([novy_riadok])
    
    df.to_excel("data_trnava_komplet.xlsx", index=False)
    print(f"Zber hotový: {cas_zberu}")

if __name__ == "__main__":
    zber_dat()

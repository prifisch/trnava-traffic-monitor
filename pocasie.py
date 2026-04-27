import requests
import pandas as pd
import os
from datetime import datetime
import pytz

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")
WEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")

# Definícia vjazdov (súradnice sme mali v predošlej verzii)
VJAZDY = {
    "Zdrzanie_Zelenec (min)": "48.358,17.583",
    "Zdrzanie_Bucany (min)": "48.411,17.636",
    "Zdrzanie_Zavar (min)": "48.375,17.653",
    "Zdrzanie_Biely_Kostol (min)": "48.372,17.545",
    "Zdrzanie_Sucha (min)": "48.391,17.525",
    "Zdrzanie_Spacince (min)": "48.415,17.599",
    "Zdrzanie_Ruzindol (min)": "48.356,17.522",
    "Zdrzanie_Boleraz (min)": "48.435,17.521"
}

def ziskaj_zdrzanie(suradnice):
    try:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key={TOMTOM_KEY}&point={suradnice}"
        res = requests.get(url, timeout=10).json()
        return round(res['flowSegmentData'].get('delaySeconds', 0) / 60, 2)
    except:
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
    
    # 1. Počasie
    w_url = f"http://api.openweathermap.org/data/2.5/weather?q=Trnava&appid={WEATHER_API_KEY}&units=metric"
    w_data = requests.get(w_url).json()
    
    # Príprava riadku s presnými názvami stĺpcov ako máš v Exceli
    novy_riadok = {
        "Čas zberu": cas_zberu,
        "Teplota (°C)": w_data['main']['temp'],
        "Počasie": w_data['weather'][0]['description']
    }

    # 2. Doprava pre všetky smery
    for nazov_stlpca, suradnice in VJAZDY.items():
        novy_riadok[nazov_stlpca] = ziskaj_zdrzanie(suradnice)

    # 3. Parkovanie
    novy_riadok["volne_rybnikova"] = ziskaj_parkovanie()

    # Uloženie
    try:
        df = pd.read_excel("data_trnava_komplet.xlsx")
        # Odstránime prípadné staré "zlé" stĺpce (malými písmenami), ak tam vznikli
        df = df.drop(columns=['cas', 'teplota', 'pocasie', 'zdrzanie_min'], errors='ignore')
        df = pd.concat([df, pd.DataFrame([novy_riadok])], ignore_index=True)
    except:
        df = pd.DataFrame([novy_riadok])
    
    df.to_excel("data_trnava_komplet.xlsx", index=False)
    print(f"Zber hotový: {cas_zberu}")

if __name__ == "__main__":
    zber_dat()

import requests
import pandas as pd
import os
from datetime import datetime
import pytz

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")
WEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")

VJAZDY = {
    "Zdrzanie_Zelenec (min)": "48.3615,17.5855", # Pri vjazde do mesta
    "Zdrzanie_Bucany (min)": "48.3932,17.6105", # Pri kruháči pri obchvate
    "Zdrzanie_Zavar (min)": "48.3735,17.6255",  # Pri PSA / Logistickom parku
    "Zdrzanie_Boleraz (min)": "48.4025,17.5511" # Pri Trstínskej ceste
}

def ziskaj_zdrzanie(nazov, suradnice):
    try:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/12/json?key={TOMTOM_KEY}&point={suradnice}"
        res = requests.get(url, timeout=10).json()
        
        flow = res.get('flowSegmentData', {})
        current = flow.get('currentSpeed', 1)
        free = flow.get('freeFlowSpeed', 1)
        
        # Výpočet plynulosti v percentách (100% = úplne voľno)
        plynulost = round((current / free) * 100, 2)
        
        print(f"DEBUG {nazov}: Plynulosť {plynulost}% ({current}/{free})")
        return plynulost
    except:
        return 100  # Ak zlyhá, predpokladáme voľnú cestu

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

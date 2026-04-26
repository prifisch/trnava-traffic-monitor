import requests
import pandas as pd
import os
from datetime import datetime
import pytz

# --- KONFIGURÁCIA ---
TOMTOM_KEY = os.getenv("TOMTOM_KEY")
WEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")

def ziskaj_parkovanie():
    """Získa počet voľných miest na parkovisku Rybníková od mesta Trnava"""
    try:
        # Oficiálne API mesta Trnava pre parkoviská
        url = "https://opendata.trnava.sk/api/v1/parkings"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # Hľadáme parkovisko Rybníková (ID býva v systéme stabilné)
        for p in data.get('features', []):
            prop = p.get('properties', {})
            if "Rybníková" in prop.get('name', ''):
                return prop.get('free_places', 0)
        return 0
    except Exception as e:
        print(f"Chyba pri parkovaní: {e}")
        return 0

def zber_dat():
    zona = pytz.timezone('Europe/Bratislava')
    cas_zberu = datetime.now(zona).strftime("%Y-%m-%d %H:%M:%S")
    print(f"Spúšťam zber dát (Trnavský čas): {cas_zberu}")

    # 1. Počasie
    w_url = f"http://api.openweathermap.org/data/2.5/weather?q=Trnava&appid={WEATHER_API_KEY}&units=metric"
    w_data = requests.get(w_url).json()
    temp = w_data['main']['temp']
    desc = w_data['weather'][0]['description']

    # 2. Doprava (TomTom) - Príklad pre vjazd od Zelenca
    t_url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key={TOMTOM_KEY}&point=48.358,17.583"
    t_data = requests.get(t_url).json()
    zdrzanie = t_data['flowSegmentData'].get('delaySeconds', 0) / 60

    # 3. Parkovanie (Mesto Trnava) - NOVINKA
    volne_rybnikova = ziskaj_parkovanie()

    # Príprava riadku
    novy_riadok = {
        "cas": cas_zberu,
        "teplota": temp,
        "pocasie": desc,
        "zdrzanie_min": round(zdrzanie, 2),
        "volne_rybnikova": volne_rybnikova
    }

    # Uloženie do Excelu
    try:
        df = pd.read_excel("data_trnava_komplet.xlsx")
        df = pd.concat([df, pd.DataFrame([novy_riadok])], ignore_index=True)
    except:
        df = pd.DataFrame([novy_riadok])
    
    df.to_excel("data_trnava_komplet.xlsx", index=False)
    print(f"Dáta uložené. Voľné miesta Rybníková: {volne_rybnikova}")

if __name__ == "__main__":
    zber_dat()

import requests
import pandas as pd
from datetime import datetime
import time
import os
import pytz

TOMTOM_KEY = os.getenv("TOMTOM_KEY")
WEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")

CITY = "Trnava"
# Definujeme trasy pre dopravu (Štart -> Cieľ Bernolákova brána)
TRASY = {
    "Vjazd_Zelenec": {"odkial": "Zelenec, Slovakia", "kam": "Trnava, Slovakia"},
    "Vjazd_Bucany": {"odkial": "Bucany, Slovakia", "kam": "Trnava, Slovakia"}
}

def zber_dat():
    zona = pytz.timezone('Europe/Bratislava')
    cas_zberu = datetime.now(zona).strftime("%Y-%m-%d %H:%M:%S")
    print(f"Spúšťam zber dát (Trnavský čas): {cas_zberu}")

    # 1. ZBER POČASIA
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_API_KEY}&units=metric&lang=sk"
    teplota = None
    popis_pocasia = None
    
    try:
        w_res = requests.get(weather_url)
        if w_res.status_code == 200:
            w_data = w_res.json()
            teplota = w_data['main']['temp']
            popis_pocasia = w_data['weather'][0]['description']
            print(f"Počasie OK: {teplota}°C")
    except Exception as e:
        print(f"Chyba počasia: {e}")

   # 2. ZBER DOPRAVY (Rozšírený zoznam smerov)
    doprava_data = {}
    
    # Kompletný zoznam vjazdov do Trnavy
    TRASY_NAZVY = {
        "Vjazd_Zelenec": {"odkial": "Zelenec, Slovakia", "kam": "Trnava, Slovakia"},
        "Vjazd_Bucany": {"odkial": "Bucany, Slovakia", "kam": "Trnava, Slovakia"},
        "Vjazd_Zavar": {"odkial": "Zavar, Slovakia", "kam": "Trnava, Slovakia"},
        "Vjazd_Biely_Kostol": {"odkial": "Biely Kostol, Slovakia", "kam": "Trnava, Slovakia"},
        "Vjazd_Sucha": {"odkial": "Suchá nad Parnou, Slovakia", "kam": "Trnava, Slovakia"},
        "Vjazd_Spacince": {"odkial": "Špačince, Slovakia", "kam": "Trnava, Slovakia"},
        "Vjazd_Ruzindol": {"odkial": "Ružindol, Slovakia", "kam": "Trnava, Slovakia"},
        "Vjazd_Boleraz": {"odkial": "Boleráz, Slovakia", "kam": "Trnava, Slovakia"}
    }

    for meno, body in TRASY_NAZVY.items():
        try:
            # Geocoding - nájdenie súradníc pre obce a Trnavu
            search_start_url = f"https://api.tomtom.com/search/2/geocode/{body['odkial']}.json?key={TOMTOM_KEY}"
            res_start = requests.get(search_start_url).json()
            pos_start = res_start['results'][0]['position']
            start_coord = f"{pos_start['lat']},{pos_start['lon']}"

            search_ciel_url = f"https://api.tomtom.com/search/2/geocode/{body['kam']}.json?key={TOMTOM_KEY}"
            res_ciel = requests.get(search_ciel_url).json()
            pos_ciel = res_ciel['results'][0]['position']
            ciel_coord = f"{pos_ciel['lat']},{pos_ciel['lon']}"

            # Výpočet trasy s aktuálnou dopravou
            t_url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_coord}:{ciel_coord}/json?key={TOMTOM_KEY}&traffic=true"
            
            t_res = requests.get(t_url)
            if t_res.status_code == 200:
                t_data = t_res.json()
                sekundy = t_data['routes'][0]['summary']['travelTimeInSeconds']
                minuty = round(sekundy / 60, 1)
                doprava_data[meno] = minuty
                print(f"Doprava {meno} OK: {minuty} min")
            else:
                print(f"Chyba TomTom ({meno}): Status {t_res.status_code}")
                
            time.sleep(0.5) # Krátka pauza medzi dopytmi
        except Exception as e:
            print(f"Chyba pri spracovaní {meno}: {e}")

# 3. SPOJENIE A ULOŽENIE (Doplnené o nové stĺpce)
    novy_riadok = {
        "Čas zberu": [cas_zberu],
        "Teplota (°C)": [teplota],
        "Počasie": [popis_pocasia],
        "Zdrzanie_Zelenec (min)": [doprava_data.get("Vjazd_Zelenec")],
        "Zdrzanie_Bucany (min)": [doprava_data.get("Vjazd_Bucany")],
        "Zdrzanie_Zavar (min)": [doprava_data.get("Vjazd_Zavar")],
        "Zdrzanie_Biely_Kostol (min)": [doprava_data.get("Vjazd_Biely_Kostol")],
        "Zdrzanie_Sucha (min)": [doprava_data.get("Vjazd_Sucha")],
        "Zdrzanie_Spacince (min)": [doprava_data.get("Vjazd_Spacince")],
        "Zdrzanie_Ruzindol (min)": [doprava_data.get("Vjazd_Ruzindol")],
        "Zdrzanie_Boleraz (min)": [doprava_data.get("Vjazd_Boleraz")]
    }

    df = pd.DataFrame(novy_riadok)

    try:
        # Skúsime načítať existujúci súbor
        existujuci_df = pd.read_excel("data_trnava_komplet.xlsx")
        final_df = pd.concat([existujuci_df, df], ignore_index=True)
    except FileNotFoundError:
        final_df = df

    final_df.to_excel("data_trnava_komplet.xlsx", index=False)
    print("Všetky dáta úspešne uložené do data_trnava_komplet.xlsx\n")

if __name__ == "__main__":
    zber_dat()

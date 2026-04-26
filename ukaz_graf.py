import pandas as pd
import matplotlib.pyplot as plt

def nakresli_rozsireny_graf():
    try:
        # 1. Načítanie dát
        df = pd.read_excel("data_trnava_komplet.xlsx")
        df['Čas zberu'] = pd.to_datetime(df['Čas zberu'])

        # 2. Vytvorenie grafu
        fig, ax1 = plt.subplots(figsize=(14, 8))

        # Zoznam všetkých stĺpcov s dopravou (všetko čo začína "Zdrzanie_")
        stlpce_dopravy = [col for col in df.columns if 'Zdrzanie_' in col]
        
        # Farby pre jednotlivé smery, aby sa neopakovali
        farby = plt.cm.tab10.colors 

        # --- PRVÁ OSA (Všetky smery dopravy) ---
        ax1.set_xlabel('Čas a dátum', fontsize=10)
        ax1.set_ylabel('Čas cesty (minúty)', color='black', fontsize=12)
        
        for i, stlpec in enumerate(stlpce_dopravy):
            # Odstránime "Zdrzanie_" a "(min)" z názvu pre krajšiu legendu
            label_meno = stlpec.replace("Zdrzanie_", "").replace(" (min)", "")
            ax1.plot(df['Čas zberu'], df[stlpec], label=label_meno, linewidth=2, marker='.', alpha=0.8)

        ax1.tick_params(axis='y', labelcolor='black')
        ax1.grid(True, linestyle='--', alpha=0.3)

        # --- DRUHÁ OSA (Teplota) ---
        ax2 = ax1.twinx()
        ax2.set_ylabel('Teplota (°C)', color='tab:blue', fontsize=12)
        ax2.plot(df['Čas zberu'], df['Teplota (°C)'], color='tab:blue', linestyle='--', linewidth=3, alpha=0.5, label='Teplota')
        ax2.tick_params(axis='y', labelcolor='tab:blue')

        # 3. Úprava vizuálu
        plt.title('Kompletný dopravný obraz Trnavy vs. Počasie', fontsize=16, pad=20)
        
        # Legenda - umiestnime ju mimo grafu, aby nezavadzala čiaram
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', bbox_to_anchor=(1.05, 1), title="Smery a počasie")

        plt.xticks(rotation=45)
        plt.tight_layout()

        print("Generujem rozšírený graf pre všetky smery...")
        # Namiesto zobrazenia okna graf uložíme
        plt.savefig("doprava_trnava_aktualne.png", dpi=300, bbox_inches='tight')
        print("Graf bol úspešne uložený ako obrázok.")
        plt.close() # Dôležité: uvoľní pamäť

    except Exception as e:
        print(f"Chyba pri kreslení grafu: {e}")

if __name__ == "__main__":
    nakresli_rozsireny_graf()
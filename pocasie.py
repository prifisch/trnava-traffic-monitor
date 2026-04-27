html_content = f"""
    <!DOCTYPE html>
    <html lang="sk">
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <title>TrnavaPulse v2</title>
        <style>
            :root {{
                --sidebar-bg: #f8f9fa;
                --primary-color: #1a73e8;
                --text-main: #202124;
                --text-muted: #5f6368;
                --bg-main: #ffffff;
            }}
            body {{ background: var(--bg-main); font-family: 'Inter', -apple-system, sans-serif; color: var(--text-main); display: flex; }}
            
            /* Sidebar podľa inšpirácie */
            .sidebar {{ 
                width: 260px; height: 100vh; background: var(--sidebar-bg); 
                position: fixed; border-right: 1px solid #e0e0e0; padding: 32px 16px; 
            }}
            .logo {{ 
                font-weight: 800; font-size: 1.4rem; color: var(--primary-color); 
                margin-bottom: 40px; padding-left: 12px; display: flex; align-items: center; gap: 10px;
            }}
            .nav-item {{ 
                padding: 12px 16px; border-radius: 8px; color: var(--text-muted); 
                text-decoration: none; display: flex; align-items: center; gap: 12px;
                margin-bottom: 4px; cursor: pointer; font-weight: 500; transition: all 0.2s;
            }}
            .nav-item:hover {{ background: #f1f3f4; color: var(--text-main); }}
            .nav-item.active {{ background: #e8f0fe; color: var(--primary-color); }}
            
            /* Hlavný obsah */
            .main-content {{ margin-left: 260px; width: 100%; min-height: 100vh; display: flex; flex-direction: column; }}
            
            /* Horná lišta */
            .top-bar {{ 
                height: 64px; border-bottom: 1px solid #e0e0e0; display: flex; 
                align-items: center; justify-content: space-between; padding: 0 40px;
                background: white; position: sticky; top: 0; z-index: 100;
            }}
            .search-box {{ background: #f1f3f4; border: none; padding: 8px 16px; border-radius: 8px; width: 300px; outline: none; }}
            
            .content-area {{ padding: 40px; }}
            h1 {{ font-weight: 800; font-size: 2rem; margin-bottom: 32px; letter-spacing: -0.5px; }}
            
            /* Karta pre tabuľku */
            .data-card {{ 
                background: white; border: 1px solid #e0e0e0; border-radius: 16px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.03); overflow: hidden;
            }}
            .table {{ margin-bottom: 0; }}
            .table thead th {{ 
                background: #f8f9fa; font-size: 0.75rem; text-transform: uppercase; 
                letter-spacing: 0.05em; color: var(--text-muted); border-top: none;
                padding: 16px 12px; font-weight: 600; text-align: center;
            }}
            .table tbody td {{ padding: 16px 12px; vertical-align: middle; text-align: center; border-bottom: 1px solid #f1f3f4; }}
            
            .status-pill {{ 
                padding: 6px 12px; border-radius: 20px; font-size: 0.75rem; 
                font-weight: 700; display: inline-block; min-width: 65px;
            }}
            .status-green {{ background: #e6f4ea; color: #1e8e3e; }}
            .status-orange {{ background: #fef7e0; color: #f9ab00; }}
            .status-red {{ background: #fce8e6; color: #d93025; }}
            
            .time-col {{ font-weight: 700; color: var(--primary-color); text-align: left !important; padding-left: 24px !important; }}
            
            /* Animácie */
            .view-section {{ display: none; animation: fadeIn 0.4s ease-out; }}
            .view-section.active {{ display: block; }}
            @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="logo"><i class="bi bi-geo-fill"></i> TT-Pulse</div>
            <div class="nav-item active" onclick="showSection('dashboard', this)"><i class="bi bi-grid-1x2"></i> Dashboard</div>
            <div class="nav-item" onclick="showSection('mapa', this)"><i class="bi bi-map"></i> Mapa mesta</div>
            <div class="nav-item" onclick="showSection('analyzy', this)"><i class="bi bi-bar-chart"></i> Analýzy</div>
        </div>

        <div class="main-content">
            <div class="top-bar">
                <input type="text" class="search-box" placeholder="Hľadať vjazdy...">
                <div class="d-flex align-items-center gap-3">
                    <span class="small text-muted">{teraz.strftime("%d. %m. %Y")}</span>
                    <i class="bi bi-bell text-muted"></i>
                    <div style="width: 32px; height: 32px; background: #e8f0fe; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #1a73e8; font-weight: bold;">T</div>
                </div>
            </div>

            <div class="content-area">
                <div id="dashboard" class="view-section active">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <h1>Dashboard</h1>
                        <button class="btn btn-primary rounded-pill px-4" onclick="location.reload()"><i class="bi bi-arrow-clockwise me-2"></i>Aktualizovať</button>
                    </div>
                    
                    <div class="data-card">
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th class="time-col" style="text-align: left !important;">Čas</th>
                                        <th>Tep.</th>
                                        <th>Obloha</th>
                                        {"".join([f"<th>{n}</th>" for n in VJAZDY.keys()])}
                                        <th>Ryb.</th><th>Hosp.</th><th>Koll.</th>
                                    </tr>
                                </thead>
                                <tbody>{rows_html}</tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div id="mapa" class="view-section">
                    <h1>Mapa mesta</h1>
                    <div class="data-card p-2">
                        <iframe width="100%" height="600" frameborder="0" src="https://www.google.com/maps/embed?pb=!1m14!1m12!1m3!1d42392.2345!2d17.58!3d48.37!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!5e0!3m2!1ssk!2ssk!4v1700000000000!5m2!1ssk!2ssk&layer=t" style="border-radius: 12px;" allowfullscreen></iframe>
                    </div>
                </div>

                <div id="analyzy" class="view-section">
                    <h1>Analýzy</h1>
                    <div class="chart-container">
                        <canvas id="trafficChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function showSection(sectionId, element) {{
                document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                document.getElementById(sectionId).classList.add('active');
                element.classList.add('active');
            }}
            // ... (zvyšok JS kódu pre graf zostáva rovnaký)
        </script>
    </body>
    </html>
    """

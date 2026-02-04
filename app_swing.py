import streamlit as st
import pandas as pd
import yfinance as yf
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="Screener Institucional",
    layout="wide",
    page_icon="💎",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .metric-card { background-color: #0E1117; border: 1px solid #262730; border-radius: 10px; padding: 15px; }
    .stDataFrame { border-radius: 10px; }
    iframe { width: 100% !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CEREBRO MATEMÁTICO (Técnico + Fundamental) ---
@st.cache_data(ttl=3600, show_spinner=False)
def analizar_mercado(df_input, min_price, min_vol, usar_fundamentales, limit):
    # Filtro Inicial (Liquidez)
    candidatos = df_input[
        (df_input['Last Sale'] >= min_price) & 
        (df_input['Volume'] >= min_vol)
    ]['Symbol'].tolist()
    
    if limit:
        candidatos = candidatos[:30] # Limitado para pruebas rápidas
    
    resultados = []
    
    # Barra de progreso
    progreso_bar = st.progress(0)
    status_text = st.empty()
    stop_button = st.button("✋ Detener Análisis")
    
    total = len(candidatos)
    
    for i, ticker in enumerate(candidatos):
        if stop_button: break

        try:
            status_text.markdown(f"Analizando: **{ticker}** ({i+1}/{total})")
            time.sleep(0.1) # Freno anti-bloqueo
            
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            
            if len(hist) > 200:
                # --- A. ANÁLISIS TÉCNICO (El Gráfico) ---
                precio = hist['Close'].iloc[-1]
                vol_hoy = hist['Volume'].iloc[-1]
                vol_medio = hist['Volume'].rolling(50).mean().iloc[-1]
                
                sma_200 = hist['Close'].rolling(200).mean().iloc[-1]
                sma_150 = hist['Close'].rolling(150).mean().iloc[-1]
                max_20_dias = hist['High'].iloc[-21:-1].max() # Techo del último mes
                
                # Condiciones Técnicas (PDF)
                # 1. Fase 2: Precio encima de medias y medias ordenadas
                tecnico_fase2 = (precio > sma_150) and (precio > sma_200) and (sma_150 > sma_200)
                # 2. Cerca de Máximos (High Tight Flag)
                max_52s = hist['High'].max()
                cerca_maximos = precio >= (0.85 * max_52s) # A menos de un 15% de máximos anuales
                
                if tecnico_fase2 and cerca_maximos:
                    
                    # --- B. ANÁLISIS FUNDAMENTAL (Los Balances) ---
                    pasa_fundamental = True
                    crecimiento_ventas = 0
                    crecimiento_eps = 0
                    market_cap_b = 0
                    
                    if usar_fundamentales:
                        try:
                            info = stock.info
                            # Market Cap > 2 Billones ($2B)
                            mcap = info.get('marketCap', 0)
                            market_cap_b = round(mcap / 1_000_000_000, 2)
                            
                            if market_cap_b < 2.0: 
                                pasa_fundamental = False
                            
                            # Crecimiento Ventas (Revenue Growth) > 25%
                            # yfinance da 0.25 para 25%
                            rev_growth = info.get('revenueGrowth', 0)
                            crecimiento_ventas = round(rev_growth * 100, 2) if rev_growth else 0
                            
                            if crecimiento_ventas < 25:
                                pasa_fundamental = False
                                
                            # Crecimiento EPS (Earnings Growth) > 20%
                            eps_growth = info.get('earningsGrowth', 0)
                            crecimiento_eps = round(eps_growth * 100, 2) if eps_growth else 0
                            
                            if crecimiento_eps < 20:
                                pasa_fundamental = False
                                
                        except:
                            pasa_fundamental = False # Si no tiene datos, descartamos por seguridad
                    
                    # --- C. FILTRO DE ROTURA (Volumen) ---
                    vol_rel = vol_hoy / vol_medio if vol_medio > 0 else 0
                    es_rotura = (vol_rel > 1.5) and (precio > max_20_dias)
                    
                    # GUARDAR SI CUMPLE TODO
                    if pasa_fundamental:
                        nota = "✅ Calidad"
                        if es_rotura: nota = "💎 ROTURA + CALIDAD"
                        
                        resultados.append({
                            "Symbol": ticker,
                            "Precio": precio,
                            "Vol_Relativo": vol_rel,
                            "Ventas_QoQ%": crecimiento_ventas if usar_fundamentales else "N/A",
                            "EPS_QoQ%": crecimiento_eps if usar_fundamentales else "N/A",
                            "Mkt_Cap_B": market_cap_b if usar_fundamentales else "N/A",
                            "Link": f"https://finviz.com/quote.ashx?t={ticker}",
                            "Estado": nota
                        })
                        
        except Exception:
            pass
        
        progreso_bar.progress((i + 1) / total)
    
    progreso_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(resultados)

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.title("💎 Sniper Fundamental")
    uploaded_file = st.file_uploader("1. Sube 'nasdaq_screener.csv'", type=["csv"])
    
    st.divider()
    st.subheader("⚙️ Filtros Técnicos")
    min_p = st.number_input("Precio Mínimo ($)", 10.0, 500.0, 15.0)
    min_v = st.number_input("Volumen Mínimo", 50000, 5000000, 200000)
    
    st.divider()
    st.subheader("📊 Filtros de Valor (PDF)")
    usar_fundamentales = st.toggle("Activar Filtro Fundamental", value=False)
    if usar_fundamentales:
        st.info("""
        **Condiciones Activadas:**
        - Cap. Mercado > $2B
        - Ventas (QoQ) > 25%
        - EPS (QoQ) > 20%
        """)
    
    modo_turbo = st.toggle("⚡ Modo Rápido (50 acciones)", value=True)
    run_btn = st.button("🔍 ANALIZAR MERCADO", type="primary")

# --- 4. DASHBOARD ---
if run_btn and uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file)
        df_raw.columns = [c.strip() for c in df_raw.columns]
        if df_raw['Last Sale'].dtype == object:
            df_raw['Last Sale'] = df_raw['Last Sale'].replace({'\$': '', ',': ''}, regex=True).astype(float)

        df_res = analizar_mercado(df_raw, min_p, min_v, usar_fundamentales, modo_turbo)

        if not df_res.empty:
            # KPIs
            roturas = df_res[df_res['Estado'].str.contains("ROTURA")]
            col1, col2, col3 = st.columns(3)
            col1.metric("Candidatos Totales", len(df_res))
            col2.metric("💎 Joyas (Rotura)", len(roturas))
            
            # Pestañas
            tab_tabla, tab_grafico = st.tabs(["📋 Resultados", "📈 Gráfico Pro"])
            
            with tab_tabla:
                cols_config = {
                    "Symbol": "Ticker",
                    "Precio": st.column_config.NumberColumn(format="$%.2f"),
                    "Vol_Relativo": st.column_config.ProgressColumn("Volumen", format="%.1fx", min_value=0, max_value=10),
                    "Link": st.column_config.LinkColumn("Finviz", display_text="Ver")
                }
                # Añadir columnas fundamentales si están activas
                if usar_fundamentales:
                    cols_config.update({
                        "Ventas_QoQ%": st.column_config.NumberColumn("Ventas %", format="%.1f%%"),
                        "EPS_QoQ%": st.column_config.NumberColumn("EPS %", format="%.1f%%"),
                        "Mkt_Cap_B": st.column_config.NumberColumn("Cap ($B)", format="%.1fB")
                    })
                
                st.dataframe(
                    df_res.sort_values(by="Vol_Relativo", ascending=False),
                    column_config=cols_config,
                    use_container_width=True,
                    height=600
                )
            
            with tab_grafico:
                ticker_sel = st.selectbox("Elige empresa:", df_res['Symbol'])
                components.html(f"""
                <div class="tradingview-widget-container" style="height:500px;width:100%">
                  <div id="tradingview_chart"></div>
                  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                  <script type="text/javascript">
                  new TradingView.widget({{
                  "autosize": true, "symbol": "{ticker_sel}", "interval": "D", "timezone": "Etc/UTC", "theme": "dark", "style": "1", "locale": "es", "toolbar_bg": "#f1f3f6", "enable_publishing": false, "allow_symbol_change": true, "container_id": "tradingview_chart"
                  }});
                  </script>
                </div>
                """, height=500)

        else:
            st.warning("Ninguna empresa cumplió los criterios. ¡El mercado está difícil hoy!")
            
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("👋 Sube tu archivo CSV para empezar.")
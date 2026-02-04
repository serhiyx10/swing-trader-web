import streamlit as st
import pandas as pd
import yfinance as yf
import time
import streamlit.components.v1 as components

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="Sniper Elite Terminal",
    layout="wide",
    page_icon="🎯",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .metric-card { background-color: #0E1117; border: 1px solid #262730; border-radius: 10px; padding: 15px; }
    .stDataFrame { border-radius: 10px; }
    iframe { width: 100% !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CEREBRO MATEMÁTICO ---
def analizar_mercado(df_input, min_price, min_vol, usar_fundamentales, limit):
    # Filtro Inicial
    candidatos = df_input[
        (df_input['Last Sale'] >= min_price) & 
        (df_input['Volume'] >= min_vol)
    ]['Symbol'].tolist()
    
    if limit:
        candidatos = candidatos[:40] 
    
    resultados = []
    
    # Descargar datos del SPY (S&P 500) para comparar fuerza relativa
    spy = yf.Ticker("SPY")
    hist_spy = spy.history(period="6mo")
    spy_return_3m = 0
    if len(hist_spy) > 60:
        spy_start = hist_spy['Close'].iloc[-60]
        spy_end = hist_spy['Close'].iloc[-1]
        spy_return_3m = ((spy_end - spy_start) / spy_start) * 100

    progreso_bar = st.progress(0)
    status_text = st.empty()
    stop_button = st.button("✋ Detener Análisis")
    
    total = len(candidatos)
    
    for i, ticker in enumerate(candidatos):
        if stop_button: 
            st.warning("🛑 Análisis detenido.")
            break

        try:
            status_text.markdown(f"Escaneando: **{ticker}** ({i+1}/{total})")
            time.sleep(0.05) 
            
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            
            if len(hist) > 200:
                # --- DATOS TÉCNICOS ---
                precio = hist['Close'].iloc[-1]
                vol_hoy = hist['Volume'].iloc[-1]
                vol_medio = hist['Volume'].rolling(50).mean().iloc[-1]
                
                sma_200 = hist['Close'].rolling(200).mean().iloc[-1]
                sma_150 = hist['Close'].rolling(150).mean().iloc[-1]
                max_20_dias = hist['High'].iloc[-21:-1].max() 
                min_20_dias = hist['Low'].iloc[-21:-1].min() # Soporte reciente (para Stop Loss)
                
                # --- FUERZA RELATIVA (RS RATING) ---
                # Comparamos rendimiento a 3 meses vs SPY
                precio_3m_atras = hist['Close'].iloc[-60]
                stock_return_3m = ((precio - precio_3m_atras) / precio_3m_atras) * 100
                rs_rating = stock_return_3m - spy_return_3m # Si es positivo, gana al mercado
                
                # Condiciones Técnicas
                tecnico_fase2 = (precio > sma_150) and (precio > sma_200) and (sma_150 > sma_200)
                max_52s = hist['High'].max()
                cerca_maximos = precio >= (0.80 * max_52s) # Relajado al 20%
                
                if tecnico_fase2 and cerca_maximos:
                    
                    # --- DATOS FUNDAMENTALES ---
                    pasa_fundamental = True
                    crecimiento_ventas = 0
                    crecimiento_eps = 0
                    market_cap_b = 0
                    
                    if usar_fundamentales:
                        try:
                            info = stock.info
                            mcap = info.get('marketCap', 0)
                            market_cap_b = round(mcap / 1_000_000_000, 2)
                            if market_cap_b < 0.3: pasa_fundamental = False # Bajado a 300M para pillar small caps
                            
                            rev_growth = info.get('revenueGrowth', 0)
                            crecimiento_ventas = round(rev_growth * 100, 2) if rev_growth else 0
                            if crecimiento_ventas < 15: pasa_fundamental = False # Bajado a 15%
                                
                            eps_growth = info.get('earningsGrowth', 0)
                            crecimiento_eps = round(eps_growth * 100, 2) if eps_growth else 0
                            if crecimiento_eps < 15: pasa_fundamental = False
                        except:
                            pasa_fundamental = False
                    
                    # --- FILTRO ROTURA ---
                    vol_rel = vol_hoy / vol_medio if vol_medio > 0 else 0
                    es_rotura = (vol_rel > 1.5) and (precio > max_20_dias)
                    
                    if pasa_fundamental:
                        nota = "✅ Calidad"
                        if es_rotura: nota = "💎 ROTURA PURA"
                        
                        resultados.append({
                            "Symbol": ticker,
                            "Precio": precio,
                            "Stop_Loss_Ideal": min_20_dias * 0.98, # Un 2% bajo el último mínimo
                            "Vol_Relativo": vol_rel,
                            "RS_Rating": rs_rating,
                            "Ventas_QoQ%": crecimiento_ventas if usar_fundamentales else "N/A",
                            "EPS_QoQ%": crecimiento_eps if usar_fundamentales else "N/A",
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
    st.title("🎯 Sniper Elite")
    uploaded_file = st.file_uploader("1. Sube 'nasdaq_screener.csv'", type=["csv"])
    
    st.divider()
    
    # --- NUEVA CALCULADORA DE RIESGO ---
    st.subheader("💰 Gestión de Riesgo (Calculadora)")
    capital_cuenta = st.number_input("Capital Total Cuenta ($)", value=10000)
    riesgo_pct = st.number_input("Riesgo por Operación (%)", value=1.0, step=0.1)
    riesgo_usd = capital_cuenta * (riesgo_pct / 100)
    st.info(f"Riesgo máx. por trade: **${riesgo_usd:.2f}**")
    
    st.divider()
    
    st.subheader("⚙️ Filtros")
    min_p = st.number_input("Precio Mín ($)", 10.0, 500.0, 15.0)
    min_v = st.number_input("Volumen Mín", 50000, 5000000, 200000)
    
    usar_fundamentales = st.toggle("Activar Filtro Fundamental (PDF)", value=False)
    modo_turbo = st.toggle("⚡ Modo Rápido (40 acciones)", value=True)
    
    run_btn = st.button("🔍 ANALIZAR MERCADO", type="primary")

# --- 4. DASHBOARD ---
if 'resultados' not in st.session_state:
    st.session_state.resultados = None

if run_btn and uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file)
        df_raw.columns = [c.strip() for c in df_raw.columns]
        if df_raw['Last Sale'].dtype == object:
            df_raw['Last Sale'] = df_raw['Last Sale'].replace({'\$': '', ',': ''}, regex=True).astype(float)

        st.session_state.resultados = analizar_mercado(df_raw, min_p, min_v, usar_fundamentales, modo_turbo)

    except Exception as e:
        st.error(f"Error: {e}")

# MOSTRAR RESULTADOS
if st.session_state.resultados is not None and not st.session_state.resultados.empty:
    df_res = st.session_state.resultados
    
    # CALCULAR POSICIÓN AUTOMÁTICA
    # Añadimos columna de cuántas acciones comprar según el riesgo del usuario
    df_res['Riesgo_Trade_Unitario'] = df_res['Precio'] - df_res['Stop_Loss_Ideal']
    # Evitar división por cero
    df_res['Acciones_Comprar'] = df_res.apply(
        lambda x: int(riesgo_usd / x['Riesgo_Trade_Unitario']) if x['Riesgo_Trade_Unitario'] > 0 else 0, axis=1
    )
    
    # KPIs
    roturas = df_res[df_res['Estado'].str.contains("ROTURA")]
    lideres = df_res[df_res['RS_Rating'] > 0] # Acciones que ganan al SPY
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Oportunidades", len(df_res))
    col2.metric("💎 Roturas Puras", len(roturas))
    col3.metric("🚀 Líderes (RS+)", len(lideres))
    
    tab_tabla, tab_grafico = st.tabs(["📋 Plan de Trading", "📈 Gráfico Pro"])
    
    with tab_tabla:
        cols_config = {
            "Symbol": "Ticker",
            "Precio": st.column_config.NumberColumn(format="$%.2f"),
            "Acciones_Comprar": st.column_config.NumberColumn("🛒 Comprar (Cant.)", help=f"Cantidad para arriesgar ${riesgo_usd}"),
            "Stop_Loss_Ideal": st.column_config.NumberColumn("🛑 Stop Loss", format="$%.2f", help="Bajo el último soporte"),
            "RS_Rating": st.column_config.NumberColumn("Fuerza Relativa", format="%.1f", help="Positivo = Gana al S&P500"),
            "Vol_Relativo": st.column_config.ProgressColumn("Volumen", format="%.1fx", min_value=0, max_value=10),
            "Link": st.column_config.LinkColumn("Finviz", display_text="Ver")
        }
        
        if usar_fundamentales:
            cols_config.update({
                "Ventas_QoQ%": st.column_config.NumberColumn("Ventas %", format="%.1f%%"),
                "EPS_QoQ%": st.column_config.NumberColumn("EPS %", format="%.1f%%"),
            })
        
        # Colorear filas: Verde si es líder (RS > 0), Rojo si es rezagada
        st.dataframe(
            df_res.sort_values(by="Vol_Relativo", ascending=False),
            column_config=cols_config,
            use_container_width=True,
            height=600
        )
    
    with tab_grafico:
        col_sel, col_empty = st.columns([1,3])
        with col_sel:
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

elif run_btn:
    st.warning("No se encontraron resultados.")
elif not uploaded_file:
    st.info("👋 Sube tu archivo CSV para empezar.")
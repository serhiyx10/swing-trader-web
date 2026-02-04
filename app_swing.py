import streamlit as st
import pandas as pd
import yfinance as yf
import streamlit.components.v1 as components # Necesario para TradingView

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Terminal Swing Pro", # Puedes cambiar este nombre
    layout="wide",
    page_icon="🚀",
    initial_sidebar_state="expanded"
)

# Estilos CSS para dar aspecto profesional (Modo Oscuro mejorado)
st.markdown("""
    <style>
    .metric-card {
        background-color: #0E1117;
        border: 1px solid #262730;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .stDataFrame { border-radius: 10px; }
    /* Ajuste para que el widget de TradingView ocupe bien el espacio */
    iframe { width: 100% !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CEREBRO MATEMÁTICO (Lógica de Fase 2) ---
@st.cache_data(ttl=3600) # Caché de 1 hora para velocidad
def analizar_mercado(df_input, min_price, min_vol, limit):
    # Filtro previo rápido
    candidatos = df_input[
        (df_input['Last Sale'] >= min_price) & 
        (df_input['Volume'] >= min_vol)
    ]['Symbol'].tolist()
    
    if limit:
        candidatos = candidatos[:50] # Modo rápido
    
    resultados = []
    
    # Barra de progreso
    progress_text = "Analizando mercado en busca de patrones institucionales..."
    my_bar = st.progress(0, text=progress_text)
    
    total = len(candidatos)
    
    for i, ticker in enumerate(candidatos):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            
            if len(hist) > 200:
                # Datos actuales
                precio = hist['Close'].iloc[-1]
                vol_hoy = hist['Volume'].iloc[-1]
                vol_medio = hist['Volume'].rolling(50).mean().iloc[-1]
                
                # Medias Móviles
                sma_200 = hist['Close'].rolling(200).mean().iloc[-1]
                sma_150 = hist['Close'].rolling(150).mean().iloc[-1]
                sma_50 = hist['Close'].rolling(50).mean().iloc[-1]
                
                # LÓGICA DE LA ESTRATEGIA (Fase 2)
                # 1. Precio encima de medias clave
                tendencia_alcista = (precio > sma_150) and (precio > sma_200)
                # 2. Estructura correcta (150 > 200)
                estructura_medias = sma_150 > sma_200
                
                if tendencia_alcista and estructura_medias:
                    # Cálculo de fuerza
                    vol_rel = vol_hoy / vol_medio if vol_medio > 0 else 0
                    distancia_media = ((precio - sma_200)/sma_200)
                    
                    # Filtro de seguridad: que no esté exageradamente extendida (>60%)
                    if distancia_media < 0.6: 
                        resultados.append({
                            "Symbol": ticker,
                            "Precio": precio,
                            "Vol_Relativo": vol_rel,
                            "Dist_SMA200": distancia_media,
                            "Link": f"https://finviz.com/quote.ashx?t={ticker}", # Enlace a Finviz
                            "Estado": "🔥 ROTURA" if vol_rel > 1.5 else "✅ Tendencia"
                        })
        except:
            pass # Si falla un ticker, pasamos al siguiente
        
        # Actualizar barra
        my_bar.progress((i + 1) / total)
    
    my_bar.empty() # Borrar barra al terminar
    return pd.DataFrame(resultados)

# --- 3. BARRA LATERAL (CONTROLES) ---
with st.sidebar:
    st.title("🛡️ Swing Scanner")
    st.caption("Terminal de Análisis Institucional")
    st.divider()
    
    uploaded_file = st.file_uploader("📂 1. Cargar 'nasdaq_screener.csv'", type=["csv"])
    
    st.subheader("⚙️ 2. Filtros")
    min_p = st.number_input("Precio Mínimo ($)", 10.0, 1000.0, 15.0)
    min_v = st.number_input("Volumen Mínimo", 50000, 5000000, 150000)
    
    st.divider()
    modo_turbo = st.toggle("⚡ Modo Turbo (Solo 50)", value=True, help="Desactiva para escanear TODO el mercado (tarda más)")
    
    run_btn = st.button("🔍 ESCANEAR AHORA", type="primary", use_container_width=True)
    
    st.info("💡 Consejo: Busca 'Roturas' con Volumen > 2.0x y comprueba noticias.")

# --- 4. DASHBOARD PRINCIPAL ---
if run_btn and uploaded_file:
    try:
        # Carga y limpieza
        df_raw = pd.read_csv(uploaded_file)
        df_raw.columns = [c.strip() for c in df_raw.columns]
        # Limpiar símbolo $ si existe
        if df_raw['Last Sale'].dtype == object:
            df_raw['Last Sale'] = df_raw['Last Sale'].replace({'\$': '', ',': ''}, regex=True).astype(float)

        # Ejecutar Motor
        df_res = analizar_mercado(df_raw, min_p, min_v, modo_turbo)

        if not df_res.empty:
            # --- KPIs (Indicadores Clave) ---
            top_roturas = df_res[df_res['Estado'] == "🔥 ROTURA"]
            best_pick = df_res.sort_values('Vol_Relativo', ascending=False).iloc[0]['Symbol']
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Empresas Escaneadas", len(df_raw) if not modo_turbo else 50)
            col2.metric("Oportunidades", len(df_res))
            col3.metric("🔥 Roturas Hoy", len(top_roturas))
            col4.metric("🏆 Top Volumen", best_pick)
            
            st.divider()

            # --- PESTAÑAS DE ANÁLISIS ---
            tab_table, tab_chart, tab_news = st.tabs(["💎 Tabla Filtrada", "📈 Gráfico Pro", "📰 Noticias y Contexto"])
            
            # PESTAÑA 1: TABLA
            with tab_table:
                st.dataframe(
                    df_res.sort_values(by="Vol_Relativo", ascending=False),
                    column_order=("Symbol", "Precio", "Vol_Relativo", "Dist_SMA200", "Estado", "Link"),
                    column_config={
                        "Symbol": "Ticker",
                        "Precio": st.column_config.NumberColumn(format="$%.2f"),
                        "Vol_Relativo": st.column_config.ProgressColumn(
                            "Fuerza Vol.", 
                            format="%.1fx", 
                            min_value=0, 
                            max_value=10,
                            help="Volumen de hoy vs la media. Buscamos > 1.5x"
                        ),
                        "Dist_SMA200": st.column_config.NumberColumn(
                            "Extensión", 
                            format="%.1f%%",
                            help="Distancia a la media de 200. Si es >50%, cuidado."
                        ),
                        "Link": st.column_config.LinkColumn(
                            "Análisis", display_text="Ver en Finviz"
                        ),
                        "Estado": st.column_config.TextColumn("Señal")
                    },
                    use_container_width=True,
                    height=600
                )
            
            # PESTAÑA 2: GRÁFICO TRADINGVIEW
            with tab_chart:
                col_sel, col_empty = st.columns([1, 4])
                with col_sel:
                    # Selector de Ticker (por defecto el mejor)
                    ticker_sel = st.selectbox("Selecciona Acción:", df_res.sort_values(by="Vol_Relativo", ascending=False)['Symbol'])
                
                # Widget HTML de TradingView
                tv_widget = f"""
                <div class="tradingview-widget-container" style="height:500px;width:100%">
                  <div id="tradingview_chart"></div>
                  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                  <script type="text/javascript">
                  new TradingView.widget(
                  {{
                  "autosize": true,
                  "symbol": "{ticker_sel}",
                  "interval": "D",
                  "timezone": "Etc/UTC",
                  "theme": "dark",
                  "style": "1",
                  "locale": "es",
                  "toolbar_bg": "#f1f3f6",
                  "enable_publishing": false,
                  "allow_symbol_change": true,
                  "container_id": "tradingview_chart"
                  }}
                  );
                  </script>
                </div>
                """
                components.html(tv_widget, height=500)
            
            # PESTAÑA 3: NOTICIAS
            with tab_news:
                st.subheader(f"🗞️ Últimas noticias de {ticker_sel}")
                st.caption("Fuente: Yahoo Finance Live")
                try:
                    tick_obj = yf.Ticker(ticker_sel)
                    news = tick_obj.news
                    
                    if news:
                        for n in news[:5]: # Top 5 noticias
                            with st.container():
                                # Diseño limpio de noticia
                                st.markdown(f"#### [{n['title']}]({n['link']})")
                                if 'publisher' in n:
                                    st.caption(f"Publicado por: {n['publisher']}")
                                st.divider()
                    else:
                        st.info("No se encontraron noticias recientes para este valor.")
                except Exception as e:
                    st.warning("No se pudieron cargar las noticias en este momento.")

        else:
            st.warning("⚠️ No se encontraron empresas. Intenta bajar el precio mínimo o el volumen.")
            
    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")

else:
    # PANTALLA DE INICIO (Cuando no has subido nada)
    st.markdown("""
    <div style='text-align: center; padding-top: 50px;'>
        <h1>👋 Bienvenido a tu Terminal</h1>
        <p style='font-size: 18px; color: gray;'>
            Sube el archivo <b>nasdaq_screener.csv</b> en la barra lateral para comenzar.
        </p>
    </div>
    """, unsafe_allow_html=True)
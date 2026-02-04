import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# --- 1. CONFIGURACIÓN VISUAL PRO ---
st.set_page_config(
    page_title="Swing Screener",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para "tunear" la web
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
    </style>
    """, unsafe_allow_html=True)

# --- 2. CEREBRO MATEMÁTICO (Tu lógica intacta) ---
@st.cache_data(ttl=3600) # Guardar en caché para que vaya más rápido
def analizar_mercado(df_input, min_price, min_vol, limit):
    candidatos = df_input[
        (df_input['Last Sale'] >= min_price) & 
        (df_input['Volume'] >= min_vol)
    ]['Symbol'].tolist()
    
    if limit:
        candidatos = candidatos[:50] # Modo rápido
    
    resultados = []
    
    # Barra de progreso visual
    progress_text = "Escaneando el mercado..."
    my_bar = st.progress(0, text=progress_text)
    
    for i, ticker in enumerate(candidatos):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            
            if len(hist) > 200:
                precio = hist['Close'].iloc[-1]
                vol_hoy = hist['Volume'].iloc[-1]
                vol_medio = hist['Volume'].rolling(50).mean().iloc[-1]
                sma_200 = hist['Close'].rolling(200).mean().iloc[-1]
                sma_150 = hist['Close'].rolling(150).mean().iloc[-1]
                
                # Lógica
                tendencia = (precio > sma_150) and (precio > sma_200) and (sma_150 > sma_200)
                vol_rel = vol_hoy / vol_medio if vol_medio > 0 else 0
                
                if tendencia:
                    resultados.append({
                        "Symbol": ticker,
                        "Precio": precio,
                        "Vol_Relativo": vol_rel,
                        "Dist_SMA200": ((precio - sma_200)/sma_200), # Decimal para formato %
                        "Volumen_Real": vol_hoy,
                        "Link": f"https://finance.yahoo.com/quote/{ticker}",
                        "Estado": "🔥 ROTURA" if vol_rel > 1.5 else "✅ Tendencia"
                    })
        except:
            pass
        my_bar.progress((i + 1) / len(candidatos))
    
    my_bar.empty()
    return pd.DataFrame(resultados)

# --- 3. INTERFAZ GRÁFICA (SIDEBAR) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/10458/10458852.png", width=80)
    st.title("Swing Scanner")
    st.caption("Herramienta de Análisis Fase 2")
    st.divider()
    
    uploaded_file = st.file_uploader("📂 Cargar 'nasdaq_screener.csv'", type=["csv"])
    
    st.subheader("⚙️ Filtros")
    min_p = st.number_input("Precio Mínimo ($)", 10.0, 1000.0, 15.0)
    min_v = st.number_input("Volumen Mínimo", 50000, 5000000, 150000)
    
    st.divider()
    modo_turbo = st.toggle("⚡ Modo Turbo (50 empresas)", value=True)
    
    run_btn = st.button("🔍 ESCANEAR MERCADO", type="primary", use_container_width=True)

# --- 4. DASHBOARD PRINCIPAL ---
if run_btn and uploaded_file:
    try:
        # Carga inicial
        df_raw = pd.read_csv(uploaded_file)
        # Limpieza rápida
        df_raw.columns = [c.strip() for c in df_raw.columns]
        if df_raw['Last Sale'].dtype == object:
            df_raw['Last Sale'] = df_raw['Last Sale'].replace({'\$': '', ',': ''}, regex=True).astype(float)

        # Ejecutar análisis
        df_res = analizar_mercado(df_raw, min_p, min_v, modo_turbo)

        if not df_res.empty:
            # --- SECCIÓN A: MÉTRICAS (KPIs) ---
            top_roturas = df_res[df_res['Estado'] == "🔥 ROTURA"]
            
            st.markdown("### 📊 Resumen de Mercado")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            
            kpi1.metric("Empresas Analizadas", len(df_raw) if not modo_turbo else 50)
            kpi2.metric("Oportunidades Fase 2", len(df_res))
            kpi3.metric("🔥 Roturas Explosivas", len(top_roturas), delta="Prioridad Alta")
            best_pick = df_res.sort_values('Vol_Relativo', ascending=False).iloc[0]['Symbol']
            kpi4.metric("🏆 Top Pick del Día", best_pick)
            
            st.divider()

            # --- SECCIÓN B: TABLA INTERACTIVA ---
            tab_main, tab_chart = st.tabs(["💎 Tabla de Oportunidades", "📈 Análisis Visual"])
            
            with tab_main:
                # Configuración de columnas para que se vean bonitas
                st.dataframe(
                    df_res.sort_values(by="Vol_Relativo", ascending=False),
                    column_order=("Symbol", "Precio", "Vol_Relativo", "Dist_SMA200", "Estado", "Link"),
                    column_config={
                        "Symbol": "Ticker",
                        "Precio": st.column_config.NumberColumn(format="$%.2f"),
                        "Vol_Relativo": st.column_config.ProgressColumn(
                            "Fuerza Institucional", 
                            format="%.1fx", 
                            min_value=0, 
                            max_value=10,
                            help="Cuanto más llena la barra, más compra institucional."
                        ),
                        "Dist_SMA200": st.column_config.NumberColumn(
                            "Distancia Media", 
                            format="%.1f%%"
                        ),
                        "Link": st.column_config.LinkColumn(
                            "Yahoo", display_text="Ver Gráfico"
                        ),
                        "Estado": st.column_config.TextColumn("Señal")
                    },
                    use_container_width=True,
                    height=500
                )
            
            with tab_chart:
                col_sel, col_graph = st.columns([1, 3])
                with col_sel:
                    ticker_sel = st.selectbox("Selecciona empresa para ver gráfico:", df_res['Symbol'])
                    
                with col_graph:
                    # Gráfico rápido con Plotly
                    stock_chart = yf.Ticker(ticker_sel)
                    hist_chart = stock_chart.history(period="6mo")
                    
                    fig = go.Figure(data=[go.Candlestick(x=hist_chart.index,
                        open=hist_chart['Open'], high=hist_chart['High'],
                        low=hist_chart['Low'], close=hist_chart['Close'])])
                    
                    fig.update_layout(title=f"Gráfico Semanal - {ticker_sel}", template="plotly_dark", height=400)
                    st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("No se encontraron resultados con estos filtros.")
            
    except Exception as e:
        st.error(f"Error en el archivo: {e}")

else:
    # Pantalla de bienvenida vacía
    st.markdown("""
    <div style='text-align: center; padding: 50px;'>
        <h1>👋 Bienvenido a tu Terminal Swing</h1>
        <p>Sube el archivo CSV en la izquierda para comenzar el análisis.</p>
    </div>
    """, unsafe_allow_html=True)
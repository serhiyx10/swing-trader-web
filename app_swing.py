import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Swing Sniper", layout="wide", page_icon="📈")

st.title("📈 Escáner de Oportunidades Swing Trade")
st.markdown("""
Esta herramienta busca patrones de **Fase 2 + Volumen Institucional** basándose en la estrategia de rotura.
***
""")

# --- BARRA LATERAL (CONFIGURACIÓN) ---
st.sidebar.header("Configuración del Escáner")
uploaded_file = st.sidebar.file_uploader("1. Sube el archivo Nasdaq (CSV)", type="csv")
min_precio = st.sidebar.number_input("Precio Mínimo ($)", value=10.0)
min_vol = st.sidebar.number_input("Volumen Mínimo Diario", value=150000)
test_mode = st.sidebar.checkbox("Modo Prueba (Solo 50 empresas)", value=True)

# --- FUNCIONES DE LÓGICA (TU MOTOR) ---
def analizar_ticker(symbol, progress_text):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="1y")
        
        if len(hist) < 200: return None
        
        # Datos
        precio = hist['Close'].iloc[-1]
        vol_ayer = hist['Volume'].iloc[-1]
        vol_medio = hist['Volume'].rolling(50).mean().iloc[-1]
        
        # Medias
        sma_50 = hist['Close'].rolling(50).mean().iloc[-1]
        sma_150 = hist['Close'].rolling(150).mean().iloc[-1]
        sma_200 = hist['Close'].rolling(200).mean().iloc[-1]
        
        # Tendencia SMA 200
        sma_200_ayer = hist['Close'].rolling(200).mean().iloc[-2]
        sma_200_alcista = sma_200 > sma_200_ayer
        
        # Condiciones
        cond_precio = (precio > sma_150) and (precio > sma_200)
        cond_medias = (sma_150 > sma_200)
        max_52s = hist['High'].max()
        cerca_maximos = precio >= (0.75 * max_52s)
        
        if not (cond_precio and cond_medias and sma_200_alcista and cerca_maximos):
            return None
            
        # Filtro Volumen
        vol_spike = vol_ayer > (1.5 * vol_medio)
        
        # Filtro Earnings (Simplificado para velocidad)
        riesgo_earnings = "No"
        try:
            cal = stock.calendar
            if cal is not None and not cal.empty:
                fechas = cal.iloc[0]
                if isinstance(fechas, (list, pd.Series)): # A veces es lista
                    prox_fecha = fechas[0]
                else:
                    prox_fecha = fechas
                
                # Chequeo simple de fecha
                # (Aquí iría lógica compleja de fecha, simplificamos para la UI)
                riesgo_earnings = "Verificar Manual"
        except:
            pass

        return {
            "Symbol": symbol,
            "Precio": round(precio, 2),
            "Vol_Relativo": round(vol_ayer / vol_medio, 2),
            "Dist_SMA200_%": round(((precio - sma_200)/sma_200)*100, 1),
            "Nota": "🔥 Rotura con Volumen" if vol_spike else "✅ Tendencia Fuerte"
        }

    except Exception as e:
        return None

# --- BOTÓN DE EJECUCIÓN ---
if st.sidebar.button("🚀 INICIAR ESCÁNER"):
    if uploaded_file is not None:
        try:
            # Leer CSV subido
            df_input = pd.read_csv(uploaded_file)
            
            # Limpieza inicial
            df_input.columns = [c.strip() for c in df_input.columns]
            if df_input['Last Sale'].dtype == object:
                df_input['Last Sale'] = df_input['Last Sale'].replace({'\$': '', ',': ''}, regex=True).astype(float)
            
            # Filtrar universo
            candidatos = df_input[
                (df_input['Last Sale'] >= min_precio) & 
                (df_input['Volume'] >= min_vol)
            ]['Symbol'].tolist()
            
            st.info(f"Analizando {len(candidatos)} empresas filtradas por liquidez...")
            
            # Limitar si es modo prueba
            if test_mode:
                candidatos = candidatos[:50]
                st.warning("⚠️ MODO PRUEBA ACTIVADO: Solo analizando las primeras 50.")

            # BARRA DE PROGRESO
            my_bar = st.progress(0)
            resultados = []
            total = len(candidatos)
            place_holder = st.empty()
            
            for i, ticker in enumerate(candidatos):
                # Actualizar barra y texto
                progreso = (i + 1) / total
                my_bar.progress(progreso)
                place_holder.text(f"Analizando: {ticker}...")
                
                res = analizar_ticker(ticker, place_holder)
                if res:
                    resultados.append(res)
            
            place_holder.text("¡Análisis Completado!")
            my_bar.empty()
            
            # --- MOSTRAR RESULTADOS ---
            if resultados:
                df_res = pd.DataFrame(resultados)
                
                # Separar las ROTURAS (Lo importante)
                st.subheader(f"💎 Joyas Encontradas ({len(df_res)})")
                
                # Configurar la tabla para que coloree el volumen alto
                st.dataframe(
                    df_res.style.background_gradient(subset=['Vol_Relativo'], cmap="Greens"),
                    use_container_width=True,
                    height=600
                )
                
                # Botón de descarga
                csv = df_res.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "💾 Descargar Excel/CSV",
                    csv,
                    "Resultados_Swing.csv",
                    "text/csv"
                )
                
            else:
                st.error("Ninguna empresa cumplió los criterios hoy.")
                
        except Exception as e:
            st.error(f"Error con el archivo: {e}")
    else:
        st.warning("👈 Por favor, sube el archivo 'nasdaq_screener.csv' en la barra lateral.")

else:
    st.write("👈 Sube el archivo CSV y pulsa 'Iniciar Escáner' para comenzar.")
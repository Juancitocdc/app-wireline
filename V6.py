


import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import base64

# ==========================================
# CONFIGURACIÓN BÁSICA DE STREAMLIT
# ==========================================
st.set_page_config(page_title="App Wireline", layout="wide")
st.title("Seguimiento de Operaciones - Wireline")

# ==========================================
# 0. FUNCIÓN PARA LEER LA IMAGEN DE FONDO
# ==========================================
@st.cache_data
def cargar_imagen_base64(ruta):
    try:
        with open(ruta, "rb") as img_file:
            encoded_string = base64.b64encode(img_file.read()).decode()
            return f"data:image/jpeg;base64,{encoded_string}"
    except FileNotFoundError:
        return None

# Cargamos tu imagen de fondo (verifica la ruta)
ruta_imagen = "pala.jpg"
imagen_uri = cargar_imagen_base64(ruta_imagen)

# ==========================================
# 1. CARGA DE DATOS (CON CACHÉ)
# ==========================================
@st.cache_data
def cargar_datos():
    ruta_excel = "Wireline_Python (1).xlsx"
    df = pd.read_excel(ruta_excel)
    
    df.columns = df.columns.str.strip()
    
    col_yac = [col for col in df.columns if 'yaci' in col.lower()][0]
    col_pad = [col for col in df.columns if 'pad' in col.lower()][0]
    col_pozo = [col for col in df.columns if 'pozo' in col.lower()][0]
    
    col_tapon = [col for col in df.columns if 'Tapón' in col or 'Tapon' in col][0]
    col_carga = [col for col in df.columns if 'Carga' in col][0]
    col_cluster = [col for col in df.columns if 'Clus' in col][0]
    col_fase = [col for col in df.columns if 'Fase' in col][0]
    col_densidad = [col for col in df.columns if 'Densidad' in col][0]
    col_metros = [col for col in df.columns if 'Metros' in col][0]

    df[col_tapon] = df[col_tapon].fillna('Pendiente')
    df[col_carga] = df[col_carga].fillna('Pendiente')
    df[col_cluster] = df[col_cluster].fillna(0)
    df[col_fase] = df[col_fase].fillna('-')
    df[col_densidad] = df[col_densidad].fillna('-')

    df['Config Disparo'] = df.apply(
        lambda x: f"{x[col_carga]} | {x[col_cluster]}cls | {x[col_fase]} | {x[col_densidad]}" 
        if pd.notna(x[col_metros]) else 'Pendiente', 
        axis=1
    )
    
    return df, col_yac, col_pad, col_pozo, col_tapon, col_carga, col_cluster, col_fase, col_densidad, col_metros

df_base, col_yac, col_pad, col_pozo, col_tapon, col_carga, col_cluster, col_fase, col_densidad, col_metros = cargar_datos()

# ==========================================
# 2. FILTROS EN STREAMLIT
# ==========================================
st.markdown("### 🔍 Filtros")
f1, f2, f3 = st.columns(3)

yac_opts = ["Todos"] + sorted(df_base[col_yac].dropna().unique().tolist())
sel_yac = f1.selectbox("Yacimiento:", yac_opts)
df_tmp = df_base[df_base[col_yac] == sel_yac] if sel_yac != "Todos" else df_base

pad_opts = ["Todos"] + sorted(df_tmp[col_pad].dropna().unique().tolist())
sel_pad = f2.selectbox("PAD:", pad_opts)
if sel_pad != "Todos": 
    df_tmp = df_tmp[df_tmp[col_pad] == sel_pad]

pozo_opts = ["Todos"] + sorted(df_tmp[col_pozo].dropna().unique().tolist())
sel_pozo = f3.selectbox("Pozo:", pozo_opts)
if sel_pozo != "Todos": 
    df_tmp = df_tmp[df_tmp[col_pozo] == sel_pozo]

st.divider()

# ==========================================
# 3. LÓGICA DE GRÁFICO (DICCIONARIO EN CÓDIGO)
# ==========================================
if not df_tmp.empty:
    
    # --- 1. DICCIONARIO MANUAL DE ETAPAS DE DISEÑO ---
    etapas_diseno = {
        'FP-1461(h)': 71,
        'FP-1462(h)': 70,
        'FP-1463(h)': 71,
        'FP-1464(h)': 67
    }
    
    max_etapas_reales = df_tmp.groupby(col_pozo)['Etapa'].max().to_dict()

    # --- 2. CREAR LA GRILLA DE ETAPAS ---
    pozos_filtrados = df_tmp[col_pozo].unique()
    filas_grilla = []
    
    for pozo in pozos_filtrados:
        etapas_reales_del_pozo = int(max_etapas_reales.get(pozo, 0))
        max_etapas = max(etapas_reales_del_pozo, etapas_diseno.get(pozo, etapas_reales_del_pozo))
        
        for e in range(1, max_etapas + 1):
            filas_grilla.append({col_pozo: pozo, 'Etapa': e})
            
    df_grilla = pd.DataFrame(filas_grilla)
    
    df_tmp = pd.merge(df_grilla, df_tmp, on=[col_pozo, 'Etapa'], how='left')
    
    df_tmp[col_tapon] = df_tmp[col_tapon].fillna('Pendiente')
    df_tmp[col_carga] = df_tmp[col_carga].fillna('Pendiente')
    df_tmp[col_cluster] = df_tmp[col_cluster].fillna(0)
    df_tmp[col_fase] = df_tmp[col_fase].fillna('-')
    df_tmp[col_densidad] = df_tmp[col_densidad].fillna('-')
    df_tmp['Config Disparo'] = df_tmp['Config Disparo'].fillna('Pendiente')

    # --- 3. DEFINICIÓN DE COLORES Y HOVER (CON REGLA PARA ETAPA 1) ---
    color_estado = []
    color_tapon = []
    color_config = []
    hover_text = []

    # Preparamos las paletas de colores
    tapones_unicos = df_base[col_tapon].unique() 
    paleta_tapon = px.colors.qualitative.Set1
    mapa_tapon = {tapon: paleta_tapon[i % len(paleta_tapon)] for i, tapon in enumerate(tapones_unicos)}
    mapa_tapon['Pendiente'] = '#444444'

    configs_unicas = df_base['Config Disparo'].unique()
    paleta_config = px.colors.qualitative.Plotly
    mapa_config = {conf: paleta_config[i % len(paleta_config)] for i, conf in enumerate(configs_unicas)}
    mapa_config['Pendiente'] = '#444444'

    # Recorremos fila por fila para aplicar las reglas de la Etapa 1
    for index, row in df_tmp.iterrows():
        e = row['Etapa']
        
        # Regla de Colores
        if e == 1:
            color_estado.append('#2ca02c') # Verde forzado
            color_tapon.append('#ffffff')  # Blanco forzado
            color_config.append('#ffffff') # Blanco forzado
            
            # Hover limpio para BPS
            hover_text.append(f"<b>Pozo:</b> {row[col_pozo]}<br><b>Etapa:</b> 1<br><b>BPS</b>")
        else:
            # Colores normales
            color_estado.append('#2ca02c' if pd.notna(row[col_metros]) else '#444444')
            color_tapon.append(mapa_tapon.get(row[col_tapon], '#444444'))
            color_config.append(mapa_config.get(row['Config Disparo'], '#444444'))
            
            # Hover completo con redondeo
            m_val = round(row[col_metros], 2) if pd.notna(row[col_metros]) else "nan"
            hover_text.append(
                f"<b>Pozo:</b> {row[col_pozo]}<br>"
                f"<b>Etapa:</b> {e}<br>"
                f"---<br>"
                f"<b>Tapón:</b> {row[col_tapon]}<br>"
                f"<b>Carga:</b> {row[col_carga]}<br>"
                f"<b>Clusters:</b> {row[col_cluster]} | "
                f"<b>Fase:</b> {row[col_fase]} | "
                f"<b>Densidad:</b> {row[col_densidad]}<br>"
                f"<b>Metros Efectivos:</b> {m_val} m"
            )

    # --- 4. CONSTRUCCIÓN DE LA FIGURA PLOTLY ---
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_tmp['Etapa'],
        y=df_tmp[col_pozo],
        mode='markers',
        marker=dict(symbol='square', size=16, color=color_estado, line=dict(width=1, color='black')),
        text=hover_text,
        hoverinfo="text"
    ))

    # Inyección de la imagen de fondo
    # if imagen_uri:
    #     fig.add_layout_image(
    #         dict(
    #             source=imagen_uri,
    #             xref="paper", yref="paper",
    #             x=0, y=1,
    #             sizex=1, sizey=1,
    #             xanchor="left", yanchor="top",
    #             sizing="stretch",
    #             opacity=0.3, 
    #             layer="below"
    #         )
    #     )

# --- CÁLCULO DE ALTURA DINÁMICA ---
    # Contamos cuántos pozos únicos hay en la vista actual
    cantidad_pozos = len(df_tmp[col_pozo].unique())
    
    # Le damos 35 píxeles de altura a cada pozo, con un mínimo de 500px en total
    altura_dinamica = max(500, cantidad_pozos * 35)

    # Configuración del layout
    fig.update_layout(
        title=f'Vista PAD ({cantidad_pozos} pozos filtrados)',
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='#1e1e1e',
        font=dict(color='white'),
        xaxis=dict(title='Número de Etapa', autorange="reversed", tickmode='linear', dtick=2),
        
        # Agregamos dtick=1 al eje Y para forzar a que muestre TODOS los nombres de los pozos
        yaxis=dict(title='', categoryorder='category descending', dtick=1), 
        
        height=altura_dinamica, # <-- Usamos la variable dinámica aquí en lugar del 500 fijo
        
        updatemenus=[dict(
            buttons=list([
                dict(args=[{"marker.color": [color_estado]}], label="Vista: Estado", method="restyle"),
                dict(args=[{"marker.color": [color_tapon]}], label="Vista: Tipo de Tapón", method="restyle"),
                dict(args=[{"marker.color": [color_config]}], label="Vista: Configuración", method="restyle")
            ]),
            direction="down", pad={"r": 10, "t": 10}, showactive=True,
            x=0.01, xanchor="left", y=1.2, yanchor="top", bgcolor="#333333", bordercolor="white"
        )]
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("No hay datos para la combinación de filtros seleccionada.")
# -*- coding: utf-8 -*-
"""
Created on Thu May  8 17:38:32 2025

@author: jahop
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import folium_static
from datetime import datetime
import numpy as np
import os
from scipy.spatial import ConvexHull
from fpdf import FPDF

# Configuración de la página
st.set_page_config(page_title="Análisis de Pozos Exploratorios - SENER", layout="wide")
st.title("🔍 SENER: Dashboard de Análisis de Pozos Exploratorios")

# 1. Carga automática del archivo Excel
ARCHIVO_EXCEL = "nombre-de-los-pozos-exploratorios.xlsx"

# Verificar si el archivo existe
if os.path.exists(ARCHIVO_EXCEL):
    try:
        df = pd.read_excel(ARCHIVO_EXCEL)

        # Limpieza básica de datos - manejo de valores nulos
        df = df.replace(['NA', 'N/A', 'NaN', 'nan', None], np.nan)
        
        # Limpieza de columnas numéricas
        numeric_cols = ["Profundidad total (m)", "intervalo_productor_m", "Clave estatal"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(",", ""),
                    errors='coerce'
                )

        # Convertir fechas y calcular días de perforación
        date_columns = ["Fecha de inicio de perforación", "Fecha de fin de terminación"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

        if all(col in df.columns for col in date_columns):
            df["Días de perforación"] = (
                df["Fecha de fin de terminación"] - df["Fecha de inicio de perforación"]
            ).dt.days

        # 2. Mostrar todos los datos
        st.header("📝 Datos Completos del Archivo")
        st.dataframe(df, height=400, use_container_width=True)

        # 3. Sidebar con filtros y búsqueda
        #st.sidebar.header("🔧 Filtros Avanzados")
        
        # 3. Sidebar con filtros y búsqueda
        st.sidebar.markdown("**👤 Javier Horacio Pérez Ricárdez**")
        st.sidebar.markdown("** Mayo del 2025 **")
        st.sidebar.header("🔧 Filtros Avanzados")
        
        
        
        # Sistema de búsqueda
        search_term = st.sidebar.text_input("Buscar pozos por nombre")
        if search_term:
            df_search = df[df["Nombre del pozo exploratorio terminado"].astype(str).str.contains(search_term, case=False, na=False)]
            if not df_search.empty:
                st.subheader(f"Resultados de búsqueda para: '{search_term}'")
                st.dataframe(df_search)
            else:
                st.warning(f"No se encontraron pozos con el término '{search_term}'")

        filter_cols = ["Región", "Régimen", "Cuenca", "Resultado del pozo exploratorio", "Ubicación"]
        for col in filter_cols:
            if col in df.columns:
                options = ["Todos"] + [str(x) for x in df[col].dropna().unique()]
                selected = st.sidebar.selectbox(f"Filtrar por {col}", options)
                if selected != "Todos":
                    df = df[df[col].astype(str) == selected]

        # 4. KPIs clave
        st.header("📊 Métricas Clave")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total de Pozos", len(df))

        with col2:
            if "Resultado del pozo exploratorio" in df.columns:
                pozos_exitosos = df[
                    df["Resultado del pozo exploratorio"].astype(str).str.contains("Productor", na=False, case=False)
                ].shape[0]
                porcentaje = int((pozos_exitosos / len(df)) * 100) if len(df) > 0 else 0
                st.metric("Pozos Exitosos", f"{pozos_exitosos} ({porcentaje}%)")

        with col3:
            if "Profundidad total (m)" in df.columns:
                avg_depth = round(df["Profundidad total (m)"].mean(), 0)
                st.metric("Profundidad Promedio", f"{avg_depth} m" if not pd.isna(avg_depth) else "N/A")
        
        with col4:
            if "Días de perforación" in df.columns:
                avg_days = round(df["Días de perforación"].mean(), 0)
                st.metric("Días promedio perforación", f"{avg_days} días" if not pd.isna(avg_days) else "N/A")

        # 5. KPIs Adicionales
        st.header("📈 KPIs Adicionales")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)

        with kpi1:
            if "intervalo_productor_m" in df.columns:
                avg_interval = df["intervalo_productor_m"].mean()
                st.metric("Intervalo productor promedio", f"{round(avg_interval,1)} m" if not pd.isna(avg_interval) else "N/A")

        with kpi2:
            if "Ubicación" in df.columns:
                terrestres = df[df["Ubicación"] == "Terrestre"].shape[0]
                st.metric("Pozos terrestres", terrestres)

        with kpi3:
            if "Ubicación" in df.columns:
                marinos = df[df["Ubicación"] == "Marino"].shape[0]
                st.metric("Pozos marinos", marinos)

        with kpi4:
            if "Régimen" in df.columns:
                asignaciones = df[df["Régimen"] == "Asignación"].shape[0]
                st.metric("Pozos en asignación", asignaciones)

        # 6. Análisis Temporal
        if all(col in df.columns for col in ["Fecha de inicio de perforación", "Resultado del pozo exploratorio"]):
            st.header("📅 Evolución Temporal de Perforación")
            
            df["Año"] = df["Fecha de inicio de perforación"].dt.year
            temporal_df = df.groupby(["Año", "Resultado del pozo exploratorio"]).size().unstack().fillna(0)
            
            fig = px.bar(temporal_df, 
                         x=temporal_df.index, 
                         y=temporal_df.columns,
                         title="Pozos perforados por año y resultado",
                         labels={'value':'Número de pozos', 'variable':'Resultado'},
                         barmode='stack')
            st.plotly_chart(fig, use_container_width=True)

        # 7. Análisis por Régimen Contractual
        if "Régimen" in df.columns:
            st.header("📑 Distribución por Régimen Contractual")
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(df, names="Régimen", 
                             title="Distribución por régimen contractual")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.histogram(df, x="Régimen", color="Resultado del pozo exploratorio",
                                  title="Resultados por régimen contractual",
                                  barmode='group')
                st.plotly_chart(fig, use_container_width=True)

        # 8. Análisis de Profundidades
        if "Profundidad total (m)" in df.columns:
            st.header("⛏ Análisis de Profundidades")
            
            fig = px.box(df, x="Resultado del pozo exploratorio", y="Profundidad total (m)",
                        title="Distribución de profundidades por resultado")
            st.plotly_chart(fig, use_container_width=True)
            
            fig = px.histogram(df, x="Profundidad total (m)", nbins=30,
                              color="Resultado del pozo exploratorio",
                              marginal="rug",
                              title="Distribución de profundidades")
            st.plotly_chart(fig, use_container_width=True)

        # 9. Análisis Geológico (con manejo de nulos)
        if "Objetivo geológico" in df.columns and "Resultado del pozo exploratorio" in df.columns:
            st.header("🪨 Análisis por Objetivo Geológico")
            
            # Filtrar filas con valores nulos
            df_geo = df.dropna(subset=["Objetivo geológico", "Resultado del pozo exploratorio"])
            
            if not df_geo.empty:
                fig = px.sunburst(df_geo, 
                                path=['Objetivo geológico', 'Resultado del pozo exploratorio'],
                                title="Relación entre objetivo geológico y resultados")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No hay datos suficientes para mostrar el análisis geológico (valores nulos)")

        # 10. Mapa de pozos exploratorios (con verificación de coordenadas)
        st.header("🗺 Mapa de Ubicación de Pozos Exploratorios")

        coordenadas_entidades = {
            'Campeche': (19.8300, -90.5000),
            'Chiapas': (16.7500, -93.1167),
            'Coahuila de Zaragoza': (27.3000, -102.0500),
            'Nuevo León': (25.6667, -100.3000),
            'Oaxaca': (17.0667, -96.7167),
            'Puebla': (19.0333, -98.1833),
            'Tabasco': (17.9667, -92.5833),
            'Tamaulipas': (24.2667, -98.8333),
            'Veracruz de Ignacio de la Llave': (19.4333, -96.3833)
        }

        if "Entidad Federativa" in df.columns:
            # Asignar coordenadas base
            df["Latitud_Base"] = df["Entidad Federativa"].map(lambda x: coordenadas_entidades.get(x, (23.6345, -102.5528))[0])
            df["Longitud_Base"] = df["Entidad Federativa"].map(lambda x: coordenadas_entidades.get(x, (23.6345, -102.5528))[1])

            # Generar coordenadas aleatorias alrededor del punto base
            np.random.seed(42)
            df["Latitud"] = df["Latitud_Base"] + np.random.uniform(-0.2, 0.2, len(df))
            df["Longitud"] = df["Longitud_Base"] + np.random.uniform(-0.2, 0.2, len(df))

            # Filtrar filas con coordenadas válidas
            df_mapa = df.dropna(subset=["Latitud", "Longitud"])
            
            if not df_mapa.empty:
                m = folium.Map(location=[23.6345, -102.5528], zoom_start=5, tiles="cartodbpositron", control_scale=True)

                marker_cluster = MarkerCluster(name="Todos los pozos", overlay=True, control=True).add_to(m)

                for _, row in df_mapa.iterrows():
                    es_productor = "productor" in str(row.get("Resultado del pozo exploratorio", "")).lower()
                    icono = folium.Icon(
                        color='green' if es_productor else 'red',
                        icon='oil' if es_productor else 'remove',
                        prefix='fa'
                    )

                    popup_html = f"""
                    <div style="width: 250px">
                        <h4 style="margin-bottom:5px">{row.get('Nombre del pozo exploratorio terminado', 'N/A')}</h4>
                        <p><b>Entidad:</b> {row.get('Entidad Federativa', 'N/A')}<br>
                        <b>Municipio:</b> {row.get('Municipio', 'N/A')}<br>
                        <b>Resultado:</b> <span style="color:{'green' if es_productor else 'red'}">
                            {str(row.get('Resultado del pozo exploratorio', 'N/A'))}</span><br>
                        <b>Profundidad:</b> {str(row.get('Profundidad total (m)', 'N/A'))} m<br>
                        <b>Cuenca:</b> {str(row.get('Cuenca', 'N/A'))}</p>
                    </div>
                    """

                    folium.Marker(
                        location=[row["Latitud"], row["Longitud"]],
                        popup=folium.Popup(popup_html, max_width=300),
                        icon=icono,
                        tooltip=f"Pozo: {row.get('Nombre del pozo exploratorio terminado', 'N/A')}"
                    ).add_to(marker_cluster)

                # Capa de calor
                HeatMap(
                    data=df_mapa[['Latitud', 'Longitud']].values,
                    name="Densidad de pozos",
                    radius=15,
                    blur=10,
                    overlay=True,
                    control=True
                ).add_to(m)

                # Capa de cuencas (solo si hay datos suficientes)
                if "Cuenca" in df_mapa.columns:
                    cuencas_layer = folium.FeatureGroup(name="Cuencas", show=False)
                    
                    for cuenca, group in df_mapa.groupby("Cuenca"):
                        points = group[['Latitud', 'Longitud']].dropna().values
                        if len(points) > 2:
                            try:
                                hull = ConvexHull(points)
                                hull_points = points[hull.vertices]
                                folium.Polygon(
                                    locations=hull_points,
                                    color='blue',
                                    fill=True,
                                    fill_color='blue',
                                    fill_opacity=0.2,
                                    popup=f"Cuenca: {str(cuenca)}<br>Pozos: {len(group)}"
                                ).add_to(cuencas_layer)
                            except:
                                continue
                    
                    cuencas_layer.add_to(m)

                folium.LayerControl(position='topright', collapsed=False).add_to(m)
                folium_static(m, width=1000, height=600)

                st.success(f"✅ Mostrando {len(df_mapa)} pozos en el mapa")
                col1, col2 = st.columns(2)

                with col1:
                    st.metric(
                        "Pozos productores",
                        f"{sum(df_mapa['Resultado del pozo exploratorio'].astype(str).str.contains('Productor', case=False, na=False))}",
                        help="Marcados con iconos verdes"
                    )
                with col2:
                    st.metric(
                        "Pozos improductivos",
                        f"{sum(~df_mapa['Resultado del pozo exploratorio'].astype(str).str.contains('Productor', case=False, na=False))}",
                        help="Marcados con iconos rojos"
                    )
            else:
                st.warning("No hay datos con coordenadas válidas para mostrar el mapa")

        # 11. Exportar Resultados
        st.header("📤 Exportar Resultados")

        @st.cache_data
        def convert_df_to_csv(df):
            return df.to_csv(index=False).encode('utf-8')

        csv = convert_df_to_csv(df)
        st.download_button(
            "Descargar datos filtrados (CSV)",
            csv,
            "pozos_filtrados.csv",
            "text/csv",
            key='download-csv'
        )

        # Generar reporte PDF
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Reporte de Pozos Exploratorios - SENER", ln=1, align='C')
            pdf.cell(200, 10, txt=f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=2)
            pdf.cell(200, 10, txt=f"Total de pozos: {len(df)}", ln=3)
            
            if "Resultado del pozo exploratorio" in df.columns:
                pozos_exitosos = df[df["Resultado del pozo exploratorio"].astype(str).str.contains("Productor", na=False, case=False)].shape[0]
                pdf.cell(200, 10, txt=f"Pozos productores: {pozos_exitosos}", ln=4)
            
            if "Profundidad total (m)" in df.columns:
                pdf.cell(200, 10, txt=f"Profundidad promedio: {round(df['Profundidad total (m)'].mean(),0)} m", ln=5)
            
            pdf.output("reporte_pozos.pdf")
            
            with open("reporte_pozos.pdf", "rb") as f:
                st.download_button(
                    "Descargar reporte (PDF)",
                    f,
                    "reporte_pozos.pdf",
                    "application/pdf"
                )
        except Exception as e:
            st.warning(f"No se pudo generar el reporte PDF: {str(e)}")

    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        if 'df' in locals():
            st.write("Datos para diagnóstico:", df.head())
        else:
            st.write("No se pudo cargar el DataFrame")

else:
    st.error(f"No se encontró el archivo {ARCHIVO_EXCEL}. Por favor colóquelo en la misma carpeta que esta aplicación.")
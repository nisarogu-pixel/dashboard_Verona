import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from io import BytesIO

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Carnes Verona | Estudio de Tiempos",
    page_icon="🥩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CUSTOM CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0f1117; }
    [data-testid="stSidebar"] { background-color: #1a1d26; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130, #252840);
        border: 1px solid #2e3250;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-value { font-size: 2.2rem; font-weight: 700; color: #e8634a; }
    .metric-label { font-size: 0.85rem; color: #8892b0; margin-top: 4px; }
    .muda-badge {
        display: inline-block;
        background: #3d1f1f;
        color: #e8634a;
        border: 1px solid #7a2e2e;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 3px;
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #ccd6f6;
        border-left: 3px solid #e8634a;
        padding-left: 10px;
        margin: 20px 0 12px 0;
    }
    h1, h2, h3 { color: #ccd6f6 !important; }
    .stTabs [data-baseweb="tab"] { color: #8892b0; }
    .stTabs [aria-selected="true"] { color: #e8634a !important; border-bottom-color: #e8634a !important; }
    div[data-testid="stMetric"] label { color: #8892b0 !important; }
    div[data-testid="stMetric"] div { color: #ccd6f6 !important; }
</style>
""", unsafe_allow_html=True)

# ─── COLOR PALETTE ───────────────────────────────────────────────────────────────
COLORS = {
    "primary":   "#e8634a",
    "secondary": "#5e81f4",
    "accent":    "#56cfe1",
    "warning":   "#f4b942",
    "success":   "#52d68a",
    "bg":        "#1e2130",
    "grid":      "#2e3250",
    "text":      "#ccd6f6",
    "muted":     "#8892b0",
}
PROCESS_COLORS = ["#e8634a", "#5e81f4", "#56cfe1", "#52d68a"]
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#1a1d26",
    font=dict(color=COLORS["text"], family="Inter, sans-serif"),
    title_font=dict(color=COLORS["text"], size=15),
    xaxis=dict(gridcolor=COLORS["grid"], linecolor=COLORS["grid"], tickfont=dict(color=COLORS["muted"])),
    yaxis=dict(gridcolor=COLORS["grid"], linecolor=COLORS["grid"], tickfont=dict(color=COLORS["muted"])),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=COLORS["text"])),
    margin=dict(l=40, r=20, t=50, b=40),
)

# ─── DATA LOADING ────────────────────────────────────────────────────────────────
def parse_tiempo_col(series):
    """Normaliza columna Tiempo a segundos (int). Acepta números, HH:MM:SS y timedelta."""
    result = []
    for val in series:
        if pd.isna(val):
            result.append(np.nan)
        elif isinstance(val, (int, float)):
            result.append(float(val))
        elif hasattr(val, 'total_seconds'):          # timedelta
            result.append(val.total_seconds())
        else:
            try:
                parts = str(val).strip().split(":")
                if len(parts) == 3:
                    h, m, s = parts
                    result.append(int(h)*3600 + int(m)*60 + float(s))
                else:
                    result.append(float(val))
            except:
                result.append(np.nan)
    return result

@st.cache_data(show_spinner=False)
def load_excel(file_bytes):
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheets = {}
    for name in xl.sheet_names:
        df = pd.read_excel(BytesIO(file_bytes), sheet_name=name)

        # Normalizar columna de segundos: buscar Tiempo(s) primero, luego Segundos
        time_col = None
        for c in df.columns:
            if "tiempo(s)" in c.lower() or "segundos" in c.lower():
                time_col = c
                break
        if time_col is None:
            for c in df.columns:
                if "tiempo" in c.lower():
                    time_col = c
                    break

        if time_col:
            df["_segundos"] = parse_tiempo_col(df[time_col])
        else:
            df["_segundos"] = np.nan

        # Normalizar columna de operario
        op_col = next((c for c in df.columns if "operario" in c.lower()), None)
        df["_operario"] = df[op_col].str.strip() if op_col else "N/A"

        # Normalizar columna de actividad — labels únicos con prefijo J1, J2...
        actividad_col = None
        for label in ["observacion", "molido", "proceso.1", "chorizo"]:
            col = next((c for c in df.columns if label in c.lower()), None)
            if col:
                actividad_col = col
                break
        job_nums = [f"J{i+1}" for i in range(len(df))]
        if actividad_col:
            df["_actividad"] = [
                f"{j} - {str(a).strip()}" if pd.notna(a) and str(a).strip() != "" else j
                for j, a in zip(job_nums, df[actividad_col])
            ]
        else:
            df["_actividad"] = job_nums

        # Normalizar muda
        muda_col = next((c for c in df.columns if "muda" in c.lower()), None)
        df["_muda"] = df[muda_col].fillna("Sin muda") if muda_col else "Sin muda"

        # Normalizar temperatura
        temp_col = next((c for c in df.columns if "temperatura" in c.lower()), None)
        df["_temperatura"] = pd.to_numeric(df[temp_col], errors="coerce") if temp_col else np.nan

        # Unidades si existe
        uni_col = next((c for c in df.columns if "unidades" in c.lower()), None)
        df["_unidades"] = pd.to_numeric(df[uni_col], errors="coerce") if uni_col else np.nan

        df["_proceso"] = name
        sheets[name] = df

    return sheets

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🥩 Carnes Verona")
    st.markdown("**Estudio de Tiempos — Producción**")
    st.divider()

    uploaded = st.file_uploader("📂 Subir archivo Excel", type=["xlsx", "xls"])
    if uploaded:
        st.success(f"✅ {uploaded.name}")

    st.divider()
    st.markdown("**Filtros**")

PROCESS_NAMES = ["Mezcladora", "Molido", "Colgado", "Empaque"]

# ─── MAIN CONTENT ────────────────────────────────────────────────────────────────
st.markdown("# 📊 Dashboard de Producción")
st.markdown("Estudio de tiempos · Análisis de mudas · Carnes Verona")

if not uploaded:
    st.info("👈 Sube tu archivo Excel en el panel izquierdo para comenzar.")
    st.markdown("""
    **¿Qué verás aquí?**
    - ⏱️ Tiempo promedio, mínimo y máximo por proceso
    - 🔴 Identificación y clasificación de mudas (desperdicios)
    - 👷 Productividad por operario
    - 🌡️ Análisis de temperatura por proceso
    - 📋 Tabla detallada de registros
    """)
    st.stop()

# Cargar datos
raw_bytes = uploaded.read()
with st.spinner("Procesando datos..."):
    sheets = load_excel(raw_bytes)

# Procesos disponibles
available = [p for p in PROCESS_NAMES if p in sheets]

with st.sidebar:
    selected = st.multiselect(
        "Procesos a mostrar",
        options=available,
        default=available
    )
    st.divider()
    st.caption("Unidad de tiempo: **segundos**")

if not selected:
    st.warning("Selecciona al menos un proceso en el panel izquierdo.")
    st.stop()

# ─── KPI CARDS ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Resumen General</div>', unsafe_allow_html=True)

kpi_cols = st.columns(len(selected))
for i, proc in enumerate(selected):
    df = sheets[proc]
    avg = df["_segundos"].mean()
    total_mudas = (df["_muda"] != "Sin muda").sum()
    n = len(df)
    with kpi_cols[i]:
        color = PROCESS_COLORS[i % len(PROCESS_COLORS)]
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size:1.4rem; margin-bottom:4px">{['🔴','🔵','🟢','🟡'][i % 4]}</div>
            <div style="font-size:1rem; font-weight:600; color:{color}">{proc}</div>
            <div class="metric-value" style="color:{color}">{avg:.0f}s</div>
            <div class="metric-label">Tiempo promedio</div>
            <div style="margin-top:8px; font-size:0.8rem; color:#8892b0">
                {n} registros · {total_mudas} mudas detectadas
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─── TABS ────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(["⏱️ Tiempos", "🔴 Mudas", "👷 Operarios", "📋 Datos", "🤖 Resumen IA"])

# ── TAB 1: TIEMPOS ───────────────────────────────────────────────────────────────
with tab1:
    for i, proc in enumerate(selected):
        df = sheets[proc].dropna(subset=["_segundos"])
        color = PROCESS_COLORS[i % len(PROCESS_COLORS)]

        st.markdown(f'<div class="section-title">{proc} — Operario: {df["_operario"].iloc[0]}</div>', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("⏱️ Promedio", f"{df['_segundos'].mean():.0f} s")
        c2.metric("⬇️ Mínimo",   f"{df['_segundos'].min():.0f} s")
        c3.metric("⬆️ Máximo",   f"{df['_segundos'].max():.0f} s")
        c4.metric("📐 Desv. Std", f"{df['_segundos'].std():.0f} s")

        col_a, col_b = st.columns([2, 1])

        with col_a:
            labels = df["_actividad"].astype(str)
            fig = go.Figure()
            avg_val = df["_segundos"].mean()
            fig.add_trace(go.Bar(
                x=labels,
                y=df["_segundos"],
                marker_color=color,
                marker_line_color="rgba(0,0,0,0.3)",
                marker_line_width=1,
                name="Tiempo (s)",
                text=df["_segundos"].apply(lambda v: f"{v:.0f}s"),
                textposition="outside",
                textfont=dict(color=COLORS["text"], size=11)
            ))
            fig.add_hline(y=avg_val, line_dash="dot", line_color=COLORS["warning"],
                          annotation_text=f"Promedio: {avg_val:.0f}s",
                          annotation_font_color=COLORS["warning"])
            fig.update_layout(**PLOTLY_LAYOUT, title=f"Tiempos por actividad — {proc}",
                              xaxis_tickangle=-35, height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            # Box plot — más claro que histograma para reportes ejecutivos
            fig2 = go.Figure()
            fig2.add_trace(go.Box(
                y=df["_segundos"],
                name=proc,
                marker_color=color,
                line_color=color,
                boxmean=True,
                hovertemplate="<b>%{y}s</b><extra></extra>"
            ))
            fig2.add_hline(y=avg_val, line_dash="dot", line_color=COLORS["warning"],
                           annotation_text=f"Promedio: {avg_val:.0f}s",
                           annotation_font_color=COLORS["warning"])
            fig2.update_layout(
                **PLOTLY_LAYOUT,
                title="Dispersión de tiempos",
                yaxis_title="Segundos",
                height=350,
                showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Temperatura si existe
        temp_data = df["_temperatura"].dropna()
        if len(temp_data) > 0:
            with st.expander(f"🌡️ Temperaturas registradas — {proc}"):
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(
                    x=list(range(len(temp_data))),
                    y=temp_data.values,
                    mode="lines+markers",
                    marker=dict(color=COLORS["accent"], size=8),
                    line=dict(color=COLORS["accent"]),
                    name="Temperatura (°C)"
                ))
                fig3.add_hline(y=4, line_dash="dash", line_color=COLORS["warning"],
                               annotation_text="Límite recomendado 4°C",
                               annotation_font_color=COLORS["warning"])
                fig3.update_layout(**PLOTLY_LAYOUT, title=f"Control de temperatura — {proc}",
                                   yaxis_title="°C", height=280)
                st.plotly_chart(fig3, use_container_width=True)

        st.divider()

# ── TAB 2: MUDAS ─────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-title">Análisis de Mudas (Lean Manufacturing)</div>', unsafe_allow_html=True)

    all_mudas = []
    for proc in selected:
        df = sheets[proc]
        muda_df = df[df["_muda"] != "Sin muda"][["_muda", "_segundos", "_actividad", "_proceso"]].copy()
        all_mudas.append(muda_df)

    if all_mudas:
        combined = pd.concat(all_mudas, ignore_index=True)
        combined["_muda"] = combined["_muda"].str.strip()

        col1, col2 = st.columns(2)

        with col1:
            muda_counts = combined["_muda"].value_counts().reset_index()
            muda_counts.columns = ["Muda", "Frecuencia"]
            fig = px.bar(
                muda_counts, x="Muda", y="Frecuencia",
                color="Muda",
                color_discrete_sequence=PROCESS_COLORS,
                title="Frecuencia de mudas por tipo"
            )
            fig.update_layout(**PLOTLY_LAYOUT, height=340, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            muda_time = combined.groupby("_muda")["_segundos"].sum().reset_index()
            muda_time.columns = ["Muda", "Tiempo total (s)"]
            fig2 = px.pie(
                muda_time, values="Tiempo total (s)", names="Muda",
                color_discrete_sequence=PROCESS_COLORS,
                title="Tiempo perdido por tipo de muda"
            )
            fig2.update_layout(**PLOTLY_LAYOUT, height=340)
            st.plotly_chart(fig2, use_container_width=True)

        # Mudas por proceso
        st.markdown('<div class="section-title">Mudas por proceso</div>', unsafe_allow_html=True)
        muda_proc = combined.groupby(["_proceso", "_muda"]).size().reset_index(name="Conteo")
        fig3 = px.bar(
            muda_proc, x="_proceso", y="Conteo", color="_muda",
            barmode="group",
            color_discrete_sequence=PROCESS_COLORS,
            labels={"_proceso": "Proceso", "_muda": "Tipo de muda"},
            title="Distribución de mudas por proceso"
        )
        fig3.update_layout(**PLOTLY_LAYOUT, height=320)
        st.plotly_chart(fig3, use_container_width=True)

        # Detalle
        st.markdown('<div class="section-title">Registros con muda</div>', unsafe_allow_html=True)
        display = combined.rename(columns={
            "_muda": "Tipo Muda", "_segundos": "Tiempo (s)",
            "_actividad": "Actividad", "_proceso": "Proceso"
        })
        st.dataframe(display, use_container_width=True, hide_index=True)
    else:
        st.info("No se encontraron mudas registradas en los procesos seleccionados.")

# ── TAB 3: OPERARIOS ─────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-title">Productividad por Operario</div>', unsafe_allow_html=True)

    op_data = []
    for proc in selected:
        df = sheets[proc].dropna(subset=["_segundos"])
        op = df["_operario"].iloc[0]
        op_data.append({
            "Operario": op,
            "Proceso":  proc,
            "Promedio (s)": round(df["_segundos"].mean(), 1),
            "Total (s)":    round(df["_segundos"].sum(), 1),
            "Registros":    len(df),
            "Mudas":        int((df["_muda"] != "Sin muda").sum()),
        })

    op_df = pd.DataFrame(op_data)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            op_df, x="Operario", y="Promedio (s)", color="Proceso",
            color_discrete_sequence=PROCESS_COLORS,
            title="Tiempo promedio por operario",
            text="Promedio (s)"
        )
        fig.update_traces(texttemplate="%{text:.0f}s", textposition="outside")
        fig.update_layout(**PLOTLY_LAYOUT, height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.bar(
            op_df, x="Operario", y="Mudas", color="Proceso",
            color_discrete_sequence=PROCESS_COLORS,
            title="Mudas detectadas por operario"
        )
        fig2.update_layout(**PLOTLY_LAYOUT, height=350)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">Tabla resumen</div>', unsafe_allow_html=True)
    st.dataframe(op_df, use_container_width=True, hide_index=True)

# ── TAB 4: DATOS CRUDOS ──────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-title">Datos por proceso</div>', unsafe_allow_html=True)
    proc_sel = st.selectbox("Seleccionar proceso", options=selected)
    df_show = sheets[proc_sel].copy()
    # Quitar columnas internas _xxx para mostrar limpio
    display_cols = [c for c in df_show.columns if not c.startswith("_")]
    st.dataframe(df_show[display_cols], use_container_width=True, hide_index=True)

    # Descarga
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for proc in selected:
            df_exp = sheets[proc][[c for c in sheets[proc].columns if not c.startswith("_")]]
            df_exp.to_excel(writer, sheet_name=proc, index=False)
    st.download_button(
        label="⬇️ Descargar Excel limpio",
        data=buffer.getvalue(),
        file_name="Reporte_Carnes_Verona.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ── TAB 5: RESUMEN IA ────────────────────────────────────────────────────────────
with tab5:
    st.markdown('<div class="section-title">🤖 Resumen Ejecutivo generado por IA</div>', unsafe_allow_html=True)
    st.markdown("Genera un análisis automático de los datos de producción con recomendaciones para tu jefe.")

    def build_prompt(sheets, selected):
        resumen = []
        for proc in selected:
            df = sheets[proc].dropna(subset=["_segundos"])
            avg = df["_segundos"].mean()
            mn  = df["_segundos"].min()
            mx  = df["_segundos"].max()
            std = df["_segundos"].std()
            op  = df["_operario"].iloc[0]
            mudas = df[df["_muda"] != "Sin muda"]["_muda"].value_counts().to_dict()
            resumen.append(
                f"- {proc} (Operario: {op}): promedio={avg:.0f}s, min={mn:.0f}s, "
                f"max={mx:.0f}s, desv={std:.0f}s, registros={len(df)}, mudas={mudas}"
            )
        datos = "\n".join(resumen)
        return f"""Eres un experto en ingeniería industrial y estudio de tiempos.
Analiza los siguientes datos de producción de una planta de embutidos llamada Carnes Verona, ubicada en Colombia.

DATOS DE PRODUCCIÓN:
{datos}

Genera un informe ejecutivo en español con:
1. **Resumen general** de la situación productiva (2-3 oraciones)
2. **Hallazgos por proceso** — identifica cuál proceso tiene mayor variabilidad y por qué es crítico
3. **Análisis de mudas** — qué desperdicios Lean se detectaron y su impacto
4. **Top 3 recomendaciones** concretas y accionables para mejorar la productividad
5. **Conclusión** de una sola oración para el jefe

Sé directo, profesional y usa lenguaje ejecutivo. Máximo 400 palabras."""

    def llamar_gemini(prompt):
        import urllib.request, json
        api_key = st.secrets["GEMINI_API_KEY"]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}]
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["candidates"][0]["content"]["parts"][0]["text"]

    if st.button("🚀 Generar Resumen Ejecutivo con IA", type="primary"):
        with st.spinner("Analizando datos con IA..."):
            try:
                prompt = build_prompt(sheets, selected)
                resumen_ia = llamar_gemini(prompt)
                st.markdown("""
                <div style='background:linear-gradient(135deg,#1e2130,#252840);
                            border:1px solid #2e3250; border-radius:12px;
                            padding:28px; margin-top:16px;'>
                """, unsafe_allow_html=True)
                st.markdown(resumen_ia)
                st.markdown("</div>", unsafe_allow_html=True)
                st.download_button(
                    label="⬇️ Descargar resumen como .txt",
                    data=resumen_ia,
                    file_name="Resumen_Ejecutivo_Carnes_Verona.txt",
                    mime="text/plain"
                )
            except Exception as e:
                st.error(f"Error al conectar con Gemini: {e}")
                st.info("Verifica que la API key esté bien guardada en Streamlit Secrets.")

# ─── FOOTER ──────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center; color:#8892b0; font-size:0.8rem;'>"
    "Carnes Verona · Estudio de Tiempos · Dashboard generado automáticamente"
    "</div>",
    unsafe_allow_html=True
)

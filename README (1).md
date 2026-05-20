# 🥩 Carnes Verona — Dashboard de Estudio de Tiempos

Dashboard profesional para análisis de tiempos de producción y mudas (Lean Manufacturing).

## Procesos analizados
- 🔴 Mezcladora (Frank)
- 🔵 Molido (William)
- 🟢 Colgado (Paola)
- 🟡 Empaque (Diana)

## Requisitos
- Python 3.9+
- pip

## Instalación local

```bash
# 1. Clonar o descargar este repositorio
git clone https://github.com/TU_USUARIO/carnes-verona.git
cd carnes-verona

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Correr la app
streamlit run app.py
```

La app abrirá automáticamente en `http://localhost:8501`

## Deploy en Streamlit Cloud (gratis)

1. Sube este repositorio a GitHub
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu repo y selecciona `app.py` como archivo principal
4. ¡Listo! Obtienes una URL pública para compartir con tu jefe

## Uso

1. Abre la app
2. Haz clic en **"Subir archivo Excel"** en el panel izquierdo
3. Sube tu `.xlsx` con las 4 hojas: Mezcladora, Molido, Colgado, Empaque
4. Explora los 4 tabs:
   - **⏱️ Tiempos** — promedios, histogramas, control de temperatura
   - **🔴 Mudas** — análisis Lean de desperdicios
   - **👷 Operarios** — productividad comparada
   - **📋 Datos** — tabla raw + descarga Excel

## Estructura del Excel esperada

Cada hoja debe tener una columna `Tiempo(s)` con los tiempos en **segundos**.
Columnas opcionales: `Temperatura`, `Muda`, `Operario`, `Observacion`, `Unidades`.

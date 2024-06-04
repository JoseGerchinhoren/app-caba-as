import streamlit as st
from datetime import datetime, timezone, timedelta

def obtener_fecha_argentina():
    # Configurar la zona horaria a Argentina
    tz_argentina = timezone(timedelta(hours=-3))  # Argentina UTC-3
    fecha_actual_argentina = datetime.now(tz_argentina)
    return fecha_actual_argentina

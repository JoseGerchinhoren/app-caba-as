import streamlit as st
import pandas as pd
import boto3
import io
from io import StringIO
from streamlit.components.v1 import html

# Obtener credenciales
from config import cargar_configuracion

# Obtener fecha actual en Argentina
from horario import obtener_fecha_argentina

# Conectar a S3
def conectar_s3():
    aws_access_key, aws_secret_key, region_name, bucket_name = cargar_configuracion()
    return boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=region_name), bucket_name

def cargar_dataframe_desde_s3(s3, bucket_name):
    csv_filename = "reservasCabana.csv"
    try:
        response = s3.get_object(Bucket=bucket_name, Key=csv_filename)
        return pd.read_csv(io.BytesIO(response['Body'].read()))
    except s3.exceptions.NoSuchKey:
        st.warning("No se encontró el archivo CSV en S3.")
        return pd.DataFrame(columns=['idReserva', 'cabaña', 'fechaIngreso', 'fechaEgreso', 'estado', 'pago', 'nombreCliente', 'contacto', 'edadCliente', 'cantidadPersonas', 'origenReserva', 'fechaReserva'])

def upload_to_s3(data, s3, bucket_name):
    csv_filename = "reservasCabana.csv"
    csv_buffer = StringIO()
    data.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    s3.put_object(Bucket=bucket_name, Key=csv_filename, Body=csv_buffer.getvalue())

def generate_id(reservas):
    return max(reservas['idReserva'].max() + 1, 1) if not reservas.empty else 1

def add_reserva(reservas, cabaña, fechaIngreso, fechaEgreso, estado, pago, nombreCliente, contacto, edadCliente, cantidadPersonas, origenReserva):
    idReserva = generate_id(reservas)
    fecha_reserva = obtener_fecha_argentina().date()  # Obtener la fecha de la reserva
    nueva_reserva = pd.DataFrame({
        'idReserva': [idReserva],
        'cabaña': [cabaña],
        'fechaIngreso': [fechaIngreso],
        'fechaEgreso': [fechaEgreso],
        'estado': [estado],
        'pago': [pago],
        'nombreCliente': [nombreCliente],
        'contacto': [contacto],
        'edadCliente': [edadCliente],
        'cantidadPersonas': [cantidadPersonas],
        'origenReserva': [origenReserva],
        'fechaReserva': [fecha_reserva]
    })
    return pd.concat([reservas, nueva_reserva], ignore_index=True)

def mostrar_calendario(reservas):
    events = []
    for _, row in reservas.iterrows():
        event = {
            'title': f"{row['nombreCliente']} (Cabaña {row['cabaña']})",
            'start': row['fechaIngreso'],
            'end': row['fechaEgreso']
        }
        events.append(event)
    
    events_js = str(events).replace("'", '"')

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link href='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.0/main.min.css' rel='stylesheet' />
        <script src='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.0/main.min.js'></script>
        <style>
            body {{
                color: white;
            }}
            .fc-event {{
                color: white !important;
                background-color: #007bff !important;
                border: none !important;
            }}
        </style>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                var calendarEl = document.getElementById('calendar');
                var calendar = new FullCalendar.Calendar(calendarEl, {{
                    initialView: 'dayGridMonth',
                    events: {events_js}
                }});
                calendar.render();
            }});
        </script>
    </head>
    <body>
        <div id='calendar'></div>
    </body>
    </html>
    """
    
    st.components.v1.html(html_code, height=600)

def main():
    # Conectar a S3 y cargar datos
    s3, bucket_name = conectar_s3()
    reservas = cargar_dataframe_desde_s3(s3, bucket_name)
    
    # Interfaz de usuario
    st.title("Gestión de Reservas de Cabañas")
    
    # Sección para ingresar nueva reserva
    with st.expander("Ingresar Nueva Reserva"):
        cabaña = st.selectbox("Cabaña", [1, 2])
        fechaIngreso = st.date_input("Fecha de Ingreso")
        fechaEgreso = st.date_input("Fecha de Egreso")
        nombreCliente = st.text_input("Nombre del Cliente")
        contacto = st.text_input("Contacto")
        edadCliente = st.number_input("Edad del Cliente", min_value=0, max_value=120, step=1)
        cantidadPersonas = st.number_input("Cantidad de Personas", min_value=1, step=1)
        origenReserva = st.text_input("Origen de la Reserva", placeholder="Ej: Booking, Facebook, etc.")
        estado = st.selectbox("Estado", ["Sin seña", "Señado", "Cancelado", "Pagado"])
        pago = 0
        if estado in ["Señado", "Pagado"]:
            pago = st.number_input("Monto del Pago", min_value=0, step=1)
        
        submit = st.button("Guardar Reserva")
        
        if submit:
            reservas = add_reserva(reservas, cabaña, fechaIngreso, fechaEgreso, estado, pago, nombreCliente, contacto, edadCliente, cantidadPersonas, origenReserva)
            upload_to_s3(reservas, s3, bucket_name)
            st.success("Reserva guardada con éxito")
    
    # Sección para visualizar reservas
    with st.expander("Ver Reservas"):
        filtro_cabaña = st.selectbox("Filtrar por Cabaña", [1, 2, "Todas"], index=2)
        
        if filtro_cabaña != "Todas":
            reservas_filtradas = reservas[reservas['cabaña'] == int(filtro_cabaña)]
        else:
            reservas_filtradas = reservas
        
        reservas_filtradas = reservas_filtradas.sort_values(by='idReserva', ascending=False)
        
        st.write(reservas_filtradas)

        # Mostrar calendario con reservas
        st.subheader("Calendario de Reservas")
        mostrar_calendario(reservas_filtradas)

if __name__ == '__main__':
    main()

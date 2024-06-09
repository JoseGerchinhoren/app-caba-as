import streamlit as st
import pandas as pd
import boto3
import io
from io import StringIO
from datetime import datetime

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
            'title': f"{row['nombreCliente']} (C{row['cabaña']})",
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

def editar_reserva(reservas, idReserva, cabaña, fechaIngreso, fechaEgreso, estado, pago, nombreCliente, contacto, edadCliente, cantidadPersonas, origenReserva):
    reservas.loc[reservas['idReserva'] == idReserva, ['cabaña', 'fechaIngreso', 'fechaEgreso', 'estado', 'pago', 'nombreCliente', 'contacto', 'edadCliente', 'cantidadPersonas', 'origenReserva']] = [cabaña, fechaIngreso, fechaEgreso, estado, pago, nombreCliente, contacto, edadCliente, cantidadPersonas, origenReserva]
    return reservas

def main():
    # Conectar a S3 y cargar datos
    s3, bucket_name = conectar_s3()
    reservas = cargar_dataframe_desde_s3(s3, bucket_name)
    
    # Interfaz de usuario
    st.header("Gestión de Reservas de Cabañas")
    
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

    # Sección para editar reserva
    with st.expander("Edita Reserva"):
        id_reserva_editar = st.number_input("ID de la Reserva a Editar", min_value=None, step=1)
        reserva_editar = reservas[reservas['idReserva'] == id_reserva_editar]
        if not reserva_editar.empty:
            cabañas_disponibles = [str(x) for x in [1, 2]]
            cabaña_editar = st.selectbox("Cabaña", cabañas_disponibles, index=cabañas_disponibles.index(str(reserva_editar['cabaña'].iloc[0])), key=f"cabaña_{id_reserva_editar}")
            # Obtener el valor de fecha en formato datetime
            fecha_ingreso_valor = datetime.strptime(reserva_editar['fechaIngreso'].iloc[0], '%Y-%m-%d').date()
            # Utilizar el valor convertido en el date_input
            fechaIngreso_editar = st.date_input("Fecha de Ingreso", value=fecha_ingreso_valor) 
            fecha_egreso_valor = datetime.strptime(reserva_editar['fechaEgreso'].iloc[0], '%Y-%m-%d').date()
            fechaEgreso_editar = st.date_input("Fecha de Egreso", value=fecha_egreso_valor)
            nombreCliente_editar = st.text_input("Nombre del Cliente", value=reserva_editar['nombreCliente'].iloc[0])
            contacto_editar = st.text_input("Contacto", value=reserva_editar['contacto'].iloc[0])
            edadCliente_editar = st.number_input("Edad del Cliente", min_value=0, max_value=120, step=1, value=reserva_editar['edadCliente'].iloc[0])
            cantidadPersonas_editar = st.number_input("Cantidad de Personas", min_value=1, step=1, value=reserva_editar['cantidadPersonas'].iloc[0])
            origenReserva_editar = st.text_input("Origen de la Reserva", placeholder="Ej: Booking, Facebook, etc.", value=reserva_editar['origenReserva'].iloc[0])
            estado_editar = st.selectbox("Estado", ["Sin seña", "Señado", "Cancelado", "Pagado"], index=["Sin seña", "Señado", "Cancelado", "Pagado"].index(reserva_editar['estado'].iloc[0]), key=f"estado_{id_reserva_editar}")
            pago_editar = 0
            if estado_editar in ["Señado", "Pagado"]:
                pago_editar = st.number_input("Monto del Pago", min_value=0, step=1, value=reserva_editar['pago'].iloc[0])

            submit_editar = st.button("Guardar Cambios")

            if submit_editar:
                reservas = editar_reserva(reservas, id_reserva_editar, cabaña_editar, fechaIngreso_editar, fechaEgreso_editar, estado_editar, pago_editar, nombreCliente_editar, contacto_editar, edadCliente_editar, cantidadPersonas_editar, origenReserva_editar)
                upload_to_s3(reservas, s3, bucket_name)
                st.success("Reserva editada con éxito")
        else:
            st.warning("No se encontró una reserva con ese ID")

if __name__ == '__main__':
    main()

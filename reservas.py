import streamlit as st
import pandas as pd
import boto3
import io
from io import StringIO

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
        return pd.DataFrame(columns=['idReserva', 'cabaña', 'fechaIngreso', 'fechaEgreso', 'nombreCliente', 'edadCliente'])

def upload_to_s3(data, s3, bucket_name):
    csv_filename = "reservasCabana.csv"
    csv_buffer = StringIO()
    data.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    s3.put_object(Bucket=bucket_name, Key=csv_filename, Body=csv_buffer.getvalue())

# Conectar a S3 y cargar datos
s3, bucket_name = conectar_s3()
reservas = cargar_dataframe_desde_s3(s3, bucket_name)

# Generar ID de reserva único
def generate_id():
    return max(reservas['idReserva'].max() + 1, 1) if not reservas.empty else 1

# Función para agregar una nueva reserva
def add_reserva(cabaña, fechaIngreso, fechaEgreso, nombreCliente, edadCliente):
    idReserva = generate_id()
    nueva_reserva = pd.DataFrame({
        'idReserva': [idReserva],
        'cabaña': [cabaña],
        'fechaIngreso': [fechaIngreso],
        'fechaEgreso': [fechaEgreso],
        'nombreCliente': [nombreCliente],
        'edadCliente': [edadCliente]
    })
    return reservas.append(nueva_reserva, ignore_index=True)

# Interfaz de usuario
st.title("Gestión de Reservas de Cabañas")

# Sección para ingresar nueva reserva
with st.expander("Ingresar Nueva Reserva"):
    with st.form("form_reserva"):
        cabaña = st.selectbox("Cabaña", [1, 2])
        fechaIngreso = st.date_input("Fecha de Ingreso")
        fechaEgreso = st.date_input("Fecha de Egreso")
        nombreCliente = st.text_input("Nombre del Cliente")
        edadCliente = st.number_input("Edad del Cliente", min_value=0, max_value=120, step=1)
        
        submit = st.form_submit_button("Guardar Reserva")
        
        if submit:
            reservas = add_reserva(cabaña, fechaIngreso, fechaEgreso, nombreCliente, edadCliente)
            upload_to_s3(reservas, s3, bucket_name)
            st.success("Reserva guardada con éxito")

# Sección para visualizar reservas
with st.expander("Ver Reservas"):
    filtro_cabaña = st.selectbox("Filtrar por Cabaña", [1, 2, "Todas"], index=2)
    
    if filtro_cabaña != "Todas":
        reservas_filtradas = reservas[reservas['cabaña'] == int(filtro_cabaña)]
    else:
        reservas_filtradas = reservas
    
    st.write(reservas_filtradas)

    # Mostrar calendario con reservas
    st.subheader("Calendario de Reservas")
    events = []
    for _, row in reservas_filtradas.iterrows():
        events.append({
            'start': row['fechaIngreso'],
            'end': row['fechaEgreso'],
            'title': f"{row['nombreCliente']} (Cabaña {row['cabaña']})"
        })
    
#     calendar(events)

# def main():
    
#     registra_entrenamientos_hipertrofia()

# if __name__ == '__main__':
#     main()

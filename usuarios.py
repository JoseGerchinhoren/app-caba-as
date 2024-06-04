import streamlit as st
import boto3
import pandas as pd
import io
from datetime import datetime
from config import cargar_configuracion

# Obtener credenciales
aws_access_key, aws_secret_key, region_name, bucket_name = cargar_configuracion()

# Conecta a S3
s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=region_name)

# Función para insertar un nuevo usuario en la base de datos
def insertar_usuario(nombre_apellido, contraseña, confirmar_contraseña, fecha_creacion, rol):
    try:
        # Verificar si las contraseñas coinciden
        if contraseña != confirmar_contraseña:
            st.warning("Las contraseñas no coinciden. Por favor, inténtelo de nuevo.")
            return

        # Leer el archivo CSV desde S3
        csv_file_key = 'usuarios_combustible.csv'
        response = s3.get_object(Bucket=bucket_name, Key=csv_file_key)
        usuarios_df = pd.read_csv(io.BytesIO(response['Body'].read()))

        # Obtener el último idUsuario
        ultimo_id = usuarios_df['idUsuario'].max()

        # Si no hay registros, asignar 0 como idUsuario, de lo contrario, incrementar el último idUsuario
        nuevo_id = 0 if pd.isna(ultimo_id) else int(ultimo_id) + 1

        # Crear una nueva fila como un diccionario
        nueva_fila = {'idUsuario': nuevo_id, 'nombreApellido': nombre_apellido,
                      'contraseña': contraseña, 'fechaCreacion': fecha_creacion, 'rol': rol}

        # Convertir el diccionario a DataFrame y concatenarlo al DataFrame existente
        usuarios_df = pd.concat([usuarios_df, pd.DataFrame([nueva_fila])], ignore_index=True)

        # Guardar el DataFrame actualizado de nuevo en S3
        with io.StringIO() as csv_buffer:
            usuarios_df.to_csv(csv_buffer, index=False)
            s3.put_object(Body=csv_buffer.getvalue(), Bucket=bucket_name, Key=csv_file_key)

        st.success("Usuario registrado exitosamente")

    except Exception as e:
        st.error(f"Error al registrar el usuario: {e}")

def ingresa_usuario():
    # st.title("""Crear Usuario \n * Ingrese los datos del usuario, incluyendo nombre y apellido, email, contraseña, verificacion de contraseña, fecha de nacimiento, DNI, domicilio y rol (empleado o admin). \n * Presione 'Registrar Usuario' para guardar la información.""")

    st.title('Ingresar Usuario')

    # Campos para ingresar los datos del nuevo usuario
    nombre_apellido = st.text_input("Nombre y Apellido:")
    contraseña = st.text_input("Contraseña:", type="password")
    confirmar_contraseña = st.text_input("Confirmar Contraseña:", type="password")
    
    # El campo 'fecha_creacion' se asigna automáticamente a la fecha actual
    fecha_creacion = datetime.now().strftime("%Y-%m-%d")
    
    rol = st.selectbox("Rol:", ["empleado", "inspector","admin"])

    # Botón para registrar el nuevo usuario
    if st.button("Registrar Usuario"):
        if nombre_apellido and contraseña and confirmar_contraseña and rol:
            insertar_usuario(nombre_apellido, contraseña, confirmar_contraseña, fecha_creacion, rol)
        else:
            st.warning("Por favor, complete todos los campos.")

if __name__ == "__main__":
    ingresa_usuario()
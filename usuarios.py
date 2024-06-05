import streamlit as st
import boto3
import pandas as pd
import io
from datetime import datetime
import time
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
        csv_file_key = 'usuarios.csv'
        response = s3.get_object(Bucket=bucket_name, Key=csv_file_key)
        usuarios_df = pd.read_csv(io.BytesIO(response['Body'].read()))

        # Obtener el último idUsuario
        ultimo_id = usuarios_df['idUsuario'].max()

        # Si no hay registros, asignar 0 como idUsuario, de lo contrario, incrementar el último idUsuario
        nuevo_id = 0 if pd.isna(ultimo_id) else int(ultimo_id) + 1

        # Crear una nueva fila como un diccionario
        nueva_fila = {'idUsuario': nuevo_id, 'nombreApellido': nombre_apellido,
                      'contraseña': contraseña, 'rol': rol}

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
    st.title('Ingresar Usuario')

    # Campos para ingresar los datos del nuevo usuario
    nombre_apellido = st.text_input("Nombre y Apellido:")
    contraseña = st.text_input("Contraseña:", type="password")
    confirmar_contraseña = st.text_input("Confirmar Contraseña:", type="password")
        
    rol = st.selectbox("Rol:", ["empleado", "inspector","admin"])

    # Botón para registrar el nuevo usuario
    if st.button("Registrar Usuario"):
        if nombre_apellido and contraseña and confirmar_contraseña and rol:
            insertar_usuario(nombre_apellido, contraseña, confirmar_contraseña, rol)
        else:
            st.warning("Por favor, complete todos los campos.")



def visualizar_usuarios():
    st.title("Visualiza Usuarios")

    # Cargar el archivo usuarios.csv desde S3
    s3_csv_key = 'usuarios.csv'
    csv_obj = s3.get_object(Bucket=bucket_name, Key=s3_csv_key)
    usuarios_df = pd.read_csv(io.BytesIO(csv_obj['Body'].read()), dtype={'idUsuario': int}).applymap(lambda x: str(x).replace(',', '') if pd.notna(x) else x)

    # Cambiar los nombres de las columnas si es necesario
    usuarios_df.columns = ["idUsuario", "Nombre y Apellido", "contraseña", "Rol"]

    # Cambiar el orden de las columnas según el nuevo orden deseado
    usuarios_df = usuarios_df[["idUsuario", "Nombre y Apellido", "Rol"]]

    # Convertir la columna "idUsuario" a tipo int
    usuarios_df['idUsuario'] = usuarios_df['idUsuario'].astype(int)

    # Ordenar el DataFrame por 'idVenta' en orden descendente
    usuarios_df = usuarios_df.sort_values(by='idUsuario', ascending=False)

    # Convertir la columna "idUsuario" a tipo cadena y eliminar las comas
    usuarios_df['idUsuario'] = usuarios_df['idUsuario'].astype(str).str.replace(',', '')

    # Mostrar la tabla de usuarios
    st.dataframe(usuarios_df)

def editar_usuario():
    st.header("Editar Usuario")

    # Campo para ingresar el idUsuario del usuario que se desea editar
    id_usuario_editar = st.text_input("Ingrese el idUsuario del usuario que desea editar:")

    if id_usuario_editar is not None:
        # Descargar el archivo CSV desde S3 y cargarlo en un DataFrame
        csv_file_key = 'usuarios.csv'
        try:
            response = s3.get_object(Bucket=bucket_name, Key=csv_file_key)
            usuarios_df = pd.read_csv(io.BytesIO(response['Body'].read()), dtype={'idUsuario': str}).applymap(lambda x: str(x).replace(',', '') if pd.notna(x) else x)
        except s3.exceptions.NoSuchKey:
            st.warning("No se encontró el archivo CSV en S3.")
            return

        # Filtrar el DataFrame para obtener el arreglo específico por idUsuario
        usuario_editar_df = usuarios_df[usuarios_df['idUsuario'] == id_usuario_editar]

        # Verificar si se encontró un usuario con el idUsuario proporcionado
        if not usuario_editar_df.empty:
            # Mostrar la información actual del usuario
            st.write("Información actual del usuario:")
            st.dataframe(usuario_editar_df)

            # Mostrar campos para editar cada variable
            for column in usuario_editar_df.columns:
                if column not in ['idUsuario', 'contraseña']:  # Evitar editar estos campos
                    if column == 'rol':
                        nuevo_valor = st.selectbox("Rol", ["empleado", "inspector", "admin"], index=["empleado", "inspector", "admin"].index(usuario_editar_df.iloc[0][column]))
                    else:
                        nuevo_valor = st.text_input(f"Nuevo valor para {column}", value=usuario_editar_df.iloc[0][column])

                    # Verificar si el campo es numérico o de fecha/hora
                    if column == 'idEmpleado':
                        if not nuevo_valor.isdigit():
                            st.warning(f"ID del empleado debe ser un valor numérico.")
                            return
                    elif column == 'rol' and nuevo_valor not in ['empleado', 'inspector', 'admin']:
                        st.warning("Rol debe ser 'empleado', 'inspector' o 'admin'.")
                        return

                    usuario_editar_df.at[usuario_editar_df.index[0], column] = nuevo_valor

            # Botón para guardar los cambios
            if st.button("Guardar cambios", key="guardar_cambios_btn"):
                # Actualizar el DataFrame original con los cambios realizados
                usuarios_df.update(usuario_editar_df)

                # Guardar el DataFrame actualizado en S3
                with io.StringIO() as csv_buffer:
                    usuarios_df.to_csv(csv_buffer, index=False)
                    s3.put_object(Body=csv_buffer.getvalue(), Bucket=bucket_name, Key=csv_file_key)

                st.success("¡Usuario actualizado correctamente!")

        else:
            st.warning(f"No se encontró ningún usuario con el idUsuario {id_usuario_editar}")

    else:
        st.warning("Ingrese el idUsuario del usuario que desea editar.")

def eliminar_usuario():
    st.header('Eliminar Usuario')

    # Ingresar el idUsuario del usuario a eliminar
    id_usuario_eliminar = st.number_input('Ingrese el idUsuario del usuario a eliminar', value=None, min_value=0)

    if id_usuario_eliminar is not None:
        st.error(f'¿Está seguro de eliminar al usuario con idUsuario {id_usuario_eliminar}?')

        if st.button('Eliminar Usuario'):
            # Descargar el archivo CSV desde S3 y cargarlo en un DataFrame
            response = s3.get_object(Bucket=bucket_name, Key='usuarios.csv')
            usuarios_df = pd.read_csv(io.BytesIO(response['Body'].read()))

            # Verificar si el usuario con el idUsuario a eliminar existe en el DataFrame
            if id_usuario_eliminar in usuarios_df['idUsuario'].values:
                # Eliminar al usuario con el idUsuario especificado
                usuarios_df = usuarios_df[usuarios_df['idUsuario'] != id_usuario_eliminar]

                # Guardar el DataFrame actualizado en S3
                with io.StringIO() as csv_buffer:
                    usuarios_df.to_csv(csv_buffer, index=False)
                    s3.put_object(Body=csv_buffer.getvalue(), Bucket=bucket_name, Key='usuarios.csv')

                st.success(f"¡Usuario con idUsuario {id_usuario_eliminar} eliminado correctamente!")

                # Esperar 2 segundos antes de recargar la aplicación
                time.sleep(2)
                
                # Recargar la aplicación
                st.rerun()
            else:
                st.error(f"No se encontró ningún usuario con el idUsuario {id_usuario_eliminar}")
    else:
        st.error('Ingrese el idUsuario del usuario para eliminarlo')

def main():
    # Interfaz de usuario
    with st.expander('Ingresa Usuario'):
        ingresa_usuario()
    with st.expander('Visualiza Usuarios'):
        visualizar_usuarios()
        editar_usuario()
        eliminar_usuario()

if __name__ == "__main__":
    main()

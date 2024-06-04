import streamlit as st
import boto3
import pandas as pd
import io
from config import cargar_configuracion
import time

# Obtener credenciales
aws_access_key, aws_secret_key, region_name, bucket_name = cargar_configuracion()

# Conecta a S3
s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=region_name)

def visualizar_usuarios():
    st.title("Visualiza Usuarios")

    # Cargar el archivo usuarios.csv desde S3
    s3_csv_key = 'usuarios_combustible.csv'
    csv_obj = s3.get_object(Bucket=bucket_name, Key=s3_csv_key)
    usuarios_df = pd.read_csv(io.BytesIO(csv_obj['Body'].read()), dtype={'idUsuario': int}).applymap(lambda x: str(x).replace(',', '') if pd.notna(x) else x)

    # Cambiar los nombres de las columnas si es necesario
    usuarios_df.columns = ["idUsuario", "Nombre y Apellido", "contraseña", "Fecha de Creacion", "Rol"]

    # Cambiar el orden de las columnas según el nuevo orden deseado
    usuarios_df = usuarios_df[["idUsuario", "Nombre y Apellido", "Fecha de Creacion", "Rol"]]

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
        csv_file_key = 'usuarios_combustible.csv'
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
                if column not in ['idUsuario', 'fechaCreacion', 'contraseña']:  # Evitar editar estos campos
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
            response = s3.get_object(Bucket=bucket_name, Key='usuarios_combustible.csv')
            usuarios_df = pd.read_csv(io.BytesIO(response['Body'].read()))

            # Verificar si el usuario con el idUsuario a eliminar existe en el DataFrame
            if id_usuario_eliminar in usuarios_df['idUsuario'].values:
                # Eliminar al usuario con el idUsuario especificado
                usuarios_df = usuarios_df[usuarios_df['idUsuario'] != id_usuario_eliminar]

                # Guardar el DataFrame actualizado en S3
                with io.StringIO() as csv_buffer:
                    usuarios_df.to_csv(csv_buffer, index=False)
                    s3.put_object(Body=csv_buffer.getvalue(), Bucket=bucket_name, Key='usuarios_combustible.csv')

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
    visualizar_usuarios()
    editar_usuario()
    eliminar_usuario()

if __name__ == "__main__":
    main()

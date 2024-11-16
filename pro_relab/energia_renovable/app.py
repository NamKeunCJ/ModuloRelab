import psycopg2
import hashlib
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import date, datetime, timedelta
import threading
import time
import requests # elementos para datos davis
import xml.etree.ElementTree as ET # elementos para datos davis
import pandas as pd #Extrer los datos del archivo plano
###############################################################################
#LIBRERIAS PARA EL MODELO DE PREDICCION
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
###############################################################################

# Crear una instancia de la aplicación Flask
app = Flask(__name__)

# Configurar la clave secreta de la aplicación, utilizada para gestionar sesiones y cookies seguras
app.config['SECRET_KEY'] = 'unicesmag'

# Configurar los parámetros de la base de datos
app.config['DB_HOST'] = 'localhost'  # El host donde se encuentra la base de datos
app.config['DB_NAME'] = 'modulo_relab'  # El nombre de la base de datos
app.config['DB_USER'] = 'postgres'  # El usuario de la base de datos
app.config['DB_PASSWORD'] = 'unicesmag'  # La contraseña del usuario de la base de datos

# Definir una función para obtener la conexión a la base de datos
def get_db_connection():
    # Establecer una conexión a la base de datos utilizando los parámetros configurados en la aplicación
    conn = psycopg2.connect(
        host=app.config['DB_HOST'],
        database=app.config['DB_NAME'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD']
    )
    return conn  # Devolver la conexión a la base de datos

# Ruta para la página de inicio de sesión
@app.route('/')
@app.route('/inicio_sesion')
def inicio_sesion():
    # Obtener el ID de usuario de la sesión actual
    user_id = session.get('user_id')    
    # Verificar si el usuario ha iniciado sesión
    if user_id is not None:
        # Si el usuario ha iniciado sesión, redirigir a la página principal
        return redirect(url_for('inicio_principal'))    
    # Si el usuario no ha iniciado sesión, renderizar la página de inicio de sesión
    return render_template('autenticacion_y_registro/index.html')

# Ruta para manejar el inicio de sesión
@app.route('/login', methods=['POST'])
def login():
    print("Entro Login")    
    # Verificar si el método de la solicitud es POST
    if request.method == 'POST': 
        mail = request.form['cor_usu']  # Obtener el correo del usuario desde el formulario
        password = request.form['con_usu']  # Obtener la contraseña del usuario desde el formulario        
        # Encriptar la contraseña ingresada a MD5
        password_md5 = hashlib.md5(password.encode()).hexdigest()        
        # Buscar el usuario y la contraseña en la base de datos por su correo y contraseña
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT id_usu, per_usu FROM usuario WHERE cor_usu=%s AND con_usu=%s;', (mail, password_md5))
                user = cur.fetchone()  # Obtener el primer resultado de la consulta        
        # Verificar si se encontró un usuario con las credenciales proporcionadas
        if user is not None:
            session['user_id'] = user[0]  # Guardar el ID del usuario en la sesión
            session['user_rol'] = user[1]  # Guardar el rol del usuario en la sesión
            return 'success'  # Devolver 'success' si el inicio de sesión es exitoso
        else:
            return 'error'  # Devolver 'error' si las credenciales son incorrectas

# Ruta para manejar el registro de una nueva cuenta (POST)
@app.route('/registro', methods=['GET', 'POST'])
def registro():    
    print("Entro Registrar")    
    if request.method == 'POST':        
        # Obtener los datos del formulario
        nombres = request.form['nom_usu']
        apellidos = request.form['ape_usu']
        correo = request.form['cor_usu']
        numero_documento = request.form['doc_usu']
        contra = request.form['con_usu']        
        # Codificar la contraseña en formato MD5
        password_md5 = hashlib.md5(contra.encode()).hexdigest()        
        # Buscar el usuario en la base de datos por su correo electrónico o número de documento
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT cor_usu, doc_usu FROM usuario WHERE cor_usu=%s OR doc_usu=%s;', (correo, numero_documento))
                user_exis = cur.fetchone()
                print(user_exis)                
                if user_exis is not None:
                    # Si el usuario ya existe, devolver 'exist'
                    print("El usuario ya existe en la base de datos")
                    return 'exist' 
                else:                     
                    # Si el usuario no existe, insertar el nuevo usuario en la base de datos
                    cur.execute("""
                        INSERT INTO usuario (nom_usu, ape_usu, cor_usu, doc_usu, con_usu)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (nombres, apellidos, correo, numero_documento, password_md5))
                    conn.commit()
                    print("Nuevo usuario agregado correctamente")
                    return 'success' 
    # Si el método no es POST, renderizar el formulario de registro
    return render_template('autenticacion_y_registro/registro.html')


# Página principal
@app.route('/inicio_principal')
def inicio_principal():
    user_id = session.get('user_id')    
    if user_id is None:
        # Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('inicio_sesion'))    
    # Obtener más información del usuario a partir de su ID
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Ejecutar una consulta SQL para obtener el ID del usuario
            cur.execute(f'SELECT id_usu FROM usuario WHERE id_usu={user_id};')
            user = cur.fetchone()    
    # Renderizar la plantilla HTML de la página principal y pasar los datos del usuario
    return render_template('autenticacion_y_registro/pagina principal.html', user=user)

#Cerrar Sesion        
@app.route('/logout')
def logout():
    # Borrar la información de la sesión
    session.clear()
    # Redireccionar a la página de inicio o a donde prefieras
    return redirect(url_for('inicio_sesion'))  

# Ruta para editar el perfil del usuario
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile(): 
    if request.method == 'POST':
        print("entro")        
        # Obtener el ID del usuario de la sesión
        id_usu = session.get('user_id')        
        # Obtener los datos del formulario
        cor_usu = request.form['cor_usu']
        password = request.form['con_usu']         
        # Conectar a la base de datos
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verificar si ya existe otro usuario con el mismo correo electrónico
                cur.execute("""
                    SELECT cor_usu FROM usuario WHERE cor_usu = %s AND id_usu != %s
                """, (cor_usu, id_usu))
                user_exis = cur.fetchone()                
                if user_exis is None:
                    # Obtener la información actual del usuario
                    cur.execute(f"""SELECT cor_usu, con_usu FROM usuario WHERE id_usu={id_usu};""")
                    user_data = cur.fetchone()                    
                    # Actualizar el correo electrónico del usuario
                    cur.execute('''
                        UPDATE usuario SET cor_usu = %s WHERE id_usu = %s
                    ''', (cor_usu, id_usu))                    
                    # Actualizar la contraseña si no es el valor por defecto
                    if password != "***************":
                        # Codificar la nueva contraseña en MD5
                        password_md5 = hashlib.md5(password.encode()).hexdigest()
                        cur.execute('''
                            UPDATE usuario SET con_usu = %s WHERE id_usu = %s
                        ''', (password_md5, id_usu))                    
                    # Redirigir con un mensaje de éxito
                    success = '1'
                    return redirect(url_for('edit_profile', success=success))
                else:
                    # Redirigir con un mensaje de error si el correo ya está en uso
                    error = '2'
                    return redirect(url_for('edit_profile', error=error))
    
    # Si el método no es POST
    success = request.args.get('success')
    error = request.args.get('error')    
    # Obtener el ID del usuario de la sesión
    user_id = session.get('user_id')    
    if user_id is None:
        # Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('inicio_sesion'))    
    # Conectar a la base de datos
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Obtener la información del usuario
            cur.execute(f"""SELECT u.nom_usu, u.ape_usu, u.doc_usu, u.cor_usu, u.con_usu, r.tip_rol 
            FROM usuario u JOIN roles r ON u.id_rol = r.id_rol
            WHERE u.id_usu = {user_id};""")
            user_data = cur.fetchone()
            print(user_data)            
            # Si se encontró al usuario, asignar los datos
            if user_data:
                user = {
                    "nom_usu": user_data[0],
                    "ape_usu": user_data[1],
                    "doc_usu": user_data[2],
                    "cor_usu": user_data[3],
                    "con_usu": user_data[4],
                    "tip_rol": user_data[5],
                    "id_usu": user_id
                }            
            # Renderizar el template con los datos del usuario y los mensajes de éxito/error
            if success == "1" or error == "2":
                return render_template('autenticacion_y_registro/edit_profile.html', success=success, error=error, user=user)
            else:
                return render_template('autenticacion_y_registro/edit_profile.html', user=user)

# Ruta para editar el perfil de un usuario por parte del administrador
@app.route('/update_user', methods=['GET', 'POST'])
def update_user():
    if request.method == 'POST':  # Verifica si la solicitud es POST
        user_id = session.get('user_id')  # Obtiene el ID del usuario autenticado de la sesión
        id_usu = int(request.form['id_usu'])  # Obtiene el ID del usuario del formulario
        nom_usu = request.form['nom_usu']  # Obtiene el nombre del usuario del formulario
        ape_usu = request.form['ape_usu']  # Obtiene el apellido del usuario del formulario
        per_usu = request.form['per_usu']  # Obtiene el perfil del usuario del formulario
        doc_usu = request.form['doc_usu']  # Obtiene el documento del usuario del formulario
        id_rol = request.form['rol_usu']  # Obtiene el rol del usuario del formulario
                
        # Conectar a la base de datos y actualizar el usuario
        with get_db_connection() as conn:  # Abre una conexión a la base de datos
            with conn.cursor() as cur:  # Crea un cursor para ejecutar las consultas
                # Verificar si el usuario es diferente del usuario autenticado
                if id_usu != user_id:  # Si el ID del usuario del formulario no es el mismo que el ID del usuario autenticado
                    cur.execute('UPDATE usuario SET per_usu = %s WHERE id_usu = %s;', (per_usu, id_usu))  # Actualiza el perfil del usuario
                
                cur.execute('''
                    UPDATE usuario 
                    SET nom_usu = %s, ape_usu = %s, doc_usu = %s, id_rol = %s 
                    WHERE id_usu = %s;
                ''', (nom_usu, ape_usu, doc_usu, id_rol, id_usu))  # Actualiza los datos del usuario
                
                conn.commit()  # Guarda cambios en la base de datos
        
        success = '1'  # Establece un indicador de éxito
        return redirect(url_for('update_user', success=success))  # Redirige a la misma página con el indicador de éxito

    success = request.args.get('success')  # Obtiene el indicador de éxito de los parámetros de la URL
    error = request.args.get('error')  # Obtiene el indicador de error de los parámetros de la URL
    user_id = session.get('user_id')  # Obtiene el ID del usuario autenticado de la sesión
    if user_id is None:  # Si el usuario no ha iniciado sesión
        return redirect(url_for('redirigir'))  # Redirige a la página de inicio de sesión   
    
    # Obtener más información del usuario a partir de su ID
    with get_db_connection() as conn:  # Abre una conexión a la base de datos
        with conn.cursor() as cur:  # Crea un cursor para ejecutar las consultas
            cur.execute('SELECT per_usu FROM usuario WHERE id_usu = %s;', (user_id,))  # Obtiene el perfil del usuario autenticado
            user = cur.fetchone()  # Obtiene el resultado de la consulta
                        
            if user[0] == 'Administrador':  # Si el usuario autenticado es un Administrador
                cur.execute('''
                    SELECT * FROM roles;
                ''')  # Obtiene todos los roles
                rol = cur.fetchall()  # Obtiene todos los resultados de la consulta
                cur.execute('''
                    SELECT * FROM usuario
                    JOIN roles ON usuario.id_rol = roles.id_rol;
                ''')  # Obtiene todos los usuarios y sus roles
                edit_usu = cur.fetchall()  # Obtiene todos los resultados de la consulta
                
                if success == "1" or error == "2":  # Si hay un indicador de éxito o error
                    return render_template('autenticacion_y_registro/edit_user.html', success=success, error=error, rol=rol, edit_usu=edit_usu)  # Renderiza la plantilla con los datos obtenidos
                else:
                    return render_template('autenticacion_y_registro/edit_user.html', rol=rol, edit_usu=edit_usu)  # Renderiza la plantilla con los datos obtenidos
            else:
                return redirect(url_for('inicio_principal'))  # Si el usuario no es Administrador, redirige a la página principal

# Conexión de la estación meteorológica con el sistema de información
def davis():
    # Inicia una función llamada `davis` que se ejecutará indefinidamente.
    while True:
        print("Dato recibido")
        
        # Llaves de la API (se usan para autenticar y acceder a los datos).
        API_KEY = "jxhpskyfalmhlegx9mwqnwplcpmoltc0"
        STATION_ID = "181874"
        headers = {"X-Api-Secret": "sxchcxmtchcydblvcgbknst9mumap1cq"}

        # Obtiene el timestamp actual y define el rango de tiempo de 30 días hacia atrás.
        end_timestamp = int(time.time())
        start_timestamp = end_timestamp - (30 * 24 * 3600)

        # Duración máxima permitida para cada consulta (86400 segundos = 1 día).
        max_duration_seconds = 86400

        # Bucle para procesar datos en bloques de tiempo.
        while end_timestamp > start_timestamp:
            current_start = max(end_timestamp - max_duration_seconds, start_timestamp)
            url = f"https://api.weatherlink.com/v2/historic/{STATION_ID}?api-key={API_KEY}&start-timestamp={current_start}&end-timestamp={end_timestamp}"
            
            try:
                response = requests.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json().get('sensors', [])
                    db_data = []

                    for sensor in data:
                        for inner_data in sensor.get('data', []):
                            ts = inner_data.get('ts')
                            avg, hi = inner_data.get('solar_rad_avg'), inner_data.get('solar_rad_hi')
                            db_data.append(((avg, hi), datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')))

                    # Guardar los datos en la base de datos
                    with get_db_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.executemany("""
                                INSERT INTO dato_irradiancia (prom_irr, max_irr, created_at)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (created_at) DO NOTHING
                            """, [(prom, max_, created_at) for (prom, max_), created_at in db_data])
                            conn.commit()
                    
                    
                elif response.status_code == 400:
                    print("Error 400: Solicitud incorrecta", response.json())

            except requests.RequestException as e:
                print(f"Error en la API: {e}")

            end_timestamp = current_start - 1
        print("Datos guardados en la base de datos.")
        # Revisar y completar datos faltantes en los últimos 30 días
        revisar_completar_datos_faltantes()
        time.sleep(300)

# Función para revisar y completar datos faltantes en los últimos 30 días
def revisar_completar_datos_faltantes():
    # Definir el rango de 30 días
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    # Recuperar todos los datos de los últimos 30 días desde la base de datos
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT prom_irr, max_irr, created_at
                FROM dato_irradiancia
                WHERE created_at >= %s AND created_at <= %s
                ORDER BY created_at ASC
            """, (start_date.strftime('%Y-%m-%d %H:%M:%S'), end_date.strftime('%Y-%m-%d %H:%M:%S')))
            records = cursor.fetchall()

    # Verificar intervalos de tiempo faltantes en los datos obtenidos
    interpolated_data = []
    last_timestamp = None

    for row in records:
        prom_irr, max_irr, created_at = row
        ts = int(created_at.timestamp())  # Utilizar directamente `created_at.timestamp()` en lugar de `strptime`

        if last_timestamp and ts - last_timestamp > 300:
            # Interpolación para intervalos de 5 minutos faltantes
            missing_intervals = (ts - last_timestamp) // 300
            for i in range(1, missing_intervals):
                missing_ts = last_timestamp + i * 300
                previous_year_data = get_previous_year_data(missing_ts)

                if previous_year_data and previous_year_data[0] is not None:
                    interpolated_entry = (previous_year_data[0], previous_year_data[1], datetime.fromtimestamp(missing_ts).strftime('%Y-%m-%d %H:%M:%S'))
                    print("Dato interpolado IF:", interpolated_entry)
                else:
                    interpolated_entry = (0, 0, datetime.fromtimestamp(missing_ts).strftime('%Y-%m-%d %H:%M:%S'))

                    print("Dato interpolado ELSE :", interpolated_entry)
                interpolated_data.append(interpolated_entry)

        last_timestamp = ts

    # Insertar los datos interpolados en la base de datos
    if interpolated_data:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany("""
                    INSERT INTO dato_irradiancia (prom_irr, max_irr, created_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (created_at) DO NOTHING
                """, interpolated_data)
        print("Datos interpolados añadidos a la base de datos.")
    else:
        print("No se encontraron datos faltantes para interpolar.")

# Función para obtener datos del año anterior para un timestamp específico
def get_previous_year_data(ts):
    query = "SELECT prom_irr, max_irr FROM dato_irradiancia WHERE created_at = %s"
    one_year_ago = (datetime.fromtimestamp(ts) - timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (one_year_ago,))
            result = cursor.fetchone()
            return result if result else (None, None)
        
# Crear un hilo para la función davis
data_fetch_thread = threading.Thread(target=davis)
data_fetch_thread.daemon = True  # Para asegurarse de que el hilo se detenga al cerrar la aplicación
data_fetch_thread.start()

#Ruta para ir a la seccion de datos de irradiancia
@app.route('/irradiance_display',methods=['GET', 'POST'])
def irradiance_display():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('inicio_sesion'))  
    
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        # Asegúrate de que las fechas no están vacías antes de añadir la hora
        start_date = f"{start_date} 06:00:00"  # Agrega hora 06:00:00 a la fecha de inicio
        end_date = f"{end_date} 19:00:00"      # Agrega hora 19:00:00 a la fecha final

        # Redirige a la misma ruta con parámetros en la URL para evitar el reenvío del formulario
        return redirect(url_for('irradiance_display', start_date=start_date, end_date=end_date))

    # Procesa los datos de la base de datos
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if start_date and end_date:
                cur.execute('SELECT prom_irr, max_irr, created_at FROM dato_irradiancia WHERE (created_at >= %s and created_at <= %s) ORDER BY created_at desc;', (start_date, end_date))
            else:
                cur.execute('SELECT prom_irr, max_irr, created_at FROM dato_irradiancia ORDER BY created_at desc LIMIT 144;')
            db_irr = cur.fetchall()
            
    return render_template('informe_y_Estadistica/date_davis.html', db_irr=db_irr)

# Ruta para obtener los últimos datos de irradiación en formato JSON
@app.route('/get_latest_irradiance_data')
def get_latest_irradiance_data():
    # Suponiendo que tienes una función para obtener la conexión a la base de datos
    with get_db_connection() as conn:  
        with conn.cursor() as cur:  
            cur.execute('SELECT prom_irr, max_irr, created_at FROM dato_irradiancia ORDER BY created_at DESC LIMIT 1')  # Ordena por fecha de creación
            db_irr = cur.fetchall()  # Obtiene todos los resultados de la consulta
            
    # Estructura los datos en una lista de diccionarios
    data = [{'prom_irr': f"{float(row[0]):.1f}", 'max_irr': f"{float(row[1]):.1f}", 'created_at': row[2].strftime('%Y-%m-%d %H:%M:%S')} for row in db_irr]
    
    return jsonify(data)  # Devuelve los datos en formato JSON

def consultas_demanda(start_date, end_date):
    # Obtener más información de los datos tomados con el HIOKI
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if not start_date or not end_date:
                cur.execute("SELECT MAX(created_at) FROM dato_demanda")
                last_date = cur.fetchone()[0]  # Obtener la última fecha
                if last_date:
                    start_date = (last_date - timedelta(days=19)).strftime('%Y-%m-%d')
                    end_date = last_date.strftime('%Y-%m-%d')

            # Parámetros de fecha
            date_params = (start_date, end_date)

            # Consulta para db_dem
            cur.execute("""
                SELECT SUM(dat_dem) AS total_dem, to_char(created_at, 'YYYY-MM-DD HH24:00:00') AS datetime
                FROM dato_demanda WHERE created_at >= %s AND created_at < %s
                GROUP BY to_char(created_at, 'YYYY-MM-DD HH24:00:00')
                ORDER BY to_char(created_at, 'YYYY-MM-DD HH24:00:00') DESC;
            """, date_params)
            db_dem = cur.fetchall()

            # Consulta para db_ana_dem
            cur.execute("""
                SELECT fec_adem, exc_adem, con_adem, per_adem 
                FROM analisis_demanda WHERE fec_adem >= %s AND fec_adem < %s
                ORDER BY fec_adem ASC;
            """, date_params)
            db_ana_dem = cur.fetchall()
            # Consultas promedio
            consulta_promedio_sql = """
                SELECT %s AS nom_adem, round(CAST(AVG({column}) AS numeric), 2)
                FROM analisis_demanda WHERE fec_adem >= %s AND fec_adem < %s {extra_condition};
            """
            consulta_promedio = [
                ('Promedio consumo neto', 'exc_adem', 'AND per_adem < -2500 AND per_adem IS NOT NULL'),
                ('Promedio actual neto', 'con_adem', 'AND per_adem < -2500 AND per_adem IS NOT NULL'),
                ('Energía perdida', 'per_adem', 'AND per_adem < -2500 AND per_adem IS NOT NULL'),
                ('Pagaría a full', 'con_adem', 'AND per_adem IS NULL')
            ]

            consult_promedio = []
            for nom_adem, column, extra_condition in consulta_promedio:
                cur.execute(consulta_promedio_sql.format(column=column, extra_condition=extra_condition), (nom_adem, *date_params))
                result = cur.fetchone()
                consult_promedio.append((result[0], float(result[1]) if result and result[1] is not None else 0.0))


            # Consultas neto
            consulta_neto_sql = """
                SELECT %s AS nom_adem, round(CAST(SUM({column}) AS numeric), 2)*{factor}
                FROM analisis_demanda WHERE fec_adem >= %s AND fec_adem < %s {extra_condition};
            """
            consulta_neto = [
                ('Consumo neto', 'exc_adem', 1.5, ''),
                ('Consumo actual neto', 'con_adem', 1.5, ''),
                ('Energía perdida', 'per_adem', 1.5, ''),
                ('Pagaría a full', 'con_adem', 10, 'AND per_adem IS NULL')
            ]

            consult_neto = []
            for nom_adem, column, factor, extra_condition in consulta_neto:
                cur.execute(consulta_neto_sql.format(column=column, factor=factor, extra_condition=extra_condition), (nom_adem, *date_params))
                result = cur.fetchone()
                consult_neto.append((result[0], float(result[1]) if result and result[1] is not None else 0.0))



    return db_dem, db_ana_dem, consult_promedio, consult_neto


@app.route('/demand_display', methods=['GET', 'POST'])
def demand_display():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('inicio_sesion'))

    start_date = end_date = costo = None
    error_file = False

    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        try:
            costo = float(request.form.get('costo_energia', 0.0))  # Default value 0.0 if not provided
        except (ValueError, TypeError):
            costo = 0.0  # O cualquier valor predeterminado


        if not start_date or not end_date:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT MAX(created_at) FROM dato_demanda")
                    last_date = cursor.fetchone()[0]
            
            if last_date:
                start_date = (last_date - timedelta(days=10)).strftime('%Y-%m-%d')
                end_date = last_date.strftime('%Y-%m-%d')

        # Procesar archivo excel si existe
        file = request.files.get('file')
        if file and file.filename.endswith('.xlsx'):
            try:
                df_modelo = pd.read_excel(file, sheet_name='97intvl')
                required_columns = {'Date', 'Time', 'AvePsum'}
                if not required_columns.issubset(df_modelo.columns):
                    error_file = True
                else:
                    df_modelo['Datetime'] = pd.to_datetime(df_modelo['Date'].astype(str) + ' ' + df_modelo['Time'].astype(str))
                    data_to_insert = df_modelo[['Datetime', 'AvePsum']].values.tolist()
            except ValueError:
                error_file = True

            if not error_file:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        duplicado = False
                        for date_time, ave_psum in data_to_insert:
                            cursor.execute("""
                                SELECT 1 FROM dato_demanda
                                WHERE dat_dem = %s AND created_at = %s AND id_usu = %s
                            """, (ave_psum, date_time, user_id))

                            if cursor.fetchone():
                                duplicado = True
                                break

                            cursor.execute("""
                                INSERT INTO dato_demanda (dat_dem, created_at, id_usu)
                                VALUES (%s, %s, %s)
                            """, (ave_psum, date_time, user_id))

                        conn.commit()

                        if not duplicado:
                            # Consultas de análisis
                            db_dem, db_ana_dem, consult_promedio, consult_neto = consultas_demanda(start_date, end_date)
                            return render_template(
                                'informe_y_Estadistica/date_hioki.html',
                                db_dem=db_dem, db_ana_dem=db_ana_dem,
                                consult_promedio=consult_promedio, consult_neto=consult_neto,
                                costo=costo
                            )

    # Consultas sin archivo cargado
    db_dem, db_ana_dem, consult_promedio, consult_neto = consultas_demanda(start_date, end_date)
    return render_template(
        'informe_y_Estadistica/date_hioki.html',
        db_dem=db_dem, db_ana_dem=db_ana_dem,
        consult_promedio=consult_promedio, consult_neto=consult_neto, costo=costo
    )



#PREDICCION DE IRRADIANCIA
@app.route('/irradiance_prediction')
def irradiance_prediction():
    prediction_g = 1
    # Ruta donde se encuentra el modelo
    ruta = 'C:/PROYECTO/Relab/pro_relab/energia_renovable/modelo/'
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT prom_irr, created_at 
                FROM (
                    SELECT prom_irr, created_at 
                    FROM dato_irradiancia 
                    WHERE created_at::time >= '06:00:00' 
                    AND created_at::time <= '19:00:00' 
                    AND created_at::date < current_date
                    AND created_at::date BETWEEN current_date - INTERVAL '30 days' AND current_date - INTERVAL '1 day'
                    ORDER BY created_at DESC 
                ) as consulta
                ORDER BY created_at ASC;
            """)
            db = cur.fetchall()

    

    # Convertir los resultados a un DataFrame de pandas
    df = pd.DataFrame(db, columns=["prom_irr", "created_at"])

    # Establecer la columna 'created_at' como índice para el formato tabular (asignando el resultado)
    df_filtrado_nuevos_datos = df.set_index('created_at', inplace=False)
    print(df_filtrado_nuevos_datos)
    # Extraer los valores de irradiancia
    DATOS_NUEVOS = df_filtrado_nuevos_datos['prom_irr'].values


    # Escalar los nuevos datos entre -1 y 1
    scaler_nuevos = MinMaxScaler(feature_range=(-1, 1))
    datos_nuevos_escalados = scaler_nuevos.fit_transform(DATOS_NUEVOS.reshape(-1, 1))

    # Definir las secuencias para entrenamiento y predicción basados en el tamaño de las secuencias de entrada
    Dias_pasados = 7  # N
    LONG_SEC = 156 * Dias_pasados  # Tamaño de entrada
    Dias_futuros = 1  # Número de días a predecir
    N_STEPS = 156  # Tamaño de salida (para 1 día, 156 valores)

    print(f"Tamaño de los datos escalados nuevos: {len(datos_nuevos_escalados)}")

    # Generar secuencias solo si hay suficientes datos
    if len(datos_nuevos_escalados) > LONG_SEC + N_STEPS:
        X_train_nuevos, Y_train_nuevos = [], []
        for i in range(len(datos_nuevos_escalados) - LONG_SEC - N_STEPS):
            X_train_nuevos.append(datos_nuevos_escalados[i:i + LONG_SEC])
            Y_train_nuevos.append(datos_nuevos_escalados[i + LONG_SEC:i + LONG_SEC + N_STEPS])  # Ajuste para N_STEPS

        # Convertir a arrays de numpy
        X_train_nuevos = np.array(X_train_nuevos)
        Y_train_nuevos = np.array(Y_train_nuevos)

        # Verificar la forma de Y_train_nuevos para asegurarse de que sea [batch_size, N_STEPS]
        print(f"Forma de Y_train_nuevos: {Y_train_nuevos.shape}")  # Debe ser [batch_size, N_STEPS]

        # Imprimir el tamaño de las secuencias antes del reshape
        print(f"Forma de X_train_nuevos antes del reshape: {X_train_nuevos.shape}")

        # Reestructurar para que tenga la forma adecuada para el modelo (batch_size, time_steps, features)
        X_train_nuevos = np.reshape(X_train_nuevos, (X_train_nuevos.shape[0], X_train_nuevos.shape[1], 1))
        print(f"Forma de X_train_nuevos después del reshape: {X_train_nuevos.shape}")
    ################################################################################
        # Cargar el modelo ya entrenado para su reentrenamiento
        modelo = tf.keras.models.load_model(ruta + '5U1L64B.keras')

        # Reentrenar el modelo con los nuevos datos
        #EPOCHS = 20
        #BATCH_SIZE = 64
        #historial = modelo.fit(X_train_nuevos, Y_train_nuevos, batch_size=BATCH_SIZE, epochs=EPOCHS, verbose=1)

        # Predicción multistep para días futuros
        # Usar el último segmento de datos escalados para predecir los días futuros
        ultimo_X = datos_nuevos_escalados[-LONG_SEC:].reshape(1, LONG_SEC, 1)

        predicciones_futuras = []
        num_predicciones = Dias_futuros * 156  # 156 valores por día

        for i in range(int(num_predicciones // N_STEPS)):
            # Hacer la predicción usando el último punto disponible
            pred_nueva = modelo.predict(ultimo_X)
            predicciones_futuras.extend(pred_nueva[0])  # Agrega todos los pasos predichos

            # Actualizar el último_X para incluir la nueva predicción
            ultimo_X = np.roll(ultimo_X, -N_STEPS, axis=1)
            ultimo_X[0, -N_STEPS:, 0] = pred_nueva[0].flatten()  # Aplanar el array antes de asignarlo

        # Transformar las predicciones de vuelta a la escala original
        predicciones_futuras = np.array(predicciones_futuras).reshape(-1, 1)
        predicciones_futuras_inv = scaler_nuevos.inverse_transform(predicciones_futuras)
        
        # Obtener la fecha y hora actuales
        fecha_actual = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)

        # Sumar un día y establecer la hora a las 6:00
        print('Esta es la fecha del dia sguiente: ')
        #fecha_actual = (fecha_hora_actual + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
        print(fecha_actual)

        eje_x_pred = []
        while len(eje_x_pred) < len(predicciones_futuras_inv):
            if 6 <= fecha_actual.hour < 19:  # Solo horas de 6:00 a 19:00
                eje_x_pred.append(fecha_actual)
            fecha_actual += pd.Timedelta(minutes=5)

        # Crear DataFrame para las predicciones
        db_irr = pd.DataFrame({
            'fecha': eje_x_pred,
            'predicciones': predicciones_futuras_inv.flatten()
        })
        print(db_irr)
    else:
        print("No hay suficientes datos para generar secuencias de entrenamiento")
    return render_template('informe_y_Estadistica/date_davis.html',prediction_g = prediction_g, db_irr=db_irr.to_dict(orient='records'))


if __name__ == '__main__':
    app.run(debug=True)
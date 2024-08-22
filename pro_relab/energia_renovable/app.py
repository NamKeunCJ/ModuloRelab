import psycopg2
import hashlib
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import date, datetime, timedelta
import threading
import time
import requests # elementos para datos davis
import xml.etree.ElementTree as ET # elementos para datos davis
import pandas as pd #Extrer los datos del archivo plano


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

#Conexion de la estacion meteorologica con el sistema de informacion
def davis():
    while True:
        print("Dato recibido")
        user_id = 1
        API_KEY = "jxhpskyfalmhlegx9mwqnwplcpmoltc0"
        STATION_ID = "181874"
        headers = {"X-Api-Secret": "sxchcxmtchcydblvcgbknst9mumap1cq"}

        end_timestamp = int(time.time())
        print("End timestamp:", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_timestamp)))

        six_months_seconds = 30 * 24 * 3600

        start_timestamp = end_timestamp - six_months_seconds
        print("Start timestamp:", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_timestamp)))

        max_duration_seconds = 86400

        current_end_timestamp = end_timestamp
        while current_end_timestamp > start_timestamp:
            current_start_timestamp = max(current_end_timestamp - max_duration_seconds, start_timestamp)
            base_url = "https://api.weatherlink.com/v2/historic"
            url = f"{base_url}/{STATION_ID}?api-key={API_KEY}&start-timestamp={current_start_timestamp}&end-timestamp={current_end_timestamp}"

            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data.get('sensors'), list):
                        irradiance_data = []
                        db_data = []
                        for sensor_data in data['sensors']:
                            if isinstance(sensor_data.get('data'), list):
                                for inner_data in sensor_data['data']:
                                    solar_radiation_avg = inner_data.get('solar_rad_avg')
                                    solar_radiation_hi = inner_data.get('solar_rad_hi')
                                    solar_radiation_ene = inner_data.get('solar_energy')
                                    date_time_string = datetime.fromtimestamp(inner_data.get('ts')).strftime('%Y-%m-%d %H:%M:%S')

                                    irradiance_data.append({
                                        "date_time": date_time_string,
                                        "avg_irradiance": solar_radiation_avg,
                                        "highest_irradiance": solar_radiation_hi,
                                        "solar_energy": solar_radiation_ene
                                    })

                                    db_data.append((
                                        solar_radiation_avg,
                                        solar_radiation_hi,
                                        date_time_string,
                                        user_id
                                    ))

                        with get_db_connection() as conn:
                            with conn.cursor() as cursor:
                                for data in db_data:
                                    prom_irr, max_irr, created_at, id_usu = data
                                    
                                    insert_query = """
                                        INSERT INTO dato_irradiancia (
                                            prom_irr, max_irr, created_at, id_usu
                                        ) VALUES (%s, %s, %s, %s)
                                        ON CONFLICT (created_at) DO NOTHING
                                    """

                                    cursor.execute(insert_query, data)

                elif response.status_code == 400:
                    print("Error 400: Solicitud incorrecta. Verifique los parámetros de la solicitud.")
                    print(response.json())

            except requests.RequestException as e:
                print(f"Error al solicitar los datos de la API: {e}")

            current_end_timestamp = current_start_timestamp - 1

        time.sleep(300)
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
        # Redirige a la misma ruta con parámetros en la URL para evitar el reenvío del formulario
        return redirect(url_for('irradiance_display', start_date=start_date, end_date=end_date))

    # Procesa los datos de la base de datos
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if start_date and end_date:
                cur.execute('SELECT prom_irr, max_irr, created_at FROM dato_irradiancia WHERE (created_at >= %s and created_at <= %s) and prom_irr!=0 ORDER BY created_at desc;', (start_date, end_date))
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

def consultas_demanda():
    # Obtener más información de los datos tomados con el HIOKI
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT SUM(dat_dem) AS total_dem, to_char(created_at, 'YYYY-MM-DD HH24:00:00') AS datetime
                FROM dato_demanda
                GROUP BY to_char(created_at, 'YYYY-MM-DD HH24:00:00')
                ORDER BY to_char(created_at, 'YYYY-MM-DD HH24:00:00') DESC;
            """)
            db_dem = cur.fetchall()
            cur.execute("""
                SELECT fec_adem, exc_adem, con_adem, per_adem FROM analisis_demanda ORDER BY fec_adem ASC;
            """)
            db_ana_dem = cur.fetchall()
            # Lista de consulta_promedio
            consulta_promedio = [
                "SELECT 'Promedio consumo neto' as nom_adem, round(CAST(AVG(exc_adem) AS numeric), 2) FROM analisis_demanda WHERE per_adem < -2500 AND per_adem IS NOT NULL;",
                "SELECT 'Promedio actual neto' as nom_adem, round(CAST(AVG(con_adem) AS numeric), 2) FROM analisis_demanda WHERE per_adem < -2500 AND per_adem IS NOT NULL;",
                "SELECT 'Energía perdida' as nom_adem, round(CAST(AVG(per_adem) AS numeric), 2) FROM analisis_demanda WHERE per_adem < -2500 AND per_adem IS NOT NULL;",
                "SELECT 'Pagaría a full' as nom_adem, round(CAST(AVG(con_adem) AS numeric), 2) FROM analisis_demanda WHERE per_adem IS NULL;",                
            ]
            
            # Ejecutar consulta_promedio y almacenar resultados
            consult_promedio= []
            for consulta in consulta_promedio:
                cur.execute(consulta)
                result = cur.fetchone()
                if result:
                    consult_promedio.append((result[0], float(result[1]) if result[1] is not None else None))
                else:
                    consult_promedio.append((None, None))
            # Lista de consulta_neto
            consulta_neto = [
                "SELECT 'Consumo neto' as nom_adem, round(CAST(SUM(exc_adem) AS numeric), 2)*1.5 FROM analisis_demanda;",
                "SELECT 'Consumo actual neto' as nom_adem, round(CAST(SUM(con_adem) AS numeric), 2)*1.5 FROM analisis_demanda;",
                "SELECT 'Energía perdida' as nom_adem, round(CAST(SUM(per_adem) AS numeric), 2)*1.5 FROM analisis_demanda;",
                "SELECT 'Pagaría a full' as nom_adem, round(CAST(SUM(con_adem) AS numeric), 2)*10 FROM analisis_demanda WHERE per_adem IS NULL;"
            ]
            
            # Ejecutar consulta_neto y almacenar resultados
            consult_neto= []
            for consulta in consulta_neto:
                cur.execute(consulta)
                result = cur.fetchone()
                if result:
                    consult_neto.append((result[0], float(result[1]) if result[1] is not None else None))
                else:
                    consult_neto.append((None, None))
    return db_dem, db_ana_dem,consult_promedio, consult_neto

@app.route('/demand_display', methods=['GET', 'POST'])
def demand_display():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('inicio_sesion'))
    error_file=False
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.xlsx'):
            try:
                df_modelo = pd.read_excel(file, sheet_name='97intvl', header=0)
                # Verificar si las columnas necesarias están presentes
                required_columns = {'Date', 'Time', 'AvePsum'}
                if not required_columns.issubset(df_modelo.columns):
                    error_file=True
                else:
                    df_modelo['Datetime'] = pd.to_datetime(df_modelo['Date'].astype(str) + ' ' + df_modelo['Time'].astype(str), format='%Y-%m-%d %H:%M:%S')
                    data_to_insert = df_modelo[['Datetime', 'AvePsum']].values.tolist()

                    '''# Leer el archivo Excel
                    df_modelo = pd.read_excel(file, sheet_name='97intvl', header=0)                
                    # Unir las columnas 'Date' y 'Time' en un solo campo 'Datetime'
                    df_modelo['Datetime'] = pd.to_datetime(df_modelo['Date'].astype(str) + ' ' + df_modelo['Time'].astype(str), format='%Y-%m-%d %H:%M:%S')
                    # Convertir 'Date' a formato de fecha para filtrado
                    df_modelo['Date'] = pd.to_datetime(df_modelo['Date']).dt.date
                    # Excluir el primer y último día
                    df_filtered = df_modelo[(df_modelo['Date'] > df_modelo['Date'].min()) & (df_modelo['Date'] < df_modelo['Date'].max())]
                    # Extraer solo las columnas específicas y convertir a lista de listas
                    data_to_insert = df_filtered[['Datetime', 'AvePsum']].values.tolist()'''
                
            except ValueError as e:
                error_file=True

            if  not error_file:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        duplicado = False
                        for date_time, ave_psum in data_to_insert:
                            search_query = """
                                SELECT 1 FROM dato_demanda
                                WHERE dat_dem = %s AND created_at = %s AND id_usu = %s
                            """
                            cursor.execute(search_query, (ave_psum, date_time, user_id))
                            if cursor.fetchone():
                                duplicado = True
                                break
                            insert_query = """
                                INSERT INTO dato_demanda (dat_dem, created_at, id_usu)
                                VALUES (%s, %s, %s)
                            """
                            cursor.execute(insert_query, (ave_psum, date_time, user_id))
                        conn.commit()

                        if not duplicado:
                            # Consultas para análisis
                            queries = {
                                'excedente': """
                                    SELECT DATE(created_at), SUM(dat_dem) FROM dato_demanda
                                    GROUP BY DATE(created_at)
                                    ORDER BY DATE(created_at) DESC;
                                """,
                                'consumo': """
                                    SELECT DATE(datetime), SUM(total_dem) 
                                    FROM (
                                        SELECT to_char(created_at, 'YYYY-MM-DD HH24:00:00') AS datetime, SUM(dat_dem) AS total_dem
                                        FROM dato_demanda 
                                        GROUP BY to_char(created_at, 'YYYY-MM-DD HH24:00:00')
                                    ) AS datos
                                    WHERE total_dem >= 0 
                                    GROUP BY DATE(datetime) 
                                    ORDER BY DATE(datetime) DESC;
                                """,
                                'energia_perdida': """
                                    SELECT DATE(datetime), SUM(total_dem) 
                                    FROM (
                                        SELECT to_char(created_at, 'YYYY-MM-DD HH24:00:00') AS datetime, SUM(dat_dem) AS total_dem
                                        FROM dato_demanda 
                                        GROUP BY to_char(created_at, 'YYYY-MM-DD HH24:00:00')
                                    ) AS datos
                                    WHERE total_dem <= 0  
                                    GROUP BY DATE(datetime) 
                                    ORDER BY DATE(datetime) DESC;
                                """
                            }
                            
                            results = {}
                            for key, query in queries.items():
                                cursor.execute(query)
                                results[key] = cursor.fetchall()

                            # Insertar resultados en analisis_demanda y obtener id_adem
                            for (fecha, excedente), (_, consumo) in zip(results['excedente'], results['consumo']):
                                insert_analisis_query = """
                                    INSERT INTO analisis_demanda (fec_adem, exc_adem, con_adem)
                                    VALUES (%s, %s, %s)
                                    RETURNING id_adem
                                """
                                cursor.execute(insert_analisis_query, (fecha, excedente, consumo))
                                id_adem = cursor.fetchone()[0]
                                cursor.execute("""
                                    UPDATE dato_demanda
                                    SET id_adem = %s
                                    WHERE DATE(created_at) = %s
                                """, (id_adem, fecha))
                            conn.commit()

                            # Actualizar el campo per_adem en analisis_demanda
                            for fecha, energia in results['energia_perdida']:
                                cursor.execute("""
                                    UPDATE analisis_demanda
                                    SET per_adem = %s
                                    WHERE fec_adem = %s
                                """, (energia, fecha))
                            conn.commit()
    db_dem, db_ana_dem,consult_promedio, consult_neto = consultas_demanda()
    return render_template('informe_y_Estadistica/date_hioki.html', db_dem=db_dem, db_ana_dem=db_ana_dem)                       

@app.route('/demand_value_calculation', methods=['POST'])
def demand_value_calculation():
    # Verificar si el método de la solicitud es POST
    if request.method == 'POST': 
        costo = float(request.form['costo_energia'])  # Obtener el valor del costo de energia
        db_dem, db_ana_dem,consult_promedio, consult_neto = consultas_demanda()
        if db_dem == []:
            return render_template('informe_y_Estadistica/date_hioki.html', db_dem=db_dem, db_ana_dem=db_ana_dem)
        
        return render_template('informe_y_Estadistica/date_hioki.html', db_dem=db_dem, db_ana_dem=db_ana_dem, consult_promedio=consult_promedio, consult_neto=consult_neto, costo = costo)

#PREDICCION DE IRRADIANCIA
@app.route('/irradiance_prediction')
def irradiance_prediction():
    prediction_g = 1
    print (prediction_g)
    return render_template('informe_y_Estadistica/date_davis.html',prediction_g = prediction_g)

if __name__ == '__main__':
    app.run(debug=True)
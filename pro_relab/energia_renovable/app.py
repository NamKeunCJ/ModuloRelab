import psycopg2
import hashlib
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import date
import time
import requests #elemetos para datos davis
import xml.etree.ElementTree as ET #elemetos para datos davis
import datetime # la fecha davis cada 5 min

# Crear una instancia de la aplicación Flask
app = Flask(__name__)

# Configurar la clave secreta de la aplicación, utilizada para gestionar sesiones y cookies seguras
app.config['SECRET_KEY'] = 'unicesmag'

# Configurar los parámetros de la base de datos
app.config['DB_HOST'] = 'localhost'  # El host donde se encuentra la base de datos
app.config['DB_NAME'] = 'energia_renovable'  # El nombre de la base de datos
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

#list  usuarios
@app.route('/update_user', methods=['GET', 'POST'])
def update_user():
    if request.method == 'POST':
        user_id = session.get('user_id')
        id_usu = int(request.form['id_usu'])
        nom_usu = request.form['nom_usu']
        ape_usu = request.form['ape_usu']
        per_usu = request.form['per_usu']
        doc_usu = request.form['doc_usu']
        id_rol = request.form['rol_usu']
                
        # Conectar a la base de datos y actualizar el usuario
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verificar si el usuario es diferente del usuario autenticado
                if id_usu != user_id:
                    cur.execute('UPDATE usuario SET per_usu = %s WHERE id_usu = %s;', (per_usu, id_usu))
                
                cur.execute('''
                    UPDATE usuario 
                    SET nom_usu = %s, ape_usu = %s, doc_usu = %s, id_rol = %s 
                    WHERE id_usu = %s;
                ''', (nom_usu, ape_usu, doc_usu, id_rol, id_usu))
                
                conn.commit()  # Guardar cambios en la base de datos
        
        success = '1'
        return redirect(url_for('update_user', success=success))

    success = request.args.get('success')
    error = request.args.get('error')
    user_id = session.get('user_id')
    if user_id is None:
        # Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('redirigir'))   
    
    # Obtener más información del usuario a partir de su ID
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT per_usu FROM usuario WHERE id_usu = %s;', (user_id,))
            user = cur.fetchone()
                        
            if user[0] == 'Administrador':
                cur.execute('''
                    SELECT * FROM roles;
                ''')
                rol = cur.fetchall()
                cur.execute('''
                    SELECT * FROM usuario
                    JOIN roles ON usuario.id_rol = roles.id_rol;
                ''')
                edit_usu = cur.fetchall()
                
                if success == "1" or error == "2":
                    return render_template('autenticacion_y_registro/edit_user.html', success=success, error=error,rol=rol, edit_usu=edit_usu)
                else:
                    return render_template('autenticacion_y_registro/edit_user.html', rol=rol,edit_usu=edit_usu)
            else:
                return redirect(url_for('inicio_principal'))

#Conexcion davis con API
@app.route('/irradiance_display')
def irradiance_display():
    user_id = session.get('user_id')
    if user_id is None:
        # Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('inicio_sesion'))  
    
    # Reemplaza con tu clave de API y el ID de la estación
    API_KEY = "jxhpskyfalmhlegx9mwqnwplcpmoltc0"
    STATION_ID = "181874"  # Puedes usar un ID entero o un UUID

    # Establece la hora de inicio deseada (ajústala según sea necesario)
    start_date = f"{date.today()} 01:00:00"  # Ejemplo de fecha y hora

    # Convierte la hora de inicio a una marca de tiempo Unix
    start_timestamp = int(time.mktime(time.strptime(start_date, "%Y-%m-%d %H:%M:%S")))

    # Calcula la duración deseada (ajústala según sea necesario)
    duration_seconds = 3600*24  # Una hora en segundos (modifica según tus necesidades)

    # Calcula la marca de tiempo de finalización basada en la duración
    end_timestamp = start_timestamp + duration_seconds

    # Construye la URL de solicitud de la API
    base_url = "https://api.weatherlink.com/v2/historic"
    url = f"{base_url}/{STATION_ID}?api-key={API_KEY}&start-timestamp={start_timestamp}&end-timestamp={end_timestamp}"

    # Establece el encabezado del secreto de la API
    headers = {"X-Api-Secret": "sxchcxmtchcydblvcgbknst9mumap1cq"}  # Reemplaza con tu secreto de API real

    context = {'irradiance_data': []}  # Inicializa context con una lista vacía por defecto

    try:
        # Envía una solicitud HTTP GET
        response = requests.get(url, headers=headers)

        # Verifica si la respuesta fue exitosa (código de estado 200)
        if response.status_code == 200:
            data = response.json()

            if isinstance(data.get('sensors'), list):
                irradiance_data = [] 
                for sensor_data in data['sensors']:
                    if isinstance(sensor_data.get('data'), list):
                        for inner_data in sensor_data['data']:
                            # Extrae los datos
                            solar_radiation_avg = inner_data.get('solar_rad_avg')
                            solar_radiation_hi = inner_data.get('solar_rad_hi')
                            solar_radiation_ene = inner_data.get('solar_energy')
                            ts = inner_data.get('ts')
                            tz_offset = inner_data.get('tz_offset')

                            # Convierte la marca de tiempo a datetime con la hora
                            if isinstance(tz_offset, int):
                                tz_offset = tz_offset / 3600

                            # Convertir marca de tiempo a fecha y hora con hora
                            timestamp_utc = datetime.datetime.fromtimestamp(ts)
                            offset_hours = tz_offset / 3600
                            timestamp_local = timestamp_utc + datetime.timedelta(hours=offset_hours)
                            date_time_string = timestamp_local.strftime("%Y-%m-%d %H:%M:%S %p")

                            # Agrega los datos a la lista
                            irradiance_data.append({
                                "date_time": date_time_string,
                                "avg_irradiance": solar_radiation_avg,
                                "highest_irradiance": solar_radiation_hi,
                                "solar_energy": solar_radiation_ene
                            })

                # Asigna irradiance_data al contexto
                context['irradiance_data'] = irradiance_data

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        context['error_message'] = f"No se pudieron obtener los datos de irradiancia: {e}"

    return render_template('informe_y_Estadistica/date_davis.html', **context)


if __name__ == '__main__':
    app.run(debug=True)
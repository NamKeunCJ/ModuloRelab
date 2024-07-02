import psycopg2
import hashlib
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import date
import time
import requests #elemetos para datos davis
import xml.etree.ElementTree as ET #elemetos para datos davis
import datetime # la fecha davis cada 5 min

app = Flask(__name__)
app.config['SECRET_KEY'] = 'unicesmag'
app.config['DB_HOST'] = 'localhost'
app.config['DB_NAME'] = 'energia_renovable'
app.config['DB_USER'] = 'postgres'
app.config['DB_PASSWORD'] = 'unicesmag'

def get_db_connection():
    conn = psycopg2.connect(
        host=app.config['DB_HOST'],
        database=app.config['DB_NAME'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD']
    )
    return conn

# Ruta para mostrar datos en la página index
@app.route('/')
def inicio_sesion():
    user_id = session.get('user_id')
    if user_id is not None:
        # Si el usuario ha iniciado sesión, redirigir a la página principal
        return redirect(url_for('inicio_principal'))
    return render_template('autenticacion_y_registro/index.html')

# Agrega esta nueva ruta para redirigir al índice
@app.route('/redirigir')
def redirigir():
    return redirect(url_for('inicio_sesion'))

# Ruta para realizar el registro
@app.route('/registro', methods=['GET'])
def registro():
    # Buscar todos los roles en la base de datos
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM roles')
            rol = cur.fetchone()
    return render_template('autenticacion_y_registro/registro.html', rol = rol)

# Ruta para manejar el inicio de sesión (POST)
@app.route('/login', methods=['POST'])
def login():
    mail = request.form['cor_usu']
    password = request.form['con_usu']
    
    # Encriptar el password ingresado a MD5
    password_md5 = hashlib.md5(password.encode()).hexdigest()
    
    # Buscar el usuario y la contraseña en la base de datos por su nombre de usuario
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id_usu, per_usu FROM usuario WHERE cor_usu=%s AND con_usu=%s;', (mail, password_md5))
            user = cur.fetchone()
    
    if user is not None:
        session['user_id'] = user[0]
        session['user_rol'] = user[1]
        return 'success'
    else:
        return 'error'


# Ruta para manejar el registro de una cuenta (POST)       
@app.route('/cuenta', methods=['POST'])
def cuenta():    
    if request.method == 'POST':        
        nombres = request.form['nom_usu']
        apellidos = request.form['ape_usu']
        correo = request.form['cor_usu']
        numero_documento = request.form['doc_usu']
        contra = request.form['con_usu']
        password_md5 = hashlib.md5(contra.encode()).hexdigest()
        # Buscar el usuario en la base de datos por su nombre de usuario y número de documento
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT cor_usu, doc_usu FROM usuario WHERE cor_usu=%s OR doc_usu=%s;', (correo, numero_documento))
                user_exis = cur.fetchone()
                print(user_exis)
                if user_exis is not None:
                    print("El usuario ya existe en la base de datos")
                    return 'exist' 
                else:                     
                    # Insertar el nuevo usuario en la base de datos
                    cur.execute("""
                        INSERT INTO usuario (nom_usu, ape_usu, cor_usu, doc_usu, con_usu)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (nombres, apellidos, correo, numero_documento, password_md5))
                    conn.commit()
                    print("Nuevo usuario agregado correctamente")
                    return 'success'      

# Página principal
@app.route('/inicio_principal')
def inicio_principal():
    user_id = session.get('user_id')    
    if user_id is None:
        # Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('redirigir'))

    # Obtener más información del usuario a partir de su ID
    with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f'SELECT id_usu FROM usuario WHERE id_usu={user_id} ;')
                user = cur.fetchone()
    return render_template('autenticacion_y_registro/pagina principal.html', user=user)


#Cerrar Sesion        
@app.route('/logout')
def logout():
    # Borrar la información de la sesión
    session.clear()
    # Redireccionar a la página de inicio o a donde prefieras
    return redirect(url_for('redirigir'))  


@app.route('/irradiance_display')
def irradiance_display():
    user_id = session.get('user_id')
    if user_id is None:
        # Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('redirigir'))  
    
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

                            # Convert timestamp to datetime with time
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
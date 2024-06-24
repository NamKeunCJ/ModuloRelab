import hashlib
import json
from babel.dates import format_date
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, extract
import datetime as dt
from datetime import date
import serial
import threading
import serial.tools.list_ports
import time
import requests #elemetos para datos davis
import xml.etree.ElementTree as ET #elemetos para datos davis
import datetime # la fecha davis cada 5 min

app = Flask(__name__)
app.config['SECRET_KEY'] = 'unicesmag'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:unicesmag@localhost/energia_renovable'
db = SQLAlchemy(app)

# Importa el modelo Usuario desde models.py
from models import Usuario, Roles, Panel, Inversor, Bateria, Proyecto,TecnologiaPanel,ArregloDePaneles,ParaleloArreglo,SerieArreglo,BancoDeBaterias,ParaleloBanco,SerieBanco,Carga, SensorIrradiancia,EnergiaArreglo

#Importante para pasar tablas al html
@app.context_processor
def inject_models():
    return dict(SerieArreglo=SerieArreglo, ParaleloArreglo = ParaleloArreglo, SensorIrradiancia=SensorIrradiancia, Panel = Panel, Carga=Carga, SerieBanco=SerieBanco,EnergiaArreglo=EnergiaArreglo, ParaleloBanco = ParaleloBanco, Bateria = Bateria, Inversor = Inversor, format_date=format_date)


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
    rol = Roles.query.all()
    return render_template('autenticacion_y_registro/registro.html', rol = rol)

# Ruta para manejar el inicio de sesión (POST)
@app.route('/login', methods=['POST'])
def login():
    # Verificar el inicio de sesión (aquí implementarías la lógica de autenticación con una base de datos)
    mail = request.form['cor_usu']
    password = request.form['con_usu']
    # Encriptar el password ingresado a MD5
    password_md5 = hashlib.md5(password.encode()).hexdigest()
    # Buscar el usuario y la contraseña en la base de datos por su nombre de usuario
    user = Usuario.query.filter_by(cor_usu=mail, con_usu=password_md5).first()

    # Si no son None puede ingresar a la pantalla principal de los proyectos
    if user is not None :
        session['user_id'] = user.id_usu
        session['user_rol'] = user.per_usu
        return 'success'
    else:        
        return  'error'  

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
        correo_usu = Usuario.query.filter_by(cor_usu=correo).first()
        documento_usu = Usuario.query.filter_by(doc_usu=numero_documento).first()

        # Verificar si los datos ya existen en la base de datos
        if correo_usu is not None or documento_usu is not None:
            return 'exist'
        else:          
            nueva_cuenta = Usuario(nom_usu=nombres, ape_usu=apellidos, cor_usu=correo, doc_usu=numero_documento, con_usu=password_md5)
            
            # Agregar la nueva cuenta a la base de datos
            db.session.add(nueva_cuenta)
            db.session.commit()

            # Redireccionar a la página de inicio de sesión u otra página de tu elección
            return 'success'

# Página principal
@app.route('/inicio_principal')
def inicio_principal():
    id_pro = request.args.get('id_pro')
    user_id = session.get('user_id')
    cant_ban, cant_arr, cant_ent_inv, num_arr= 0, 0, 0, 0
    suma_ptot_arr,suma_pot_car ,suma_ene_ban= 0,0,0
    error_banco, error_cap_inv, error_inv_arr = 'vacio', 'vacio', ''
    if user_id is None:
        # Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('redirigir'))

    # Obtener más información del usuario a partir de su ID
    user = Usuario.query.get(user_id)
    pro = Proyecto.query.get(id_pro)
    
    pro_usu = Proyecto.query.filter_by(id_pro=id_pro,id_usu=user_id).first() 

    if pro_usu or user.per_usu=="Administrador" and id_pro is not None:
        # Realiza las consultas por separado para cada tabla
        proyecto = Proyecto.query.filter_by(id_pro=id_pro).first()
        inversor = Inversor.query.filter_by(id_inv=proyecto.id_inv).first()        
        arreglos = ArregloDePaneles.query.filter_by(id_pro=id_pro).order_by(ArregloDePaneles.id_arr).all()
        
        
        ene_real = (
            db.session.query(EnergiaArreglo, SensorIrradiancia)
            .join(SensorIrradiancia, EnergiaArreglo.id_sen == SensorIrradiancia.id_sen)
            .filter(EnergiaArreglo.id_pro == id_pro)
            .order_by(desc(EnergiaArreglo.fec_ene))
            .first()
        )
        if ene_real is not None:
            suma_ptot_arr = ene_real[0].tot_ene*1000 
        else:
            sen = SensorIrradiancia(fec_sen = datetime.now(), g_sen = 0, ref_sen = "None")
            db.session.add(sen)
            db.session.commit()
            id_sen=sen.id_sen
            ene = EnergiaArreglo(efi_ene = 0, tot_ene = 0,id_pro = id_pro, id_sen = id_sen, fec_ene = datetime.now())
            # Agregar el nuevo panel a la base de datos
            db.session.add(ene)
            db.session.commit()
            ene_real = (
                db.session.query(EnergiaArreglo, SensorIrradiancia)
                .join(SensorIrradiancia, EnergiaArreglo.id_sen == SensorIrradiancia.id_sen)
                .filter(EnergiaArreglo.id_pro == id_pro)
                .order_by(desc(EnergiaArreglo.fec_ene))
                .first()
            )

        todos_datos_ene = (
            db.session.query(EnergiaArreglo, SensorIrradiancia)
            .join(SensorIrradiancia, EnergiaArreglo.id_sen == SensorIrradiancia.id_sen)
            .filter(EnergiaArreglo.id_pro == id_pro)
            .order_by(desc(EnergiaArreglo.fec_ene))
            .all()
        )
        cant_arr = ArregloDePaneles.query.filter_by(id_pro=id_pro).count()
        bancos = BancoDeBaterias.query.filter_by(id_pro=id_pro).all()        
        cant_ban = BancoDeBaterias.query.filter_by(id_pro=id_pro).count() 
        # Obtener la suma de ene_ban
        suma_general_arr = db.session.query(db.func.sum(ArregloDePaneles.ptot_arr)).filter_by(id_pro=id_pro).scalar()
        if suma_general_arr is None:
            suma_general_arr = 0
        # Obtener la suma de ene_ban
        suma_ene_ban = db.session.query(db.func.sum(BancoDeBaterias.ene_ban)).filter_by(id_pro=id_pro).scalar()
        if suma_ene_ban is None:
            suma_ene_ban = 0
        cargas = Carga.query.filter_by(id_pro=id_pro).order_by(Carga.id_car).all()
        suma_pot_car = db.session.query(db.func.sum(Carga.pot_car)).filter_by(id_pro=id_pro).scalar()
        if suma_pot_car is None:
            suma_pot_car = 0 
        
        ener_inv_ban=energia_recibe_banco(suma_ptot_arr,suma_pot_car,id_pro)
        for banco in bancos:
            min_voltaje = db.session.query(db.func.min(ParaleloBanco.vser_pban)).filter_by(id_ban=banco.id_ban).scalar()
            max_voltaje = db.session.query(db.func.max(ParaleloBanco.vser_pban)).filter_by(id_ban=banco.id_ban).scalar()
            if min_voltaje!= max_voltaje and min_voltaje>0:
                error_banco=' La combinación de baterias con diferentes voltajes puede generar riesgos y problemas que podrían llevar a situaciones peligrosas.'
        if inversor is not None:
            cant_ent_inv = inversor.ent_inv
            cant_arr_del=cant_arr-cant_ent_inv
            while cant_arr_del>0:
                # Encuentra el ID del último arreglo
                id_ultimo_arr = db.session.query(ArregloDePaneles.id_arr).join(Proyecto, ArregloDePaneles.id_pro == Proyecto.id_pro).outerjoin(Inversor, Inversor.id_inv == Proyecto.id_inv).outerjoin(BancoDeBaterias, BancoDeBaterias.id_pro == Proyecto.id_pro).filter(Proyecto.id_pro == id_pro).order_by(ArregloDePaneles.id_arr.desc()).limit(1).scalar()

                if id_ultimo_arr is not None:
                    delete_arr(id_ultimo_arr)
                inversor = Inversor.query.filter_by(id_inv=proyecto.id_inv).first()    
                cant_arr = ArregloDePaneles.query.filter_by(id_pro=id_pro).count()
                cant_arr_del=cant_arr-inversor.ent_inv      

        if arreglos is not None and inversor is not None:
            #trae las potencias y el id de cada arreglo del proyectopara comprar con la pot del inversor
            ptot_arreglos = db.session.query(ArregloDePaneles.ptot_arr,ArregloDePaneles.id_arr).join(Proyecto, ArregloDePaneles.id_pro == Proyecto.id_pro).filter(Proyecto.id_pro == id_pro).order_by(ArregloDePaneles.id_arr).all()
            for ptot_arreglos in ptot_arreglos:
                ptot_arreglo = ptot_arreglos[0]*1.2  # Accede al primer valor (ptot_arr)
                num_arr=num_arr+1
                if ptot_arreglo > inversor.pmax_inv:
                    error_cap_inv = 'Error la capacidad del inversor no soporta el arreglo ' + str(num_arr)
                    error_inv_arr=str(ptot_arreglo)+ ' Potencia del arreglo > '+ str( inversor.pmax_inv)+ ' Potencia por entrada del Inversor '
                    break
                   
        # Crea una lista con los resultados
        resultado = [proyecto, inversor, arreglos, bancos,cargas]   
        return render_template('creacion_de_proyecto/index.html', user=user, pro=pro, proyecto=resultado, cant_ban=cant_ban, cant_arr=cant_arr, cant_ent_inv=cant_ent_inv, error_cap_inv = error_cap_inv, error_inv_arr=error_inv_arr,error_banco=error_banco,ene_real=ene_real,suma_ene_ban=suma_ene_ban, suma_pot_car=suma_pot_car,ener_inv_ban=ener_inv_ban, todos_datos_ene =todos_datos_ene,suma_general_arr =suma_general_arr)
    else:
        return render_template('creacion_de_proyecto/index.html', user=user)

def energia_recibe_banco(suma_ptot_arr,suma_pot_car,id_pro) :
    carga0 = 0
    carga1 = 0
    ener_inv_ban =0
    cargas = Carga.query.filter_by(id_pro=id_pro).order_by(Carga.id_car).all()
    if cargas and len(cargas) > 0:
        carga0 = cargas[0].pot_car
        if len(cargas) > 1:
            carga1 = cargas[1].pot_car
    if suma_ptot_arr > suma_pot_car:
        ener_inv_ban = suma_ptot_arr - suma_pot_car
    elif suma_ptot_arr > carga0+carga1:
        ener_inv_ban = suma_ptot_arr - (carga0+carga1)
    elif suma_ptot_arr > carga0:
        ener_inv_ban = suma_ptot_arr - carga0
    elif suma_ptot_arr == suma_pot_car:
        ener_inv_ban = suma_ptot_arr*0.1
    elif suma_ptot_arr < suma_pot_car:
        ener_inv_ban = suma_ptot_arr
    return ener_inv_ban

#Cerrar Sesion        
@app.route('/logout')
def logout():
    # Borrar la información de la sesión
    session.clear()
    # Redireccionar a la página de inicio o a donde prefieras
    return redirect(url_for('redirigir'))  

#mostrar modal panel
@app.route('/ver_modal_panel')
def ver_modal_panel():
    tecno = TecnologiaPanel.query.all() 
    return render_template('creacion_de_componentes/crea_panel.html', tecno=tecno)

#mostrar modal bateria
@app.route('/ver_modal_bateria')
def ver_modal_bateria():
    return render_template('creacion_de_componentes/crea_bateria.html')

#mostrar modal inversor
@app.route('/ver_modal_inversor')
def ver_modal_inversor():    
    return render_template('creacion_de_componentes/crea_inversor.html')
    
#mostrar modal proyecto
@app.route('/ver_modal_proyecto')
def ver_modal_proyecto():    
    return render_template('creacion_de_proyecto/crea_proyecto.html')

#Crear panel modal       
@app.route('/add_panel', methods=['POST'])
def add_panel():
    ref_pan = request.form['ref_pan']
    idu_pan = request.form['idu_pan']
    pmax_pan = float(request.form['pmax_pan'])  # Convierte los valores a números flotantes
    vmp_pan = float(request.form['vmp_pan'])
    imp_pan = float(request.form['imp_pan'])
    voc_pan = float(request.form['voc_pan'])
    isc_pan = float(request.form['isc_pan'])
    lar_pan = float(request.form['lar_pan'])
    anc_pan = float(request.form['anc_pan'])
    efi_pan = float(request.form['efi_pan'])
    are_pan = lar_pan * anc_pan
    nom_tec = request.form['tec_pan']
    den_pan = pmax_pan / are_pan
    user_id = session.get('user_id')
    tecno = TecnologiaPanel.query.filter_by( nom_tec = nom_tec ).first()
    pmax_cal_pan=vmp_pan*imp_pan
    if tecno is None:
        tecnologia_panel = TecnologiaPanel(nom_tec=nom_tec)
        db.session.add(tecnologia_panel)
        db.session.commit()
        id_tec = tecnologia_panel.id_tec
    else:
        id_tec = tecno.id_tec
    # Buscar el panel en la base de datos
    panel = Panel.query.filter_by(idu_pan=idu_pan, est_pan='Habilitado').first()

    # Verificar si los datos ya existen en la base de datos
    if panel is not None:
        return 'exist'
    elif pmax_cal_pan > pmax_pan - 0.6 and pmax_cal_pan < pmax_pan + 0.6:
        nueva_panel = Panel(ref_pan=ref_pan, efi_pan=efi_pan, idu_pan=idu_pan, pmax_pan=pmax_pan, vmp_pan=vmp_pan, imp_pan=imp_pan, voc_pan=voc_pan, isc_pan=isc_pan,
                            lar_pan=lar_pan, anc_pan=anc_pan, are_pan=are_pan, id_tec= id_tec, den_pan=den_pan, id_usu=user_id)

        # Agregar el nuevo panel a la base de datos
        db.session.add(nueva_panel)
        db.session.commit()

        return 'success'
    else:
        return 'error'
        

#Crear inversor modal
@app.route('/add_inversor', methods=['POST'])
def add_inversor():
    ref_inv = request.form['ref_inv']
    idu_inv = request.form['idu_inv']
    ent_inv = request.form['ent_inv']
    pmax_inv = float(request.form['pmax_inv'])  # Convierte los valores a números flotantes
    vme_inv = float(request.form['vme_inv'])
    ime_inv = float(request.form['ime_inv'])
    vsa_inv = float(request.form['vsa_inv'])
    ond_inv = request.form['ond_inv']
    efi_inv = float(request.form['efi_inv'])
    user_id = session.get('user_id')

    # Buscar el inversor en la base de datos
    inversor = Inversor.query.filter_by(idu_inv=idu_inv, est_inv='Habilitado').first()
    pmax_cal_inv= vme_inv * ime_inv
    # Verificar si los datos ya existen en la base de datos
    if inversor is not None :
        return 'exist'
    elif pmax_cal_inv > pmax_inv - 0.6 and pmax_cal_inv < pmax_inv + 0.6:
        nueva_inversor = Inversor(ref_inv=ref_inv, idu_inv=idu_inv, ent_inv=ent_inv, pmax_inv=pmax_inv, vme_inv=vme_inv, ime_inv=ime_inv, vsa_inv=vsa_inv,
                            ond_inv=ond_inv, efi_inv=efi_inv, id_usu=user_id)

        # Agregar el nuevo inversor a la base de datos
        db.session.add(nueva_inversor)
        db.session.commit()

        return 'success'
    else:
        return 'error'
        
#Crear bateria modal
@app.route('/add_bateria', methods=['POST'])
def add_bateria():
    ref_bat = request.form['ref_bat']
    vol_bat = float(request.form['vol_bat'])
    cap_bat = float(request.form['cap_bat'])
    ene_bat = vol_bat*cap_bat
    idu_bat = request.form['idu_bat']
    user_id = session.get('user_id')
    # Buscar el bateria en la base de datos
    bateria = Bateria.query.filter_by(idu_bat=idu_bat, est_bat='Habilitado').first()
    
    if bateria is not None :
        return 'exist'
    elif bateria is None:
        nueva_bateria = Bateria(ref_bat=ref_bat, idu_bat=idu_bat, vol_bat=vol_bat, cap_bat=cap_bat, ene_bat=ene_bat, id_usu=user_id)

        # Agregar el nuevo bateria a la base de datos
        db.session.add(nueva_bateria)
        db.session.commit()

        return 'success'
    else:
        return 'error'
    
#Crear Proyecto
@app.route('/add_proyecto', methods=['POST'])
def add_proyecto():
    nom_pro = request.form['nom_pro']
    cred_pro = request.form['cred_pro']
    cbat_pro = request.form['cbat_pro']
    user_id = session.get('user_id')
    # Buscar el inversor en la base de datos
    proyecto = Proyecto.query.filter_by(nom_pro = nom_pro, id_usu = user_id).first()

    # Verificar si los datos ya existen en la base de datos
    if proyecto is not None:
        return 'exist'
    else:
        nueva_proyecto = Proyecto(nom_pro=nom_pro, cred_pro=cred_pro, cbat_pro=cbat_pro,  id_usu=user_id)

        # Agregar el nuevo inversor a la base de datos
        db.session.add(nueva_proyecto)
        db.session.commit()
        #como ya se creo volvemos a buscar para saber su id
        id_pro = nueva_proyecto.id_pro
        return jsonify({'id_pro':id_pro})

#mostrar modal para agregar el inversor alproyecto
@app.route('/modal_inversor_project')
def modal_inversor_project(): 
    id_pro = request.args.get('id_pro')
    pro = Proyecto.query.get(id_pro)
    arr = ArregloDePaneles.query.filter_by(id_pro=id_pro).all()
    inv = Inversor.query.filter_by(est_inv='Habilitado').all()
    info = db.session.query(Proyecto, Inversor).join(Inversor, Proyecto.id_inv == Inversor.id_inv).filter(Proyecto.id_pro == id_pro).first()
    return render_template('creacion_de_proyecto/project_inversor.html', pro = pro, arr=arr , inv = inv, info=info)

#mostrar modal para agregar el inversor alproyecto card
@app.route('/modal_inversor_project_card')
def modal_inversor_project_card(): 
    id_pro = request.args.get('id_pro')
    pro = Proyecto.query.get(id_pro)
    arr = ArregloDePaneles.query.filter_by(id_pro=id_pro).all()
    inv = Inversor.query.filter_by(est_inv='Habilitado').all()
    info = db.session.query(Proyecto, Inversor).join(Inversor, Proyecto.id_inv == Inversor.id_inv).filter(Proyecto.id_pro == id_pro).first()
    return render_template('creacion_de_proyecto/project_inversor_card.html', pro = pro, arr=arr , inv = inv, info=info)

#agregar el inversor alproyecto
@app.route('/add_inversor_project', methods=['POST'])
def add_inversor_project():     
    id_pro = request.form['id_pro']
    id_inv = request.form['id_inv']
    proyecto = Proyecto.query.get(id_pro)
    proyecto.id_inv = id_inv
    db.session.commit()
    return redirect(url_for('inicio_principal', id_pro=id_pro))

#mostrar modal para agregar el arreglo alproyecto
@app.route('/modal_arreglo_project')
def modal_arreglo_project(): 
    id_pro = request.args.get('id_pro')
    pro = Proyecto.query.get(id_pro)  
    return render_template('creacion_de_proyecto/project_arreglo.html', pro = pro )

#agregar el arreglo alproyecto
@app.route('/add_arreglo_project', methods=['POST'])
def add_arreglo_project(): 
    id_pro = request.form['id_pro']
    id_inv = request.form['id_inv']
    num_ser = int(request.form['num_ser'])
    num_pan_ser = int(request.form['num_pan_ser']) 

    arreglo_nuevo = ArregloDePaneles(id_pro=id_pro,fil_arr=num_ser,col_arr=num_pan_ser)    
    db.session.add(arreglo_nuevo)
    db.session.commit()
    id_arr = arreglo_nuevo.id_arr   
    paralelos_ids = []
    series_ids = []    
    for _ in range (num_ser):
        paralelo = ParaleloArreglo(id_arr=id_arr)
        db.session.add(paralelo)
        db.session.commit()
        # Obtener el ID del paralelo recién agregado
        id_parr = paralelo.id_parr 
        paralelos_ids.append(id_parr) 
        for _ in range(num_pan_ser):        
            serie = SerieArreglo(id_parr=id_parr)
            db.session.add(serie)
            db.session.commit()
            id_sarr = serie.id_sarr   
            series_ids.append(id_sarr) 

    return redirect(url_for('inicio_principal',id_pro=id_pro))

#mostrar modal para llenar los series
@app.route('/modal_panel_serie')
def modal_panel_serie(): 
    id_sarr = request.args.get('id_sarr')
    sarr = SerieArreglo.query.get(id_sarr) 
    
    pan = db.session.query(Panel, TecnologiaPanel).join(TecnologiaPanel, Panel.id_tec == TecnologiaPanel.id_tec).filter(Panel.est_pan == 'Habilitado').all()
    pan_ser = SerieArreglo.query.filter_by(id_sarr=id_sarr).first()
    info = db.session.query(Panel, TecnologiaPanel).join(TecnologiaPanel, Panel.id_tec == TecnologiaPanel.id_tec).filter(Panel.id_pan == pan_ser.id_pan).first()
      
    return render_template('creacion_de_proyecto/serie_panel.html', sarr=sarr, pan=pan, info=info)

#editar o añadir los paneles al serie del proyecto
@app.route('/edit_panel', methods=['POST'])
def edit_panel():     
    # Obtiene los valores enviados en el formulario POST
    id_sarr = request.form['id_sarr']
    id_pan = request.form['id_pan']
    
    # Actualiza el valor de id_pan en el registro de SerieArreglo con el id_sarr dado
    serie = SerieArreglo.query.get(id_sarr)
    serie.id_pan = id_pan    
    db.session.commit()
    id_parr = serie.id_parr
    paralelo = ParaleloArreglo.query.get(id_parr)
    id_arr = paralelo.id_arr
    # Realiza una consulta para obtener los resultados necesarios
    results = db.session.query(
        db.func.sum(Panel.vmp_pan) * db.func.min(Panel.imp_pan),
        db.func.sum(Panel.vmp_pan),
        db.func.min(Panel.imp_pan),
        db.func.sum(Panel.are_pan),
        db.func.avg(Panel.efi_pan)
    ).join(SerieArreglo, SerieArreglo.id_pan == Panel.id_pan).join(ParaleloArreglo, ParaleloArreglo.id_parr == SerieArreglo.id_parr).filter(ParaleloArreglo.id_parr == id_parr, Panel.imp_pan!=0).group_by(SerieArreglo.id_parr, ParaleloArreglo.id_arr).first()

    if results:
        pser = results[0]  # El primer valor calculado
        vser = results[1]  # El segundo valor calculado
        iser = results[2]  # El tercer valor calculado
        area = results[3]  # El cuarto valor calculado
        efis = results[4]  # El quinto valor calculado
        
        paralelo = ParaleloArreglo.query.get(id_parr)  # Obtener el registro de ParaleloArreglo por su id_parr
        paralelo.pser_parr = pser
        paralelo.vser_parr = vser
        paralelo.iser_parr = iser
        paralelo.aser_parr = area
        paralelo.efi_parr = efis
        
        db.session.commit()  # Guardar los cambios realizados
        
        result_par = db.session.query(
            db.func.min(ParaleloArreglo.vser_parr) * db.func.sum(ParaleloArreglo.iser_parr),
            db.func.min(ParaleloArreglo.vser_parr),
            db.func.sum(ParaleloArreglo.iser_parr),
            db.func.sum(ParaleloArreglo.aser_parr),
            ParaleloArreglo.id_arr,
            db.func.avg(ParaleloArreglo.efi_parr)
        ).join(ArregloDePaneles, ArregloDePaneles.id_arr == ParaleloArreglo.id_arr).filter(ParaleloArreglo.id_arr == id_arr, ParaleloArreglo.vser_parr!=0).group_by(ParaleloArreglo.id_arr).first()

        if result_par:
            parr = result_par[0]
            vparr = result_par[1]
            iparr = result_par[2]
            area = result_par[3]
            id_arr = result_par[4]
            efip = result_par[5]

            arreglo = ArregloDePaneles.query.get(id_arr)  # Obtener el registro de ArregloDePaneles por su id_arr
            arreglo.ptot_arr = parr
            arreglo.vmax_arr = vparr
            arreglo.imax_arr = iparr
            arreglo.area_arr = area
            arreglo.efi_arr= efip
            db.session.commit()  # Guardar los cambios realizados

            energia=db.session.query(EnergiaArreglo, SensorIrradiancia).join(SensorIrradiancia, EnergiaArreglo.id_sen == SensorIrradiancia.id_sen).filter(EnergiaArreglo.id_pro == arreglo.id_pro).order_by(EnergiaArreglo.id_ene.desc()).all()
            for energiaArreglo, sensorIrradiancia in energia:
                energiaArreglo.tot_ene=((arreglo.ptot_arr*sensorIrradiancia.g_sen)/1000)/1000
                energiaArreglo.efi_ene=sensorIrradiancia.g_sen*100/1000
                db.session.commit()
            return 'success'             
    return 'success' 



#mostrar modal para agregar el dod al banco 
@app.route('/modal_banco_project_dod')
def modal_banco_project_dod(): 
    id_pro = request.args.get('id_pro')
    pro = Proyecto.query.get(id_pro)
    ban=BancoDeBaterias.query.filter_by(id_pro=id_pro).all() 
    for ban in ban:
        id_ban=ban.id_ban
    dod = BancoDeBaterias.query.get(id_ban)
    return render_template('creacion_de_proyecto/project_banco_dod.html', pro = pro,dod=dod )

#editar el dod del banco al proyecto 
@app.route('/dod_banco_project', methods=['POST'])
def dod_banco_project(): 
    id_pro = request.form['id_pro']
    id_ban = request.form['id_ban']
    dod_ban = request.form['dod_ban']
    ban_dod = BancoDeBaterias.query.get(id_ban)  # Obtener el registro de ParaleloBanco por su id_pban
    ban_dod.dod_ban = dod_ban
    db.session.commit()  # Guardar los cambios realizados
    return redirect(url_for('inicio_principal',id_pro=id_pro))

#mostrar modal para agregar el banco alproyecto
@app.route('/modal_banco_project')
def modal_banco_project(): 
    id_pro = request.args.get('id_pro')
    pro = Proyecto.query.get(id_pro)  
    return render_template('creacion_de_proyecto/project_banco.html', pro = pro )

#agregar el banco al proyecto 
@app.route('/add_banco_project', methods=['POST'])
def add_banco_project(): 
    id_pro = request.form['id_pro']
    id_inv = request.form['id_inv']
    num_ser = int(request.form['num_ser'])
    num_bat_ser = int(request.form['num_bat_ser']) 

    banco_nuevo = BancoDeBaterias(id_pro=id_pro,fil_ban=num_ser,col_ban=num_bat_ser)    
    db.session.add(banco_nuevo)
    db.session.commit()
    id_ban = banco_nuevo.id_ban   
    paralelos_ids = []
    series_ids = []    
    for _ in range (num_ser):
        paralelo = ParaleloBanco(id_ban=id_ban)
        db.session.add(paralelo)
        db.session.commit()
        # Obtener el ID del paralelo recién agregado
        id_pban = paralelo.id_pban 
        paralelos_ids.append(id_pban) 
        for _ in range(num_bat_ser):        
            serie = SerieBanco(id_pban=id_pban)
            db.session.add(serie)
            db.session.commit()
            id_sban = serie.id_sban   
            series_ids.append(id_sban) 

    return redirect(url_for('inicio_principal',id_pro=id_pro))

#mostrar modal para llenar los series Bancos
@app.route('/modal_bateria_serie')
def modal_bateria_serie(): 
    id_sban = request.args.get('id_sban')
    sban = SerieBanco.query.get(id_sban) 
    bat = Bateria.query.filter_by(est_bat='Habilitado').all()
    bat_ser = SerieBanco.query.filter_by(id_sban=id_sban).first()
    info = Bateria.query.filter_by(id_bat = bat_ser.id_bat).first()
    return render_template('creacion_de_proyecto/serie_bateria.html', sban=sban, bat=bat, info=info)

#editar o añadir las baterias al serie del proyecto
@app.route('/edit_bateria', methods=['POST'])
def edit_bateria():     
    # Obtiene los valores enviados en el formulario POST
    id_sban = request.form['id_sban']
    id_bat = request.form['id_bat']
    
    # Actualiza el valor de id_bat en el registro de SerieBanco con el id_sbat dado
    serie = SerieBanco.query.get(id_sban)
    serie.id_bat = id_bat    
    db.session.commit()
    id_pban = serie.id_pban
    paralelo = ParaleloBanco.query.get(id_pban)
    id_ban = paralelo.id_ban
    # Consulta para el total de los paralelos
    results = db.session.query(
        db.func.sum(Bateria.vol_bat),
        db.func.avg(Bateria.cap_bat),
        db.func.sum(Bateria.vol_bat) * db.func.avg(Bateria.cap_bat)
    ).join(SerieBanco, SerieBanco.id_bat == Bateria.id_bat).join(ParaleloBanco, ParaleloBanco.id_pban == SerieBanco.id_pban).filter(ParaleloBanco.id_pban == id_pban, Bateria.cap_bat!=0 ).group_by(SerieBanco.id_pban, ParaleloBanco.id_ban).first()
    print(id_pban)
    if results:
        vser = results[0]  # El primer valor calculado
        cser = results[1]  # El segundo valor calculado
        eser = results[2]  # El tercer valor calculado
        
        paralelo = ParaleloBanco.query.get(id_pban)  # Obtener el registro de ParaleloBanco por su id_pban
        paralelo.vser_pban = vser
        paralelo.cser_pban = cser
        paralelo.eser_pban = eser
        print(vser)
        print(cser)
        
        db.session.commit()  # Guardar los cambios realizados
        
        # Consulta para el total del banco
        result_par = db.session.query(
            db.func.min(ParaleloBanco.vser_pban),
            db.func.sum(ParaleloBanco.cser_pban),
            db.func.min(ParaleloBanco.vser_pban) * db.func.sum(ParaleloBanco.cser_pban),
            ParaleloBanco.id_ban
        ).join(BancoDeBaterias, BancoDeBaterias.id_ban == ParaleloBanco.id_ban).filter(ParaleloBanco.id_ban == id_ban, ParaleloBanco.vser_pban!=0).group_by(ParaleloBanco.id_ban).first()
        
        if result_par:
            vpban = result_par[0]
            cpban = result_par[1]
            epban = result_par[2]
            id_ban = result_par[3]

            banco = BancoDeBaterias.query.get(id_ban)  # Obtener el registro de BancoDeBaterias por su id_ban
            banco.vol_ban = vpban
            banco.cap_ban = cpban
            banco.ene_ban = epban
            db.session.commit()  # Guardar los cambios realizados

            return 'success' 

    return 'success' 

#mostrar modal para agregar cargas alproyecto
@app.route('/modal_carga_project')
def modal_carga_project(): 
    id_pro = request.args.get('id_pro')
    pro = Proyecto.query.get(id_pro)     
    return render_template('creacion_de_proyecto/project_carga.html', pro = pro )

# Agregar la carga al proyecto
@app.route('/add_carga_project', methods=['POST'])
def add_carga_project():     
    id_pro = request.form['id_pro']
    lineal = request.form.get('car_lineal')
    inductiva = request.form.get('car_inductiva')
    no_lineal = request.form.get('car_no_lineal')
    if lineal is not None:        
        tip_car = db.session.query(Carga.tip_car).filter_by(id_pro=id_pro,tip_car=lineal).first()
        if tip_car is None:
            add_carga=Carga(id_pro=id_pro,tip_car=lineal)
            db.session.add(add_carga)
    elif lineal is  None:        
        tip_car = Carga.query.filter_by(id_pro=id_pro,tip_car="Lineal").first()
        delete_carga(tip_car)
    if inductiva is not None:        
        tip_car = db.session.query(Carga.tip_car).filter_by(id_pro=id_pro,tip_car=inductiva).first()
        if tip_car is None:
            add_carga=Carga(id_pro=id_pro,tip_car=inductiva)
            db.session.add(add_carga)
    elif inductiva is  None:        
        tip_car = Carga.query.filter_by(id_pro=id_pro,tip_car="Inductiva").first()
        delete_carga(tip_car)    
    if no_lineal is not None:        
        tip_car = db.session.query(Carga.tip_car).filter_by(id_pro=id_pro,tip_car=no_lineal).first()
        if tip_car is None:
            add_carga=Carga(id_pro=id_pro,tip_car=no_lineal)
            db.session.add(add_carga)
    elif no_lineal is None:        
        tip_car = Carga.query.filter_by(id_pro=id_pro,tip_car="No Lineal").first()        
        delete_carga(tip_car)
    db.session.commit()
    
    return redirect(url_for('inicio_principal', id_pro=id_pro))
def delete_carga(tip_car):
    if tip_car is not None:
            db.session.delete(tip_car)

#mostrar modal para llenar las potencias de las cargas
@app.route('/modal_carga_pot')
def modal_carga_pot(): 
    id_car = request.args.get('id_car')
    car = Carga.query.get(id_car)  
    return render_template('creacion_de_proyecto/pot_car.html', car=car)

#editar la potencia de la carga del proyecto
@app.route('/edit_pot_carga', methods=['POST'])
def edit_pot_carga():     
    # Obtiene los valores enviados en el formulario POST
    id_car = request.form['id_car']
    pot_car = request.form['pot_car']
    
    # Actualiza el valor de id_pan en el registro de SerieArreglo con el id_sarr dado
    carga = Carga.query.get(id_car)
    id_pro=carga.id_pro
    carga.pot_car = pot_car    
    db.session.commit()
    return redirect(url_for('inicio_principal', id_pro=id_pro))

#editar perfil
@app.route('/edit_profile')
def edit_profile(): 
    success = request.args.get('success')
    error = request.args.get('error')
    user_id = session.get('user_id')

    if user_id is None:
        # Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('redirigir'))
    
    # Obtener más información del usuario a partir de su ID
    user = db.session.query(Usuario, Roles).join(Roles, Usuario.id_rol == Roles.id_rol).filter(Usuario.id_usu==user_id).first()
    if  success == "1" or error == "2":
            return render_template('autenticacion_y_registro/edit_profile.html',success=success, error=error, user = user )
    else:
        return render_template('autenticacion_y_registro/edit_profile.html', user = user)


#editar perfil guardado
@app.route('/edit_profile_save', methods=['POST'])
def edit_profile_save():         
    id_usu = session.get('user_id')
    cor_usu = request.form['cor_usu']
    password = request.form['con_usu'] 
    try:
        # Actualizar valores del usuario
        usu = Usuario.query.get(id_usu)
        usu.cor_usu = cor_usu 

        if password != "***************":
            # Encriptar la contraseña ingresada con bcrypt
            password_md5 = hashlib.md5(password.encode()).hexdigest()
            usu.con_usu = password_md5

        db.session.commit()
        success='1'                                  
        return redirect(url_for('edit_profile',success=success ))
    except Exception as e:
        db.session.rollback()  # Revertir la transacción en caso de error
        error='2'
        return redirect(url_for('edit_profile', error=error))
            
#list  usuarios
@app.route('/update_user')
def update_user():
    success = request.args.get('success')
    error = request.args.get('error')
    user_id = session.get('user_id')
    if user_id is None:
        # Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('redirigir'))   
    # Obtener más información del usuario a partir de su ID
    user = Usuario.query.get(user_id)
    if user.per_usu== 'Administrador':
        rol = Roles.query.all()
        #Obtiene todos los componentes registrados con ese respectivo id de 
        edit_usu= db.session.query(Usuario, Roles).join(Roles, Usuario.id_rol == Roles.id_rol).all()
        if success == "1" or error == "2":
            return render_template('autenticacion_y_registro/edit_user.html',success=success, error=error,rol=rol, edit_usu=edit_usu)
        else:
            return render_template('autenticacion_y_registro/edit_user.html',rol=rol, edit_usu=edit_usu)
    else:
        return redirect(url_for('inicio_principal'))

#guardar el actualizado del usuario
@app.route('/update_usuario_save', methods=['POST'])
def update_usuario_save(): 
    user_id = session.get('user_id')
    id_usu = int(request.form['id_usu'])
    nom_usu = request.form['nom_usu']
    ape_usu = request.form['ape_usu']
    per_usu = request.form['per_usu']
    doc_usu = request.form['doc_usu']
    id_rol = request.form['rol_usu']
    usuario = Usuario.query.get(id_usu)

    if id_usu != user_id:
        usuario.per_usu = per_usu
        
    usuario.nom_usu = nom_usu    
    usuario.ape_usu = ape_usu    
    usuario.doc_usu = doc_usu
    usuario.id_rol = id_rol
    # Guardar cambios del usuario a la base de datos
    db.session.commit() 
    success='1'                                  
    return redirect(url_for('update_user',success=success ))
    

#list  paneles
@app.route('/update_panel')
def update_panel(): 
    success = request.args.get('success')
    error = request.args.get('error')
    user_id = session.get('user_id')
    if user_id is None:
        # Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('redirigir'))    
    # Obtener más información del usuario a partir de su ID
    user = Usuario.query.get(user_id)
    if user.per_usu== 'Administrador':
        tecno = TecnologiaPanel.query.all()
        #Obtiene todos los componentes registrados con ese respectivo id de 
        pan_usu = db.session.query(Panel, TecnologiaPanel).join(TecnologiaPanel, Panel.id_tec == TecnologiaPanel.id_tec).all()
        if success == "1" or error == "2":
            return render_template('creacion_de_componentes/editar_panel.html',success=success, error=error,tecno=tecno, user_comp = user, pan_usu =pan_usu )
        else:
            return render_template('creacion_de_componentes/editar_panel.html',tecno=tecno, user_comp = user, pan_usu =pan_usu )
    else:
        return redirect(url_for('inicio_principal'))

#guardar elactualizado del panel
@app.route('/update_panel_save', methods=['POST'])
def update_panel_save(): 
    id_pan = request.form['id_pan']
    ref_pan = request.form['ref_pan']
    est_pan = request.form['est_pan']
    pmax_pan = float(request.form['pmax_pan'])  # Convierte los valores a números flotantes
    vmp_pan = float(request.form['vmp_pan'])
    imp_pan = float(request.form['imp_pan'])
    voc_pan = float(request.form['voc_pan'])
    isc_pan = float(request.form['isc_pan'])
    lar_pan = float(request.form['lar_pan'])
    anc_pan = float(request.form['anc_pan'])
    are_pan = lar_pan * anc_pan
    nom_tec = request.form['tec_pan']
    den_pan = pmax_pan / are_pan
    user_id = session.get('user_id')

    #Si el panel deshabilitado no esta en ningun proyecto eliminarlo definitivamente
    proyecto_panel=SerieArreglo.query.filter_by(id_pan=id_pan).all()
    #Obtener más información del panel a partir de su ID   
    id_pan_del = Panel.query.get(id_pan)  
    if proyecto_panel :        
        panel = Panel.query.get(id_pan) 
        panel.est_pan = est_pan
        # Guardar cambios del panel a la base de datos
        db.session.commit() 
    elif est_pan == 'Deshabilitado':               
        db.session.delete(id_pan_del)  # Elimina el panel de la base de datos
        db.session.commit()  # Confirma los cambios en la base de datos  

    panel = Panel.query.get(id_pan)     
    if panel:
        tecno = TecnologiaPanel.query.filter_by(nom_tec=nom_tec).first()
        pmax_cal_pan = vmp_pan * imp_pan
        if tecno is None:
            tecnologia_panel = TecnologiaPanel(nom_tec=nom_tec)
            db.session.add(tecnologia_panel)
            db.session.commit()
            id_tec = tecnologia_panel.id_tec
        else:
            id_tec = tecno.id_tec

        if pmax_cal_pan > pmax_pan - 0.5 and pmax_cal_pan < pmax_pan + 0.5:
            panel = Panel.query.get(id_pan)  # Obtener el registro de Panel por su id_pan
            panel.ref_pan = ref_pan
            panel.pmax_pan = pmax_pan
            panel.vmp_pan = vmp_pan
            panel.imp_pan = imp_pan
            panel.voc_pan = voc_pan
            panel.isc_pan = isc_pan
            panel.lar_pan = lar_pan
            panel.anc_pan = anc_pan
            panel.id_tec = id_tec
            panel.den_pan = den_pan
            panel.est_pan = est_pan
            panel.id_usu = user_id
            # Guardar cambios del panel a la base de datos
            db.session.commit() 
            success='1'                                 
            return redirect(url_for('update_panel',success=success ))
        else:
            error='2'
            return redirect(url_for('update_panel', error=error))
            
    return redirect(url_for('update_panel'))
    


#list  baterias
@app.route('/update_bateria')
def update_bateria(): 
    success = request.args.get('success')
    user_id = session.get('user_id')
    if user_id is None:
        # Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('redirigir'))
    # Obtener más información del usuario a partir de su ID
    user = Usuario.query.get(user_id)
    if user.per_usu== 'Administrador':
        #Obtiene todos los componentes registrados con ese respectivo id de usurio
        bat_usu = Bateria.query.all()
        return render_template('creacion_de_componentes/editar_bateria.html', success=success, user_comp = user, bat_usu =bat_usu )
    else:
        return redirect(url_for('inicio_principal'))

#guardar el actualizado del bateria
@app.route('/update_bateria_save', methods=['POST'])
def update_bateria_save(): 
    id_bat = request.form['id_bat']
    ref_bat = request.form['ref_bat']
    vol_bat = float(request.form['vol_bat'])
    cap_bat = float(request.form['cap_bat'])
    ene_bat = vol_bat*cap_bat
    est_bat = request.form['est_bat']
    user_id = session.get('user_id')
    
    #Si la bateria deshabilitada no esta en ningun proyecto eliminarlo definitivamente
    proyecto_bateria=SerieBanco.query.filter_by(id_bat=id_bat).all()#AUN TE FALTA ORGANIZAR MODELS.PY
    #Obtener más información de la bateria a partir de su ID   
    id_bat_del = Bateria.query.get(id_bat)  
    if proyecto_bateria :
        bateria = Bateria.query.get(id_bat)  # Obtener el registro de bateria por su id_pan
        bateria.est_bat = est_bat
        # Guardar cambios del bateria a la base de datos
        db.session.commit()
    elif est_bat == 'Deshabilitado':                    
        db.session.delete(id_bat_del)  # Elimina la bateria de la base de datos
        db.session.commit()  # Confirma los cambios en la base de datos        

    bateria = Bateria.query.get(id_bat) 
    if bateria :
        bateria = Bateria.query.get(id_bat)  # Obtener el registro de bateria por su id_pan
        bateria.ref_bat = ref_bat    
        bateria.vol_bat = vol_bat
        bateria.cap_bat = cap_bat
        bateria.ene_bat = ene_bat
        bateria.id_usu = user_id
        # Guardar cambios del bateria a la base de datos
        db.session.commit() 
        success='1'                                  
        return redirect(url_for('update_bateria',success=success ))   

    
    return redirect(url_for('update_bateria'))
    

        
    
#list  inversores
@app.route('/update_inversor')
def update_inversor():     
    success = request.args.get('success')
    error = request.args.get('error')
    user_id = session.get('user_id')
    if user_id is None:
        # Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('redirigir'))
    # Obtener más información del usuario a partir de su ID
    user = Usuario.query.get(user_id)
    if user.per_usu== 'Administrador':
        #Obtiene todos los componentes registrados con ese respectivo id de usurio
        inv_usu = Inversor.query.all()
        return render_template('creacion_de_componentes/editar_inversor.html',error=error, success=success, user_comp = user, inv_usu = inv_usu )
    else:
        return redirect(url_for('inicio_principal'))

#guardar el actualizado del inversor
@app.route('/update_inversor_save', methods=['POST'])
def update_inversor_save(): 
    id_inv = request.form['id_inv']
    ref_inv = request.form['ref_inv']
    est_inv = request.form['est_inv']
    ent_inv = request.form['ent_inv']
    pmax_inv = float(request.form['pmax_inv'])  # Convierte los valores a números flotantes
    vme_inv = float(request.form['vme_inv'])
    ime_inv = float(request.form['ime_inv'])
    vsa_inv = float(request.form['vsa_inv'])
    ond_inv = request.form['ond_inv']
    efi_inv = float(request.form['efi_inv'])
    user_id = session.get('user_id')
    
    
    #Si el inversor deshabilitado no esta en ningun proyecto eliminarlo definitivamente  
    proyecto_inversor=Proyecto.query.filter_by(id_inv=id_inv).all()    
    id_inv_del = Inversor.query.get(id_inv)  
    if proyecto_inversor :
        inversor = Inversor.query.get(id_inv)  # Obtener el registro de inversor por su id_pan              
        inversor.est_inv = est_inv
    elif est_inv == 'Deshabilitado':               
        db.session.delete(id_inv_del)  # Elimina el inversor de la base de datos
        db.session.commit()  # Confirma los cambios en la base de datos
    
    inversor = Inversor.query.get(id_inv)     
    if inversor:
        pmax_cal_inv= vme_inv * ime_inv
        if pmax_cal_inv > pmax_inv - 0.6 and pmax_cal_inv < pmax_inv + 0.6:
            inversor = Inversor.query.get(id_inv)  # Obtener el registro de inversor por su id_pan              
            inversor.ref_inv = ref_inv  
            inversor.ent_inv = ent_inv
            inversor.pmax_inv = pmax_inv
            inversor.vme_inv = vme_inv
            inversor.ime_inv = ime_inv
            inversor.vsa_inv = vsa_inv
            inversor.ond_inv = ond_inv
            inversor.efi_inv = efi_inv
            inversor.id_usu = user_id
            # Guardar cambios del inversor a la base de datos
            db.session.commit() 
            success='1'         
            return redirect(url_for('update_inversor',success=success ))
        else:
            error='2'
            return redirect(url_for('update_inversor', error=error))    
    return redirect(url_for('update_inversor'))    

#list_project
@app.route('/list_project')
def list_project(): 
    buscar = request.args.get('buscar')
    print(buscar)
    success = request.args.get('success')
    error = request.args.get('error')
    user_id = session.get('user_id')

    if user_id is None:
        # Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('redirigir'))
    
    # Obtener más información del usuario a partir de su ID
    user = Usuario.query.get(user_id)
    if buscar is not None :
        pro_list = (
            db.session.query(
                Proyecto.id_pro,
                Proyecto.nom_pro,
                Proyecto.id_inv,
                Proyecto.fec_pro,
                db.sql.expression.func.avg(ArregloDePaneles.ptot_arr).label('arr'),
                db.sql.expression.func.avg(BancoDeBaterias.ene_ban).label('ban')
            )
            .outerjoin(ArregloDePaneles, Proyecto.id_pro == ArregloDePaneles.id_pro)
            .outerjoin(BancoDeBaterias, BancoDeBaterias.id_pro == Proyecto.id_pro)
            .filter(Proyecto.id_usu == user_id,Proyecto.est_pro== 'Habilitado', Proyecto.nom_pro.ilike(f"%{buscar}%"))
            .group_by(Proyecto.id_pro,Proyecto.nom_pro, Proyecto.id_inv, Proyecto.fec_pro, BancoDeBaterias.ene_ban).order_by(desc(Proyecto.fec_pro))
            .all()
        )
        return render_template('creacion_de_proyecto/search_project.html', user=user, pro_list=pro_list)
    else:
        pro_list = (
            db.session.query(
                Proyecto.id_pro,
                Proyecto.nom_pro,
                Proyecto.id_inv,
                Proyecto.fec_pro,
                db.sql.expression.func.avg(ArregloDePaneles.ptot_arr).label('arr'),
                db.sql.expression.func.avg(BancoDeBaterias.ene_ban).label('ban')
            )
            .outerjoin(ArregloDePaneles, Proyecto.id_pro == ArregloDePaneles.id_pro)
            .outerjoin(BancoDeBaterias, BancoDeBaterias.id_pro == Proyecto.id_pro)
            .filter(Proyecto.id_usu == user_id, Proyecto.est_pro== 'Habilitado',)
            .group_by(Proyecto.id_pro,Proyecto.nom_pro, Proyecto.id_inv, Proyecto.fec_pro, BancoDeBaterias.ene_ban).order_by(desc(Proyecto.fec_pro))
            .all()
        )

    if  success == "1" or error == "2":
        return render_template('creacion_de_proyecto/list_project.html',success=success, error=error, user = user, pro_list= pro_list)
    else:
        return render_template('creacion_de_proyecto/list_project.html', user = user, pro_list=pro_list)

#delete_project
@app.route('/delete_project')
def delete_project(): 
    id_pro = request.args.get('id_pro')
    proyecto=Proyecto.query.get(id_pro) 
    proyecto.est_pro = 'Deshabilitado'
    # Guardar cambios del inversor a la base de datos
    db.session.commit() 
    return redirect(url_for('list_project')) 


#Funcion para eliminar un arreglo
def delete_arr(id_arr):
    # Elimina las filas en serie_arreglo relacionadas con el último arreglo
    series_a_eliminar = SerieArreglo.query.join(ParaleloArreglo, ParaleloArreglo.id_parr == SerieArreglo.id_parr).filter(ParaleloArreglo.id_arr == id_arr).all()
    for serie in series_a_eliminar:
        db.session.delete(serie)
    db.session.commit()   
    
    # Elimina las filas en paralelo_arreglo relacionadas con el último arreglo
    paralelos_a_eliminar = ParaleloArreglo.query.filter_by(id_arr=id_arr).all()
    for paralelo in paralelos_a_eliminar:
        db.session.delete(paralelo)
    db.session.commit()
    
    # Elimina el último arreglo
    arreglo_a_eliminar = ArregloDePaneles.query.filter_by(id_arr=id_arr).first()
    if arreglo_a_eliminar is not None:
        db.session.delete(arreglo_a_eliminar)
    db.session.commit()

#mostrar modal eliminar arreglo de proyecto
@app.route('/ver_modal_del_arr')
def ver_modal_del_arr():
    id_arr = request.args.get('id_arr')
    id_arr_del = request.args.get('id_arr_del')
    if id_arr_del is not None:
        arr=ArregloDePaneles.query.get(id_arr_del)
        id_pro=arr.id_pro
        delete_arr(id_arr_del)
        return redirect(url_for('inicio_principal',id_pro=id_pro))
    else:
        arr=ArregloDePaneles.query.get(id_arr)
        return render_template('creacion_de_proyecto/delete_arreglo_project.html', arr=arr)

#mostrar modal eliminar banco de proyecto
@app.route('/ver_modal_del_ban')
def ver_modal_del_ban():
    id_ban = request.args.get('id_ban')
    id_ban_del = request.args.get('id_ban_del')
    if id_ban_del is not None:
        ban=BancoDeBaterias.query.get(id_ban_del)
        id_pro=ban.id_pro
        # Elimina las filas en serie_banco relacionadas con el último banco
        series_a_eliminar = SerieBanco.query.join(ParaleloBanco, ParaleloBanco.id_pban == SerieBanco.id_pban).filter(ParaleloBanco.id_ban == id_ban_del).all()
        for serie in series_a_eliminar:
            db.session.delete(serie)
        db.session.commit()   
        
        # Elimina las filas en paralelo_banco relacionadas con el último banco
        paralelos_a_eliminar = ParaleloBanco.query.filter_by(id_ban=id_ban_del).all()
        for paralelo in paralelos_a_eliminar:
            db.session.delete(paralelo)
        db.session.commit()
        
        # Elimina el último banco
        banco_a_eliminar = BancoDeBaterias.query.filter_by(id_ban=id_ban_del).first()
        if banco_a_eliminar is not None:
            db.session.delete(banco_a_eliminar)
        db.session.commit()
        return redirect(url_for('inicio_principal',id_pro=id_pro))
    else:
        ban=BancoDeBaterias.query.get(id_ban)
        return render_template('creacion_de_proyecto/delete_banco_project.html', ban=ban)

# Dictionary to store stop events for each project
stop_events_dict = {}

def encontrar_puerto_arduino():
    # Encuentra el puerto COM al que está conectado Arduino.
    puertos_disponibles = list(serial.tools.list_ports.comports())
    
    for puerto in puertos_disponibles:
        if 'Arduino' in puerto.description:
            return puerto.device
    
    return None

# datos sensor
@app.route('/datos_sensor', methods=['POST'])
def datos_sensor():
    id_pro = request.form['id_pro']
    eje_pro = request.form['eje_pro']

    #Comprobar si el evento de detención existe para el proyecto actual
    if id_pro not in stop_events_dict:
        stop_events_dict[id_pro] = threading.Event()

    stop_event = stop_events_dict[id_pro]

    ene_arr_tot = db.session.query(db.func.sum(ArregloDePaneles.ptot_arr)).filter_by(id_pro=id_pro).scalar()
    efi_arr_tot = db.session.query(db.func.avg(ArregloDePaneles.efi_arr)).filter_by(id_pro=id_pro).scalar()
    ref_sen = request.form['ref_sen']

    puerto_arduino = encontrar_puerto_arduino()
    print(puerto_arduino)
    pro=Proyecto.query.get(id_pro)
    pro.eje_pro=eje_pro
    db.session.commit()
    if eje_pro == "F":
        stop_event.clear()  # Borrar el evento para permitir que el ciclo continúe
    elif eje_pro == "T":
        stop_event.set()  # Configurar el evento para detener el bucle    
    if not puerto_arduino:
        pro=Proyecto.query.get(id_pro)
        pro.eje_pro="F"
        db.session.commit()
        stop_event.clear()
    thread = threading.Thread(target=procesar_datos, args=(id_pro, ref_sen,puerto_arduino,  ene_arr_tot, efi_arr_tot, stop_event))
    thread.start()

    return redirect(url_for('inicio_principal', id_pro=id_pro))

def ejecutar_programa_arduino(puerto_serial, codigo_arduino):
    try:
        # Abre el puerto serial
        with serial.Serial(puerto_serial, 9600, timeout=5) as ser:
            # Espera a que el Arduino esté listo
            time.sleep(2)

            # Envía el código del programa Arduino línea por línea
            for linea in codigo_arduino:
                ser.write(linea.encode())
                ser.write(b'\n')  # Agrega un salto de línea al final de cada línea

            print("Código enviado al Arduino")

    except serial.SerialException as e:
        print(f"Error al abrir el puerto serial: {e}")
def procesar_datos(id_pro, ref_sen,puerto_arduino,  ene_arr_tot, efi_arr_tot, stop_event):
    with app.app_context():         
        try:
            # Cargar el contenido del archivo .ino
            ruta_arduino = r"energia_renovable\sensores\Apogeesp110ss\Apogeesp110ss.ino"
            with open(ruta_arduino, "r") as file:
                codigo_arduino = file.readlines()

            # Ejecutar el programa de Arduino
            ejecutar_programa_arduino(puerto_arduino, codigo_arduino)

            # Continuar con el resto del código
            ser = serial.Serial(puerto_arduino, 9600)
        except serial.SerialException as e:
            pro = Proyecto.query.get(id_pro)
            pro.eje_pro = "F"
            db.session.commit()
            stop_event.clear()
            return
        time.sleep(2)

        while stop_event.is_set():
            # Leer los datos como bytes directamente
            g_sen_bytes = ser.readline()
            
            try:
                # Convertir los datos a un número flotante
                g_sen = float(g_sen_bytes.strip())
                print(g_sen)
                fec_sen=datetime.now() #hagamos de cueta que tenmos esos valores que nos esta dando el sensor (fecha)
                print(ref_sen)   

                print(id_pro)    
                datos_g = SensorIrradiancia(fec_sen=fec_sen, g_sen=g_sen, ref_sen=ref_sen)
                # Agregar los datos del sensor
                db.session.add(datos_g)
                db.session.commit()
                # Obtener el ID del sensor irradiancia recién agregado
                id_sen = datos_g.id_sen             
                print(id_sen)

                efi_ene=efi_arr_tot
                print(efi_ene)  
                arr_tot=(ene_arr_tot*efi_arr_tot/100)+ene_arr_tot
                tot_ene_kw=((arr_tot*g_sen)/1000)/1000
                print(tot_ene_kw)
                print(tot_ene_kw*1000)

                # Imprimir arreglo energia la eficiaencia  y el arreglo con la eficiencia
                print("Imprimir arreglo energia la eficiaencia  y el arreglo con la eficiencia")
                print(ene_arr_tot)
                print(efi_arr_tot)
                print(arr_tot)

                ene_arr = EnergiaArreglo(efi_ene=efi_ene, tot_ene=tot_ene_kw, id_pro=id_pro,id_sen=id_sen,fec_ene=fec_sen)
                # Agregar los datos del sensor
                db.session.add(ene_arr)
                db.session.commit()

            except ValueError:
                print("No se pudo convertir a float. Datos recibidos:", g_sen_bytes)

            time.sleep(1)

        ser.close()


@app.route('/get_latest_data/<id_pro>')
def get_latest_data(id_pro):
    query_result = db.session.query(EnergiaArreglo, SensorIrradiancia).join(SensorIrradiancia, EnergiaArreglo.id_sen == SensorIrradiancia.id_sen).filter(EnergiaArreglo.id_pro == id_pro).order_by(EnergiaArreglo.id_ene.desc()).first()
    if query_result:
        # Desempaquetar los resultados de la consulta
        energia_arreglo, sensor_irradiancia = query_result
        data = {
            'ref_sen': sensor_irradiancia.ref_sen,
            'g_sen': sensor_irradiancia.g_sen,
            'efi_ene': energia_arreglo.efi_ene,
            'tot_ene': energia_arreglo.tot_ene,
            'fec_ene': energia_arreglo.fec_ene,
        }
        return data
    else:
        return None

#informes
@app.route('/informes')
def informes():
    user_id = session.get('user_id')
    if user_id is None:
        # Si el usuario no ha iniciado sesión, redirigir a la página de inicio de sesión
        return redirect(url_for('redirigir'))   
    # Obtener más información del usuario a partir de su ID
    user = Usuario.query.get(user_id)
    
    # Consultar todos los proyectos con resultados obtimos
    proyectos = (
        db.session.query(
            Proyecto.id_pro,
            Proyecto.nom_pro,
            Proyecto.fec_pro,
            db.func.max(SensorIrradiancia.fec_sen).label('fec_sen'),
            db.func.max(SensorIrradiancia.g_sen).label('g'),
            db.func.max(EnergiaArreglo.efi_ene).label('eficiencia'),
            (db.func.max(EnergiaArreglo.tot_ene) * 1000).label('energia_w'),
            db.func.max(EnergiaArreglo.tot_ene).label('energia_kw')
        )
        .join(EnergiaArreglo, EnergiaArreglo.id_pro == Proyecto.id_pro)
        .join(SensorIrradiancia, SensorIrradiancia.id_sen == EnergiaArreglo.id_sen)
        .group_by(Proyecto.id_pro,Proyecto.nom_pro, Proyecto.fec_pro)
        .order_by(db.func.max(SensorIrradiancia.g_sen).desc())
        .all()
    )
    conteo_por_mes = (
        db.session.query(
            db.func.count(Proyecto.id_pro).label('conteo'),
            db.func.DATE_TRUNC('month', Proyecto.fec_pro).label('fecha_mes')
        )
        .filter(Proyecto.fec_pro < dt.datetime.now())
        .group_by(db.func.DATE_TRUNC('month', Proyecto.fec_pro))
        .order_by(db.func.DATE_TRUNC('month', Proyecto.fec_pro))
        .all()
    )
    if user.per_usu== 'Administrador':
        return render_template('informe_y_Estadistica/informe.html',proyectos=proyectos,conteo_por_mes=conteo_por_mes)
    else:
        return redirect(url_for('inicio_principal'))

#Datos recolestados de la davis
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

    try:
        # Envía una solicitud HTTP GET
        response = requests.get(url, headers=headers)

        # Verifica si la respuesta fue exitosa (código de estado 200)
        if response.status_code == 200:
            data = response.json()

            if isinstance(data['sensors'], list):
                irradiance_data = [] 
                for sensor_data in data['sensors']:
                    if isinstance(sensor_data['data'], list):
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
                            context = {'irradiance_data': irradiance_data}
                                                
            return render_template('informe_y_Estadistica/date_davis.html', **context)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return f"Error: {e}"  # Devuelve un mensaje de error a la página web


if __name__ == '__main__':
    app.run(debug=True)
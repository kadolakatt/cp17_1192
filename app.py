import os
import functools
import yagmail as yagmail

from werkzeug.utils import redirect
from flask import Flask, request, jsonify, url_for, g, session
from flask.templating import render_template
from forms import FormContactanos, FormRespuesta, FormLogin, FormRegistro

#Importamos la clase mensaje y usuario de nuestro modulo models
from models import mensaje, usuario

app = Flask(__name__)

app.config['SECRET_KEY'] = "82bfaf357a4dae474edcf60317a44bdb4dc61444f81204f9e3b53f302547fde2" #os.urandom(32)

#Decorador para verificar que el usuario es autenticado
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect( url_for('login') )

        return view(**kwargs)

    return wrapped_view

@app.before_request
def cargar_usuario_autenticado():
    nombre_usuario = session.get('nombre_usuario')
    if nombre_usuario is None:
        g.user = None
    else:
        g.user = usuario.cargar(nombre_usuario)


#INICIO - Funciones CP10
@app.route('/')
def index():
    return render_template('layout.html')

@app.route("/registro/", methods=["GET", "POST"])
def registro():
    if request.method == "GET":
        formulario = FormRegistro()
        return render_template('registro.html', form=formulario)
    else:
        formulario = FormRegistro(request.form)
        if formulario.validate_on_submit():
            obj_usuario = usuario(formulario.nombre.data, formulario.usuario.data,formulario.correo.data, formulario.contrasena.data)
            if obj_usuario.insertar():
                #Aqui podrias agregar más adelante un código para enviar correo electrónico al usuario
                #y que pueda activar su cuenta.
                return render_template('registro.html', mensaje="Se registró el usuario exitosamente.", form=FormRegistro())

        return render_template('registro.html', mensaje="Todos los datos son obligatorios.", form=formulario)

@app.route("/logout/")
@login_required
def logout():
    session.clear()
    return redirect( url_for('login') )

@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method=="GET":
        return render_template('login.html', form=FormLogin())
    else:
        #Codigo Obsoleto por implementación de WTforms
        #usr = request.form["usuario"]
        #pwd = request.form["contrasena"]

        formulario = FormLogin(request.form)

        usr = formulario.usuario.data.replace("'","")
        pwd = formulario.contrasena.data.replace("'","")

        obj_usuario = usuario('',usr,'',pwd)
        if obj_usuario.autenticar():
            session.clear()
            session["nombre_usuario"] = usr
            return redirect( url_for('get_listado_mensajes'))
        
        return render_template('login.html', mensaje="Nombre de usuario o contraseña incorrecta.", 
        form=formulario)

@app.route('/contactanos/', methods=["GET", "POST"])
@login_required
def contactanos():
    if request.method == "GET":

        formulario = FormContactanos()
        return render_template('contactanos.html', form=formulario)

    else:
        formulario = FormContactanos(request.form)
        if formulario.validate_on_submit():
            
            #Instanciamos la clase mensaje con los datos 
            #del formulario que se reciben de la petición
            objeto_mensaje = mensaje(0, formulario.nombre.data,
            formulario.correo.data, formulario.mensaje.data, None, 'S')

            #Invocamos el método insertar para guardar el mensaje en bd
            if objeto_mensaje.insertar():
                yag = yagmail.SMTP('alertasmisiontic2022@gmail.com','prueba123')
                yag.send(to=formulario.correo.data,subject="Su mensaje ha sido recibido.",
                        contents="Hola {0}, hemos recibido tu mensaje. En breve nos comunicaremos contigo.".format(formulario.nombre.data))
                return render_template('contactanos.html',mensaje="Su mensaje ha sido enviado.", form=FormContactanos())
            else:
                return render_template('contactanos.html', mensaje="Ocurrió un error al guardar el formulario, por favor intente nuevamente.", form=formulario)        

        return render_template('contactanos.html', mensaje="Todos los campos son obligatorios.", form=formulario)
#FIN - Funciones CP10

#INICIO - Funciones CP11
@app.route('/api/mensajes/listado',methods=["GET"])
@login_required
def get_mensajes_json():
    #Retornamos el json con el listado de mensajes en la bd
    return jsonify(mensaje.listado())


@app.route('/api/mensajes/ver/<id>', methods=["GET"])
@login_required
def get_mensaje_json(id):

    objeto_mensaje = mensaje.cargar(id)
    if objeto_mensaje:
        return jsonify(objeto_mensaje)
    
    return jsonify({ "error":"No se encontró el mensaje con el id especificado." })


@app.route('/mensajes/listado/', methods=["GET"])
@login_required
def get_listado_mensajes():
    return render_template('listado_mensajes.html', lista=mensaje.listado())

#Devuelme el listado con paginacion sencilla
@app.route('/mensajes/listado/paginado/', methods=["GET"])
@login_required
def get_listado_mensajes_pag():
    #Obtenemos del querystring de la URL los parametros page y size
    page = request.args.get('page', type=int, default=1)
    size = request.args.get('size', type=int, default=20)
    #Creamos un dict con los valores 
    pagination = {"page": page, "size": size}

    #Obtenemos los registros a mostrar en la pagina
    lista_mensajes = mensaje.listado_paginado(size, page)

    #Retornamos render template del listado paginado
    return render_template('listado_mensajes_paginado.html', lista=lista_mensajes, pagination=pagination)

@app.route('/mensajes/ver/<id>', methods=["GET"])
@login_required
def get_mensaje(id):
    objeto_mensaje = mensaje.cargar(id)
    if objeto_mensaje:
        return render_template('ver_mensaje.html',item=objeto_mensaje)
    
    return render_template('ver_mensaje.html')


@app.route('/mensajes/respuesta/<id_mensaje>', methods=["GET", "POST"])
@login_required
def responder_mensaje(id_mensaje):
    if request.method == "GET":
        formulario = FormRespuesta()

        objeto_mensaje = mensaje.cargar(id_mensaje)
        if objeto_mensaje:
            formulario.nombre.data = objeto_mensaje.nombre
            formulario.correo.data = objeto_mensaje.correo
            formulario.mensaje_original.data = objeto_mensaje.mensaje
            return render_template('responder_mensaje.html',id=id_mensaje, form = formulario)
        
        return render_template('responder_mensaje.html',id=id_mensaje, mensaje="No se encontró un mensaje para el id especificado.")

    else:
        formulario = FormRespuesta(request.form)
        if formulario.validate_on_submit():
            
            objeto_mensaje = mensaje.cargar(id_mensaje)
            objeto_mensaje.respuesta = formulario.respuesta.data
            if objeto_mensaje.responder():
                yag = yagmail.SMTP('alertasmisiontic2022@gmail.com','prueba123')
                yag.send(to=formulario.correo.data,subject="Su mensaje ha sido respondido.",
                        contents="Hola {0}. La respuesta a tu mensaje: {1} es: {2}."
                        .format(formulario.nombre.data, formulario.mensaje_original.data, formulario.respuesta.data))
                return render_template('responder_mensaje.html',id=id_mensaje, mensaje="Su respuesta ha sido enviada.")
            else:
                return render_template('responder_mensaje.html',id=id_mensaje, form=formulario, 
                mensaje="No se pudo actualizar el mensaje en la base de datos. Por favor intentelo nuevamente.")

        return render_template('responder_mensaje.html',id=id_mensaje, form=formulario, mensaje="Todos los datos son obligatorios.")
#FIN - Funciones CP11
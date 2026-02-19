import os
from django.shortcuts import render, redirect
from django.contrib import messages
# from django.http import  HttpRequestForbidden
from firebase_admin import firestore, auth
from config.firebaseConnection import initialize_firebase
from functools import wraps
import requests

# Inicializar la DB con FireStore

db = initialize_firebase()

def bienvenido(request):
    return render(request, 'bienvenido.html')

def registro_usuario(request):
    mensaje = None
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            # Vamos a crear en Firebase auth
            user = auth.create_user(
                email = email,
                password = password
            )

            # Crear en Firestore

            db.collection('gerentes').document(user.uid).set({
                'email' : email,
                'uid' : user.uid,
                'rol' : 'Gerente',
                'fecha_registro' : firestore.SERVER_TIMESTAMP,
            })

            mensaje = f"Usuario registrado correctamente con el UID: {user.uid}"
        except Exception as e:
            mensaje = f"Error: {e}"
    return render(request, 'registro.html', {'mensaje' : mensaje})

def login_required_firebase(view_func):
    # Este decorador personalizado va a proteger nuestras vistas
    # si el usuario no ha iniciado sesión.
    # Si el UID no existe, lo va a enviar a iniciar sesión.

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'uid' not in request.session:
            messages.warning(request, "Warning, no has iniciado sesión")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# logica para solicitarle a Google la validación

def cerrar_sesion(request):
    request.session.flush()
    messages.info(request, 'Has cerrado sesión correctamente')
    return redirect('login')

#listar productos
@login_required_firebase
def listar_productos(request):
    """
    READ: Recuperar los productos del usuario desde firestore
    """

    uid = request.session.get('uid')
    productos = []

    try:
        #Vamos a filtrar los productos que registro del usuario

        docs = db.collection('productos').where('usuario_id', '==', uid).stream()
        for doc in docs:
            producto = doc.to_dict()
            producto['id'] = doc.id
            productos.append(producto)
    except Exception as e:
        messages.error(request, f"Hubo un error al obtener los productos {e}")
    
    return render(request, 'productos/listar.html', {'productos' : productos})


@login_required_firebase # Verifica que el usuario esta loggeado
def editar_producto(request, producto_id):
    """
    UPDATE: Recupera los datos del producto especifico y actualiza los campos en firebase
    """
    uid = request.session.get('uid')
    producto_ref = db.collection('productos').document(producto_id)

    try:
        doc = producto_ref.get()

        if not doc.exists:
            messages.error(request, "El producto no existe")
            return redirect('listar_productos')
        
        producto_data = doc.to_dict()

        if producto_data.get('usuario_id') != uid:
            messages.error(request, "No tienes permiso para editar este producto")
            return redirect('listar_productos')
        
        if request.method == 'POST':
            nuevo_titulo = request.POST.get('nombre_producto')
            nueva_desc = request.POST.get('descripcion')
            nueva_cantidad = request.POST.get('cantidad')

            producto_ref.update({
                'nombre_producto': nuevo_titulo,
                'descripcion': nueva_desc,
                'estado': nueva_cantidad,
                'fecha_actualizacion': firestore.SERVER_TIMESTAMP
            })

            messages.success(request, "✅ producto actualizado correctamente.")
            return redirect('listar_productos')
    except Exception as e:
        messages.error(request, f"Error al editar el producto: {e}")
        return redirect('listar_productos')
    
    return render(request, 'productos/editar.html', {'producto': producto_data, 'id': producto_id})
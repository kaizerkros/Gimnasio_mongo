
#main.py - Programa principal de gestión del gimnasio
#Sistema CRUD completo con menú interactivo por consola

import sys
import os
import re
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from bson import ObjectId
from bson.json_util import dumps
import traceback
print("Iniciando main.py...")
print("Importando módulos... OK")

PRECIOS_MEMBRESIAS = {
    "basica": 30000.0,
    "premium": 45000.0,
    "vip": 55000.0,
}


def connect_to_mongodb(uri="mongodb://localhost:27017/"):
    """
    Establece conexión con MongoDB.
    
    Args:
        uri (str): URI de conexión a MongoDB
    
    Returns:
        MongoClient | None: Cliente de MongoDB o None si falla la conexión
    """
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("[OK] Conexion exitosa a MongoDB")
        return client
    except ConnectionFailure as e:
        print(f"[ERROR] Error de conexion a MongoDB: {e}")
        print("   Asegurate de que MongoDB este ejecutandose en localhost:27017")
        return None
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        return None



def format_document(doc):
    """
    Formatea un documento para mostrarlo de forma legible.
    
    Args:
        doc (dict): Documento de MongoDB
    
    Returns:
        str: Representación formateada del documento
    """
    if not doc:
        return "Documento no encontrado"
    
    # Convertir ObjectId a string para mostrarlo
    doc_copy = doc.copy()
    if '_id' in doc_copy:
        doc_copy['_id'] = str(doc_copy['_id'])
    
    lines = []
    lines.append("=" * 70)
    lines.append(f"ID: {doc_copy.get('_id', 'N/A')}")
    lines.append(f"Nombre: {doc_copy.get('nombre', 'N/A')}")
    lines.append(f"Email: {doc_copy.get('email', 'N/A')}")
    lines.append(f"Telefono: {doc_copy.get('telefono', 'N/A')}")
    
    # Fecha de registro
    fecha_registro = doc_copy.get('fecha_registro')
    if fecha_registro:
        if isinstance(fecha_registro, datetime):
            lines.append(f"Fecha Registro: {fecha_registro.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            lines.append(f"Fecha Registro: {fecha_registro}")
    
    # Membresía (subdocumento)
    membresia = doc_copy.get('membresia', {})
    if membresia:
        lines.append("")
        lines.append("--- Membresia ---")
        lines.append(f"  Tipo: {membresia.get('tipo', 'N/A')}")
        lines.append(f"  Duracion (meses): {membresia.get('duracion_meses', 'N/A')}")
        lines.append(f"  Precio Mensual: ${membresia.get('precio_mensual', 'N/A')}")
        
        fecha_inicio = membresia.get('fecha_inicio')
        if fecha_inicio and isinstance(fecha_inicio, datetime):
            lines.append(f"  Fecha Inicio: {fecha_inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        
        fecha_vencimiento = membresia.get('fecha_vencimiento')
        if fecha_vencimiento and isinstance(fecha_vencimiento, datetime):
            lines.append(f"  Fecha Vencimiento: {fecha_vencimiento.strftime('%Y-%m-%d %H:%M:%S')}")
        
        beneficios = membresia.get('beneficios', [])
        if beneficios:
            lines.append(f"  Beneficios: {', '.join(beneficios)}")
    
    # Historial de entrenamientos (array de subdocumentos)
    entrenamientos = doc_copy.get('historial_entrenamientos', [])
    lines.append("")
    lines.append("--- Historial de Entrenamientos ---")
    if entrenamientos:
        for i, entrenamiento in enumerate(entrenamientos[:5], 1):
            lines.append(f"  [{i}] Tipo: {entrenamiento.get('tipo', 'N/A')}")
            lines.append(f"      Duracion: {entrenamiento.get('duracion_minutos', 'N/A')} min")
            lines.append(f"      Calorias: {entrenamiento.get('calorias_quemadas', 'N/A')}")
            lines.append(f"      Instructor: {entrenamiento.get('instructor', 'N/A')}")
            lines.append(f"      Intensidad: {entrenamiento.get('nivel_intensidad', 'N/A')}")
            
            fecha_entrenamiento = entrenamiento.get('fecha')
            if fecha_entrenamiento and isinstance(fecha_entrenamiento, datetime):
                lines.append(f"      Fecha: {fecha_entrenamiento.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")
        
        if len(entrenamientos) > 5:
            lines.append(f"  ... y {len(entrenamientos) - 5} entrenamientos mas")
    else:
        lines.append("  El usuario aun no tiene historial de entrenamiento.")
    
    # Otros campos
    lines.append("")
    lines.append(f"Objetivos: {doc_copy.get('objetivos', 'N/A')}")
    lines.append(f"Peso: {doc_copy.get('peso_kg', 'N/A')} kg")
    lines.append(f"Altura: {doc_copy.get('altura_cm', 'N/A')} cm")
    lines.append(f"Activo: {'Si' if doc_copy.get('activo', False) else 'No'}")
    lines.append("=" * 70)
    
    return "\n".join(lines)


def format_document_short(doc):
    """
    Formato corto para listar documentos.
    
    Args:
        doc (dict): Documento de MongoDB
    
    Returns:
        str: Representación corta del documento
    """
    nombre = doc.get('nombre', 'N/A')
    email = doc.get('email', 'N/A')
    membresia_tipo = doc.get('membresia', {}).get('tipo', 'N/A')
    activo = "Si" if doc.get('activo', False) else "No"
    
    return f"{nombre:20} | {email:30} | {membresia_tipo:12} | Activo: {activo}"


def get_precio_membresia(tipo_membresia):
    """Devuelve el precio mensual fijo según el tipo de membresía."""
    if not tipo_membresia:
        return None

    tipo_normalizado = tipo_membresia.strip().lower()
    return PRECIOS_MEMBRESIAS.get(tipo_normalizado)


def get_precios_disponibles():
    """Devuelve la lista de membresías con sus precios fijos."""
    return [
        ("Basica", PRECIOS_MEMBRESIAS["basica"]),
        ("Premium", PRECIOS_MEMBRESIAS["premium"]),
        ("VIP", PRECIOS_MEMBRESIAS["vip"]),
    ]


def validar_texto_obligatorio(valor, nombre_campo, max_length=80):
    """Valida que un texto obligatorio no esté vacío y no exceda un largo máximo."""
    if valor is None:
        valor = ""
    valor = valor.strip()
    if not valor:
        raise ValueError(f"El campo '{nombre_campo}' no puede estar vacío")
    if len(valor) > max_length:
        raise ValueError(f"El campo '{nombre_campo}' no puede exceder {max_length} caracteres")
    return valor


def validar_email(email):
    """Valida que el email tenga formato de correo Gmail válido."""
    email = email.strip()
    if not email:
        raise ValueError("El email no puede estar vacío")
    if len(email) > 100:
        raise ValueError("El email no puede exceder 100 caracteres")
    patron_email = r"^[^\s@]+@gmail\.com$"
    if not re.match(patron_email, email):
        raise ValueError("El email debe ser un correo Gmail válido, por ejemplo: usuario@gmail.com")
    return email


def validar_telefono(telefono):
    """Valida que el teléfono use el formato chileno +56 9 ..."""
    telefono = telefono.strip()
    if not telefono:
        raise ValueError("El teléfono no puede estar vacío")

    patron = r"^\+56\s9\s\d{4}\s\d{4}$"
    if not re.match(patron, telefono):
        if telefono.startswith('+56'):
            raise ValueError("El número debe seguir el formato +56 9 4444 5555")
        if telefono.startswith('+'):
            raise ValueError("No se admiten números internacionales. Usa el formato +56 9 4444 5555")
        raise ValueError("El teléfono debe tener el formato +56 9 4444 5555")

    return telefono


def validar_numero_decimal(valor, nombre_campo, minimo=None, maximo=None):
    """Valida que un valor numérico sea correcto y cumpla con rangos opcionales."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"El campo '{nombre_campo}' debe ser numérico")

    if minimo is not None and numero < minimo:
        raise ValueError(f"El campo '{nombre_campo}' debe ser mayor o igual a {minimo}")
    if maximo is not None and numero > maximo:
        raise ValueError(f"El campo '{nombre_campo}' debe ser menor o igual a {maximo}")

    return numero


def buscar_miembro_por_nombre(collection, patron):
    """Busca un miembro por nombre y devuelve el más apropiado si hay coincidencias."""
    patron = patron.strip()
    if not patron:
        return None

    resultados = list(collection.find({"nombre": {"$regex": re.escape(patron), "$options": "i"}}))
    if not resultados:
        return None

    coincidencias_exactas = [
        miembro for miembro in resultados
        if miembro.get("nombre", "").strip().lower() == patron.lower()
    ]
    if coincidencias_exactas:
        return coincidencias_exactas[0]

    if len(resultados) == 1:
        return resultados[0]

    print("Se encontraron varios miembros coincidentes. Elige uno:")
    for idx, miembro in enumerate(resultados, 1):
        print(f"  {idx}. {miembro.get('nombre', 'N/A')}")

    opcion = input("Selecciona el número del miembro: ").strip()
    try:
        indice = int(opcion) - 1
        if 0 <= indice < len(resultados):
            return resultados[indice]
    except ValueError:
        pass

    print("No se pudo identificar el miembro. Se usará la primera coincidencia.")
    return resultados[0]


def opcion_crear_miembro(collection):
    """
    Opción 1: Crear un nuevo documento (miembro).
    
    Args:
        collection: Colección de MongoDB
    """
    print("\n" + "=" * 70)
    print("CREAR NUEVO MIEMBRO")
    print("=" * 70)
    
    try:
        # Datos personales
        nombre = ""
        while True:
            try:
                nombre = validar_texto_obligatorio(input("Nombre completo: "), "nombre", 25)
                break
            except ValueError as e:
                print(f"[ERROR] {e}")
                print("Inténtalo de nuevo.")
        
        email = ""
        while True:
            try:
                email = validar_email(input("Email: "))
                break
            except ValueError as e:
                print(f"[ERROR] {e}")
                print("Inténtalo de nuevo.")
        
        telefono = ""
        while True:
            try:
                telefono = validar_telefono(input("Telefono: "))
                break
            except ValueError as e:
                print(f"[ERROR] {e}")
                print("Inténtalo de nuevo.")
        
        # Fecha de registro (opcional)
        fecha_registro_str = input("Fecha de registro (YYYY-MM-DD) [dejar vacio para hoy]: ").strip()
        if fecha_registro_str:
            try:
                fecha_registro = datetime.strptime(fecha_registro_str, "%Y-%m-%d")
            except ValueError:
                print("[ERROR] Formato de fecha incorrecto. Usa YYYY-MM-DD")
                return
        else:
            fecha_registro = datetime.now()
        
        # Datos de membresía
        print("\n--- Datos de Membresia ---")
        print("Tipos disponibles: Basica, Premium, VIP")
        tipo_membresia = ""
        while True:
            try:
                tipo_membresia = validar_texto_obligatorio(input("Tipo de membresia: "), "tipo de membresia", 20)
                break
            except ValueError as e:
                print(f"[ERROR] {e}")
                print("Inténtalo de nuevo.")

        precio_mensual = get_precio_membresia(tipo_membresia)
        if precio_mensual is None:
            print("[ERROR] El tipo de membresia debe ser Basica, Premium o VIP")
            return

        precio_mensual = get_precio_membresia(tipo_membresia)
        print(f"[OK] Se asignó el precio mensual de ${precio_mensual:,.0f} CLP para la membresia {tipo_membresia.title()}.")
        
        duracion_meses = None
        while duracion_meses is None:
            try:
                valor_duracion = input("Duracion en meses: ").strip()
                if not valor_duracion:
                    raise ValueError("La duracion en meses no puede estar vacía")
                duracion_meses = int(valor_duracion)
                if duracion_meses <= 0:
                    raise ValueError("La duracion debe ser mayor a 0")
            except ValueError as e:
                print(f"[ERROR] {e}")
                print("Inténtalo de nuevo.")
        
        fecha_inicio_str = input("Fecha de inicio (YYYY-MM-DD) [dejar vacio para hoy]: ").strip()
        if fecha_inicio_str:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d")
            except ValueError:
                print("[ERROR] Formato de fecha incorrecto. Usa YYYY-MM-DD")
                return
        else:
            fecha_inicio = datetime.now()
        
        # Calcular fecha de vencimiento
        from dateutil.relativedelta import relativedelta
        fecha_vencimiento = fecha_inicio + relativedelta(months=duracion_meses)
        
        # Beneficios
        print("\nBeneficios disponibles: Acceso 24/7, Clases grupales ilimitadas, Sauna, Nutricionista, Piscina, Entrenador personal")
        beneficios = []
        while not beneficios:
            beneficios_input = input("Beneficios (separados por coma): ").strip()
            if not beneficios_input:
                print("[ERROR] Debes ingresar al menos un beneficio")
                print("Inténtalo de nuevo.")
                continue
            beneficios = [b.strip() for b in beneficios_input.split(',') if b.strip()]
            if not beneficios:
                print("[ERROR] Debes ingresar al menos un beneficio")
                print("Inténtalo de nuevo.")
        
        # Objetivos
        objetivos = ""
        while True:
            try:
                objetivos = validar_texto_obligatorio(input("Objetivos: "), "objetivos", 120)
                break
            except ValueError as e:
                print(f"[ERROR] {e}")
                print("Inténtalo de nuevo.")
        
        # Datos físicos
        peso_kg = None
        while peso_kg is None:
            try:
                peso_kg = validar_numero_decimal(input("Peso (kg): "), "peso", minimo=1, maximo=500)
            except ValueError as e:
                print(f"[ERROR] {e}")
                print("Inténtalo de nuevo.")
        
        altura_cm = None
        while altura_cm is None:
            try:
                altura_cm = validar_numero_decimal(input("Altura (cm): "), "altura", minimo=1, maximo=300)
            except ValueError as e:
                print(f"[ERROR] {e}")
                print("Inténtalo de nuevo.")
        
        # Estado activo
        activo_input = input("Activo? (s/n) [s]: ").strip().lower()
        activo = activo_input != 'n'
        
        # Crear documento
        nuevo_miembro = {
            "nombre": nombre,
            "email": email,
            "telefono": telefono,
            "fecha_registro": fecha_registro,
            "membresia": {
                "tipo": tipo_membresia,
                "duracion_meses": duracion_meses,
                "precio_mensual": precio_mensual,
                "fecha_inicio": fecha_inicio,
                "fecha_vencimiento": fecha_vencimiento,
                "beneficios": beneficios
            },
            "historial_entrenamientos": [],
            "objetivos": objetivos,
            "peso_kg": peso_kg,
            "altura_cm": altura_cm,
            "activo": activo
        }
        
        # Insertar en la base de datos
        result = collection.insert_one(nuevo_miembro)
        print(f"\n[OK] Miembro creado exitosamente con ID: {result.inserted_id}")
        
        # Mostrar el documento creado
        doc_creado = collection.find_one({"_id": result.inserted_id})
        if doc_creado:
            print("\nDocumento creado:")
            print(format_document(doc_creado))
        
    except ValueError as e:
        print(f"[ERROR] Error en la entrada de datos: {e}")
    except Exception as e:
        print(f"[ERROR] Error al crear el miembro: {e}")


def opcion_listar_miembros(collection):
    """
    Opción 2: Listar todos los miembros con detalles completos.
    
    Args:
        collection: Colección de MongoDB
    """
    print("\n" + "=" * 70)
    print("LISTAR TODOS LOS MIEMBROS")
    print("=" * 70)
    
    try:
        miembros = list(collection.find({}))
        
        if not miembros:
            print("No hay miembros registrados en la base de datos.")
            return
        
        print(f"\nTotal de miembros: {len(miembros)}")
        print("\n" + "-" * 80)
        print(f"{'Nombre':20} | {'Email':30} | {'Membresia':12} | {'Activo':6}")
        print("-" * 80)
        
        for miembro in miembros:
            nombre = miembro.get('nombre', 'N/A')[:20]
            email = miembro.get('email', 'N/A')[:30]
            membresia_tipo = miembro.get('membresia', {}).get('tipo', 'N/A')[:12]
            activo = "Si" if miembro.get('activo', False) else "No"
            
            print(f"{nombre:20} | {email:30} | {membresia_tipo:12} | {activo:6}")
        
        print("-" * 80)
        
        ver_detalles = input("\n¿Ver detalles completos de los miembros? (s/n) [n]: ").strip().lower()
        if ver_detalles == 's':
            for miembro in miembros:
                print("\n" + format_document(miembro))
        
    except Exception as e:
        print(f"[ERROR] Error al listar miembros: {e}")


def opcion_buscar_por_precio(collection):
    """
    Opción 3: Buscar miembros por un precio exacto de membresía.
    
    Args:
        collection: Colección de MongoDB
    """
    print("\n" + "=" * 70)
    print("BUSCAR POR PRECIO DE MEMBRESIA")
    print("=" * 70)

    print("\nPrecios disponibles:")
    for nombre, precio in get_precios_disponibles():
        print(f"- {nombre}: ${precio:,.0f} CLP")
    
    try:
        try:
            monto = float(input("Ingresa el precio exacto de membresia (ej: 30.00): ").strip())
            if monto < 0:
                print("[ERROR] El monto debe ser mayor o igual a 0")
                return
        except ValueError:
            print("[ERROR] Ingresa un numero valido")
            return
        
        query = {
            "membresia.precio_mensual": monto
        }
        
        resultados = list(collection.find(query))
        
        if not resultados:
            print(f"\nNo se encontraron miembros con membresia de ${monto:,.0f} CLP.")
            continuar = input("¿Quieres seguir buscando? (s/n): ").strip().lower()
            if continuar == 's':
                return opcion_buscar_por_precio(collection)
            return
        
        print(f"\nMiembros con membresia de ${monto:,.0f} CLP: {len(resultados)}")
        print("\n" + "-" * 90)
        print(f"{'Nombre':20} | {'Email':30} | {'Tipo':12} | {'Precio':8} | {'Duracion':8}")
        print("-" * 90)
        
        for miembro in resultados:
            nombre = miembro.get('nombre', 'N/A')[:20]
            email = miembro.get('email', 'N/A')[:30]
            membresia = miembro.get('membresia', {})
            tipo = membresia.get('tipo', 'N/A')[:12]
            precio = f"${membresia.get('precio_mensual', 0):,.0f} CLP"
            duracion = f"{membresia.get('duracion_meses', 'N/A')} meses"
            
            print(f"{nombre:20} | {email:30} | {tipo:12} | {precio:8} | {duracion:8}")
        
        print("-" * 90)
        
        ver_detalles = input("\n¿Ver detalles completos de los resultados? (s/n) [n]: ").strip().lower()
        if ver_detalles == 's':
            for resultado in resultados:
                print("\n" + format_document(resultado))
        
    except Exception as e:
        print(f"[ERROR] Error en la busqueda: {e}")
        
        ver_detalle = input("\n¿Ver detalles de un miembro? (ingresa el nombre o presiona Enter para salir): ").strip()
        if ver_detalle:
            detalle = buscar_miembro_por_nombre(collection, ver_detalle)
            if detalle:
                print("\n" + format_document(detalle))
            else:
                print(f"No se encontró un miembro con el nombre: {ver_detalle}")


def opcion_buscar_por_nombre(collection):
    """
    Opción 4: Buscar miembros usando expresión regular ($regex) sobre el nombre.
    
    Args:
        collection: Colección de MongoDB
    """
    print("\n" + "=" * 70)
    print("BUSCAR MIEMBROS POR NOMBRE (EXPRESION REGULAR)")
    print("=" * 70)
    
    try:
        patron = input("Ingresa el patron de busqueda (ej: 'perez' o 'juan'): ").strip()
        if not patron:
            print("[ERROR] Debes ingresar un patron de busqueda")
            return
        
        query = {
            "nombre": {"$regex": patron, "$options": "i"}
        }
        
        resultados = list(collection.find(query))
        
        if not resultados:
            print(f"\nNo se encontraron miembros con el patron '{patron}' en el nombre.")
            return
        
        print(f"\nMiembros encontrados con el patron '{patron}': {len(resultados)}")
        print("\n" + "-" * 90)
        print(f"{'Nombre':20} | {'Email':30} | {'Membresia':12} | {'Precio':8} | {'Activo'}")
        print("-" * 90)
        
        for miembro in resultados:
            nombre = miembro.get('nombre', 'N/A')[:20]
            email = miembro.get('email', 'N/A')[:30]
            membresia_tipo = miembro.get('membresia', {}).get('tipo', 'N/A')[:12]
            precio = f"${miembro.get('membresia', {}).get('precio_mensual', 0):.2f}"
            activo = "Si" if miembro.get('activo', False) else "No"
            
            print(f"{nombre:20} | {email:30} | {membresia_tipo:12} | {precio:8} | {activo}")
        
        print("-" * 90)
        
        ver_detalle = input("\n¿Ver detalles de un miembro? (ingresa el nombre o presiona Enter para salir): ").strip()
        if ver_detalle:
            detalle = buscar_miembro_por_nombre(collection, ver_detalle)
            if detalle:
                print("\n" + format_document(detalle))
            else:
                print(f"No se encontró un miembro con el nombre: {ver_detalle}")
        
    except Exception as e:
        print(f"[ERROR] Error en la busqueda: {e}")


def opcion_buscar_por_rango_fechas(collection):
    """
    Opción 5: Buscar miembros por rango de fechas de registro.
    
    Args:
        collection: Colección de MongoDB
    """
    print("\n" + "=" * 70)
    print("BUSCAR MIEMBROS POR RANGO DE FECHAS")
    print("=" * 70)
    
    try:
        # Fecha inicio
        fecha_inicio_str = input("Fecha de inicio (YYYY-MM-DD): ").strip()
        if not fecha_inicio_str:
            print("[ERROR] La fecha de inicio es obligatoria")
            return
        
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d")
        except ValueError:
            print("[ERROR] Formato de fecha incorrecto. Usa YYYY-MM-DD")
            return
        
        # Fecha fin
        fecha_fin_str = input("Fecha de fin (YYYY-MM-DD): ").strip()
        if not fecha_fin_str:
            print("[ERROR] La fecha de fin es obligatoria")
            return
        
        try:
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d")
            # Ajustar para incluir todo el día
            fecha_fin = fecha_fin.replace(hour=23, minute=59, second=59)
        except ValueError:
            print("[ERROR] Formato de fecha incorrecto. Usa YYYY-MM-DD")
            return
        
        if fecha_inicio > fecha_fin:
            print("[ERROR] La fecha de inicio debe ser anterior a la fecha de fin")
            return
        
        # Consulta con rango de fechas usando $gte y $lte
        query = {
            "fecha_registro": {
                "$gte": fecha_inicio,
                "$lte": fecha_fin
            }
        }
        
        resultados = list(collection.find(query))
        
        if not resultados:
            print(f"\nNo se encontraron miembros registrados entre {fecha_inicio_str} y {fecha_fin_str}.")
            return
        
        print(f"\nMiembros registrados entre {fecha_inicio_str} y {fecha_fin_str}: {len(resultados)}")
        print("\n" + "-" * 80)
        print(f"{'Nombre':20} | {'Email':30} | {'Fecha Registro':20} | {'Membresia':12}")
        print("-" * 80)
        
        for miembro in resultados:
            nombre = miembro.get('nombre', 'N/A')[:20]
            email = miembro.get('email', 'N/A')[:30]
            fecha_reg = miembro.get('fecha_registro')
            if fecha_reg and isinstance(fecha_reg, datetime):
                fecha_str = fecha_reg.strftime('%Y-%m-%d %H:%M')
            else:
                fecha_str = 'N/A'
            membresia_tipo = miembro.get('membresia', {}).get('tipo', 'N/A')[:12]
            
            print(f"{nombre:20} | {email:30} | {fecha_str:20} | {membresia_tipo:12}")
        
        print("-" * 80)
        
        ver_detalle = input("\n¿Ver detalles de un miembro? (ingresa el nombre o presiona Enter para salir): ").strip()
        if ver_detalle:
            detalle = buscar_miembro_por_nombre(collection, ver_detalle)
            if detalle:
                print("\n" + format_document(detalle))
            else:
                print(f"No se encontró un miembro con el nombre: {ver_detalle}")
        
    except Exception as e:
        print(f"[ERROR] Error en la busqueda: {e}")


def opcion_buscar_por_instructor(collection):
    """
    Opción 6: Buscar miembros que hayan entrenado con un instructor específico.
    Búsqueda dentro del array de subdocumentos historial_entrenamientos.
    
    Args:
        collection: Colección de MongoDB
    """
    print("\n" + "=" * 70)
    print("BUSCAR MIEMBROS POR INSTRUCTOR")
    print("=" * 70)
    
    try:
        instructor = input("Ingresa el nombre del instructor (ej: 'Carlos Rodriguez'): ").strip()
        if not instructor:
            print("[ERROR] Debes ingresar el nombre del instructor")
            return
        
        # Buscar dentro del array de subdocumentos
        query = {
            "historial_entrenamientos.instructor": {"$regex": instructor, "$options": "i"}
        }
        
        projection = {
            "_id": 1,
            "nombre": 1,
            "email": 1,
            "historial_entrenamientos": 1,
            "membresia.tipo": 1,
            "activo": 1
        }
        
        resultados = list(collection.find(query, projection))
        
        if not resultados:
            print(f"\nNo se encontraron miembros que hayan entrenado con el instructor '{instructor}'.")
            return
        
        print(f"\nMiembros que han entrenado con '{instructor}': {len(resultados)}")
        print("\n" + "-" * 80)
        
        for miembro in resultados:
            nombre = miembro.get('nombre', 'N/A')
            email = miembro.get('email', 'N/A')
            membresia_tipo = miembro.get('membresia', {}).get('tipo', 'N/A')
            activo = "Si" if miembro.get('activo', False) else "No"
            
            # Contar cuántos entrenamientos con este instructor
            entrenamientos_con_instructor = [
                e for e in miembro.get('historial_entrenamientos', [])
                if instructor.lower() in e.get('instructor', '').lower()
            ]
            
            print(f"\nNombre: {nombre}")
            print(f"Email: {email}")
            print(f"Membresia: {membresia_tipo}")
            print(f"Activo: {activo}")
            print(f"Entrenamientos con {instructor}: {len(entrenamientos_con_instructor)}")
            
            # Mostrar los entrenamientos con este instructor
            for i, entrenamiento in enumerate(entrenamientos_con_instructor[:3], 1):
                fecha = entrenamiento.get('fecha')
                if fecha and isinstance(fecha, datetime):
                    fecha_str = fecha.strftime('%Y-%m-%d %H:%M')
                else:
                    fecha_str = 'N/A'
                
                print(f"  [{i}] {entrenamiento.get('tipo', 'N/A')} - {fecha_str} - {entrenamiento.get('duracion_minutos', 'N/A')} min")
            
            if len(entrenamientos_con_instructor) > 3:
                print(f"  ... y {len(entrenamientos_con_instructor) - 3} entrenamientos mas")
        
        print("\n" + "-" * 80)
        
        ver_detalle = input("\n¿Ver detalles completos de un miembro? (ingresa el nombre o presiona Enter para salir): ").strip()
        if ver_detalle:
            detalle = buscar_miembro_por_nombre(collection, ver_detalle)
            if detalle:
                print("\n" + format_document(detalle))
            else:
                print(f"No se encontró un miembro con el nombre: {ver_detalle}")
        
    except Exception as e:
        print(f"[ERROR] Error en la busqueda: {e}")


def opcion_actualizar_campo_raiz(collection):
    """
    Opción 7: Actualizar un campo raíz del documento.
    
    Args:
        collection: Colección de MongoDB
    """
    print("\n" + "=" * 70)
    print("ACTUALIZAR CAMPO RAIZ")
    print("=" * 70)
    
    try:
        # Buscar el miembro
        nombre = input("Nombre del miembro a actualizar: ").strip()
        if not nombre:
            print("[ERROR] Debes ingresar un nombre")
            return
        
        miembro = buscar_miembro_por_nombre(collection, nombre)
        if not miembro:
            print(f"No se encontró un miembro con el nombre: {nombre}")
            return
        
        print("\nMiembro encontrado:")
        print(format_document(miembro))
        
        # Mostrar campos disponibles para actualizar
        print("\nCampos disponibles para actualizar:")
        print("1. nombre")
        print("2. email")
        print("3. telefono")
        print("4. peso_kg")
        print("5. altura_cm")
        print("6. activo (true/false)")
        print("7. objetivos")
        
        campo = input("\nSelecciona el campo a actualizar (1-7): ").strip()
        
        campos = {
            "1": "nombre",
            "2": "email",
            "3": "telefono",
            "4": "peso_kg",
            "5": "altura_cm",
            "6": "activo",
            "7": "objetivos"
        }
        
        if campo not in campos:
            print("[ERROR] Opcion no valida")
            return
        
        campo_seleccionado = campos[campo]
        nuevo_valor = input(f"Ingresa el nuevo valor para '{campo_seleccionado}': ").strip()
        
        if not nuevo_valor:
            print("[ERROR] El valor no puede estar vacio")
            return
        
        # Convertir tipos según el campo
        if campo_seleccionado == "peso_kg":
            try:
                nuevo_valor = float(nuevo_valor)
                if nuevo_valor <= 0:
                    print("[ERROR] El peso debe ser mayor a 0")
                    return
            except ValueError:
                print("[ERROR] El peso debe ser un numero")
                return
        elif campo_seleccionado == "altura_cm":
            try:
                nuevo_valor = float(nuevo_valor)
                if nuevo_valor <= 0:
                    print("[ERROR] La altura debe ser mayor a 0")
                    return
            except ValueError:
                print("[ERROR] La altura debe ser un numero")
                return
        elif campo_seleccionado == "activo":
            nuevo_valor = nuevo_valor.lower() in ['true', 'si', 's', '1', 'yes', 'y']
        
        # Confirmar actualización
        print(f"\n¿Actualizar '{campo_seleccionado}' de '{miembro.get(campo_seleccionado)}' a '{nuevo_valor}'?")
        confirmar = input("Confirmar (s/n): ").strip().lower()
        
        if confirmar != 's':
            print("[OK] Actualizacion cancelada")
            return
        
        # Realizar la actualización
        result = collection.update_one(
            {"_id": miembro["_id"]},
            {"$set": {campo_seleccionado: nuevo_valor}}
        )
        
        if result.modified_count > 0:
            print(f"\n[OK] Campo '{campo_seleccionado}' actualizado exitosamente")
            
            # Mostrar el documento actualizado
            doc_actualizado = collection.find_one({"_id": miembro["_id"]})
            if doc_actualizado:
                print("\nDocumento actualizado:")
                print(format_document(doc_actualizado))
        else:
            print("[ADVERTENCIA] No se realizaron cambios")
        
    except Exception as e:
        print(f"[ERROR] Error al actualizar: {e}")


def opcion_actualizar_subdocumento(collection):
    """
    Opción 8: Actualizar campo dentro de subdocumento o agregar a array.
    
    Args:
        collection: Colección de MongoDB
    """
    print("\n" + "=" * 70)
    print("ACTUALIZAR SUBDOCUMENTO O ARRAY")
    print("=" * 70)
    
    try:
        # Buscar el miembro
        nombre = input("Nombre del miembro a actualizar: ").strip()
        if not nombre:
            print("[ERROR] Debes ingresar un nombre")
            return
        
        miembro = buscar_miembro_por_nombre(collection, nombre)
        if not miembro:
            print(f"No se encontró un miembro con el nombre: {nombre}")
            return
        
        print("\nMiembro encontrado:")
        print(format_document(miembro))
        
        print("\nOpciones de actualización:")
        print("1. Actualizar precio de membresia")
        print("2. Actualizar duracion de membresia")
        print("3. Agregar beneficio a membresia")
        print("4. Agregar nuevo entrenamiento al historial")
        
        opcion = input("\nSelecciona una opcion (1-4): ").strip()
        
        if opcion == "1":
            # Actualizar precio de membresia
            try:
                nuevo_precio = float(input("Nuevo precio mensual: ").strip())
                if nuevo_precio < 0:
                    print("[ERROR] El precio debe ser mayor o igual a 0")
                    return
            except ValueError:
                print("[ERROR] Ingresa un numero valido")
                return
            
            confirmar = input(f"¿Actualizar precio de ${miembro['membresia']['precio_mensual']} a ${nuevo_precio}? (s/n): ").strip().lower()
            if confirmar == 's':
                result = collection.update_one(
                    {"_id": miembro["_id"]},
                    {"$set": {"membresia.precio_mensual": nuevo_precio}}
                )
                
                if result.modified_count > 0:
                    print("[OK] Precio actualizado exitosamente")
                    doc_actualizado = collection.find_one({"_id": miembro["_id"]})
                    if doc_actualizado:
                        print("\nDocumento actualizado:")
                        print(format_document(doc_actualizado))
                else:
                    print("[ADVERTENCIA] No se realizaron cambios")
        
        elif opcion == "2":
            # Actualizar duracion de membresia
            try:
                nueva_duracion = int(input("Nueva duracion en meses: ").strip())
                if nueva_duracion <= 0:
                    print("[ERROR] La duracion debe ser mayor a 0")
                    return
            except ValueError:
                print("[ERROR] Ingresa un numero entero valido")
                return
            
            confirmar = input(f"¿Actualizar duracion de {miembro['membresia']['duracion_meses']} a {nueva_duracion} meses? (s/n): ").strip().lower()
            if confirmar == 's':
                from dateutil.relativedelta import relativedelta
                fecha_inicio = miembro['membresia']['fecha_inicio']
                nueva_fecha_vencimiento = fecha_inicio + relativedelta(months=nueva_duracion)
                
                result = collection.update_one(
                    {"_id": miembro["_id"]},
                    {
                        "$set": {
                            "membresia.duracion_meses": nueva_duracion,
                            "membresia.fecha_vencimiento": nueva_fecha_vencimiento
                        }
                    }
                )
                
                if result.modified_count > 0:
                    print("[OK] Duracion actualizada exitosamente")
                    doc_actualizado = collection.find_one({"_id": miembro["_id"]})
                    if doc_actualizado:
                        print("\nDocumento actualizado:")
                        print(format_document(doc_actualizado))
                else:
                    print("[ADVERTENCIA] No se realizaron cambios")
        
        elif opcion == "3":
            # Agregar beneficio a membresia
            nuevo_beneficio = input("Nuevo beneficio a agregar: ").strip()
            if not nuevo_beneficio:
                print("[ERROR] Debes ingresar un beneficio")
                return
            
            confirmar = input(f"¿Agregar beneficio '{nuevo_beneficio}' a la membresia? (s/n): ").strip().lower()
            if confirmar == 's':
                result = collection.update_one(
                    {"_id": miembro["_id"]},
                    {"$push": {"membresia.beneficios": nuevo_beneficio}}
                )
                
                if result.modified_count > 0:
                    print("[OK] Beneficio agregado exitosamente")
                    doc_actualizado = collection.find_one({"_id": miembro["_id"]})
                    if doc_actualizado:
                        print("\nDocumento actualizado:")
                        print(format_document(doc_actualizado))
                else:
                    print("[ADVERTENCIA] No se realizaron cambios")
        
        elif opcion == "4":
            # Agregar nuevo entrenamiento al historial
            print("\n--- Nuevo Entrenamiento ---")
            
            tipo = input("Tipo de entrenamiento: ").strip()
            if not tipo:
                print("[ERROR] El tipo de entrenamiento es obligatorio")
                return
            
            try:
                duracion = int(input("Duracion (minutos): ").strip())
                if duracion <= 0:
                    print("[ERROR] La duracion debe ser mayor a 0")
                    return
            except ValueError:
                print("[ERROR] Ingresa un numero entero valido")
                return
            
            try:
                calorias = int(input("Calorias quemadas: ").strip())
                if calorias < 0:
                    print("[ERROR] Las calorias deben ser mayor o igual a 0")
                    return
            except ValueError:
                print("[ERROR] Ingresa un numero entero valido")
                return
            
            instructor = input("Nombre del instructor: ").strip()
            if not instructor:
                print("[ERROR] El nombre del instructor es obligatorio")
                return
            
            intensidad = input("Nivel de intensidad (Bajo/Medio/Alto): ").strip()
            if not intensidad:
                print("[ERROR] El nivel de intensidad es obligatorio")
                return
            
            fecha_entrenamiento_str = input("Fecha (YYYY-MM-DD) [dejar vacio para hoy]: ").strip()
            if fecha_entrenamiento_str:
                try:
                    fecha_entrenamiento = datetime.strptime(fecha_entrenamiento_str, "%Y-%m-%d")
                except ValueError:
                    print("[ERROR] Formato de fecha incorrecto. Usa YYYY-MM-DD")
                    return
            else:
                fecha_entrenamiento = datetime.now()
            
            nuevo_entrenamiento = {
                "fecha": fecha_entrenamiento,
                "duracion_minutos": duracion,
                "tipo": tipo,
                "calorias_quemadas": calorias,
                "instructor": instructor,
                "nivel_intensidad": intensidad
            }
            
            confirmar = input("\n¿Agregar este entrenamiento al historial? (s/n): ").strip().lower()
            if confirmar == 's':
                result = collection.update_one(
                    {"_id": miembro["_id"]},
                    {"$push": {"historial_entrenamientos": nuevo_entrenamiento}}
                )
                
                if result.modified_count > 0:
                    print("[OK] Entrenamiento agregado exitosamente")
                    doc_actualizado = collection.find_one({"_id": miembro["_id"]})
                    if doc_actualizado:
                        print("\nDocumento actualizado:")
                        print(format_document(doc_actualizado))
                else:
                    print("[ADVERTENCIA] No se realizaron cambios")
        
        else:
            print("[ERROR] Opcion no valida")
        
    except Exception as e:
        print(f"[ERROR] Error al actualizar: {e}")


def opcion_eliminar_miembro(collection):
    """
    Opción 9: Eliminar un miembro con confirmación y vista previa.
    
    Args:
        collection: Colección de MongoDB
    """
    print("\n" + "=" * 70)
    print("ELIMINAR MIEMBRO")
    print("=" * 70)

    try:
        nombre = input("Nombre del miembro a eliminar: ").strip()
        if not nombre:
            print("[ERROR] Debes ingresar un nombre")
            return

        miembro = buscar_miembro_por_nombre(collection, nombre)
        if not miembro:
            print(f"No se encontró un miembro con el nombre: {nombre}")
            return

        print("\nMiembro encontrado:")
        print(format_document(miembro))

        confirmacion = input("\n¿Estás seguro de eliminar este miembro? (s/n): ").strip().lower()
        if confirmacion != "s":
            print("[OK] Eliminación cancelada")
            return

        resultado = collection.delete_one({"_id": miembro["_id"]})
        if resultado.deleted_count > 0:
            print("\n[OK] Miembro eliminado correctamente")
        else:
            print("[ADVERTENCIA] No se pudo eliminar el miembro")

    except Exception as e:
        print(f"[ERROR] Error al eliminar: {e}")


def mostrar_menu():
    """Muestra el menú principal del CRUD."""
    print("\n" + "=" * 70)
    print("CRUD GIMNASIO - MENÚ PRINCIPAL")
    print("=" * 70)
    print("1. Crear miembro")
    print("2. listar miembros")
    print("3. Buscar por precio")
    print("4. Buscar por nombre")
    print("5. Buscar por rango de fechas")
    print("6. Buscar por instructor")
    print("7. actualizar miembro")
    print("8. actualizar subdocumento/historial")
    print("9. eliminar miembro")
    print("10. Salir")


def ejecutar_menu(collection):
    """Ejecuta el ciclo interactivo del menú CRUD."""
    while True:
        mostrar_menu()
        opcion = input("\nSelecciona una opción (1-10): ").strip()

        if opcion == "1":
            opcion_crear_miembro(collection)
        elif opcion == "2":
            opcion_listar_miembros(collection)
        elif opcion == "3":
            opcion_buscar_por_precio(collection)
        elif opcion == "4":
            opcion_buscar_por_nombre(collection)
        elif opcion == "5":
            opcion_buscar_por_rango_fechas(collection)
        elif opcion == "6":
            opcion_buscar_por_instructor(collection)
        elif opcion == "7":
            opcion_actualizar_campo_raiz(collection)
        elif opcion == "8":
            opcion_actualizar_subdocumento(collection)
        elif opcion == "9":
            opcion_eliminar_miembro(collection)
        elif opcion == "10":
            print("\nSaliendo del CRUD...")
            break
        else:
            print("[ERROR] Opción no válida")


def main():
    """Función principal del programa."""
    print("Iniciando main.py...")
    print("Importando módulos... OK")

    client = connect_to_mongodb()
    if client is None:
        return

    try:
        db = client["gimnasio_db"]
        collection = db["miembros"]
        ejecutar_menu(collection)
    finally:
        client.close()


if __name__ == "__main__":
    main()


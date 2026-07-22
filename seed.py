#seed.py - Script de inicialización para la base de datos del gimnasio
#Este script carga los datos iniciales desde un archivo JSON a MongoDB
#con conversión automática de fechas.

import json
import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import sys


 #Función recursiva para convertir diccionarios con formato {"$date": "..."} 
 #a objetos datetime de Python.
 #Args:
 #obj: Objeto a procesar (dict, list, str, etc.)
 #Returns:
 #Objeto con las fechas convertidas a datetime   
 
def convert_dates(obj):
    
    if isinstance(obj, dict):
        # Verificar si es un objeto de fecha de MongoDB
        if "$date" in obj and isinstance(obj["$date"], str):
            try:
                # Parsear la fecha ISO 8601
                # Eliminar 'Z' y reemplazar con '+00:00' para compatibilidad
                date_str = obj["$date"]
                if date_str.endswith('Z'):
                    date_str = date_str[:-1] + '+00:00'
                return datetime.fromisoformat(date_str)
            except ValueError as e:
                print(f"  Error al convertir fecha: {obj['$date']} - {e}")
                return obj
        
        # Procesar recursivamente los valores del diccionario
        return {key: convert_dates(value) for key, value in obj.items()}
    
    elif isinstance(obj, list):
        # Procesar recursivamente los elementos de la lista
        return [convert_dates(item) for item in obj]
    
    else:
        # Devolver el objeto sin cambios
        return obj


def load_json_data(file_path):
    """
    Carga y procesa el archivo JSON con conversión de fechas.
    
    Args:
        file_path (str): Ruta al archivo JSON
    
    Returns:
        list: Lista de documentos con fechas convertidas
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
            # Si el JSON es un array, procesar cada documento
            if isinstance(data, list):
                processed_data = [convert_dates(doc) for doc in data]
                print(f" Archivo JSON cargado correctamente: {len(processed_data)} documentos")
                return processed_data
            else:
                print(" El archivo JSON debe contener un array de documentos")
                return []
                
    except FileNotFoundError:
        print(f" Archivo no encontrado: {file_path}")
        return []
    except json.JSONDecodeError as e:
        print(f" Error al decodificar JSON: {e}")
        return []
    except Exception as e:
        print(f" Error al leer el archivo: {e}")
        return []


def connect_to_mongodb(uri="mongodb://localhost:27017/"):

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Verificar la conexión
        client.admin.command('ping')
        print(" Conexión exitosa a MongoDB")
        return client
    except ConnectionFailure as e:
        print(f" Error de conexión a MongoDB: {e}")
        print("   Asegúrate de que MongoDB esté ejecutándose en localhost:27017")
        sys.exit(1)
    except Exception as e:
        print(f" Error inesperado: {e}")
        sys.exit(1)


def seed_database(client, db_name="gimnasio_db", collection_name="miembros", data=None):
    """
    Limpia y carga los datos en la base de datos.
    
    Args:
        client: Cliente de MongoDB
        db_name (str): Nombre de la base de datos
        collection_name (str): Nombre de la colección
        data (list): Datos a insertar
    
    Returns:
        int: Número de documentos insertados
    """
    if data is None:
        print(" No hay datos para insertar")
        return 0
    
    try:
        db = client[db_name]
        collection = db[collection_name]
        
        # 1. Limpiar la colección (idempotencia)
        print(f" Limpiando colección '{collection_name}'...")
        result = collection.delete_many({})
        print(f"    Eliminados {result.deleted_count} documentos existentes")
        
        # 2. Insertar nuevos documentos
        print(f" Insertando {len(data)} documentos...")
        result = collection.insert_many(data)
        
        print(f" ¡Datos cargados exitosamente!")
        print(f"    {len(result.inserted_ids)} documentos insertados")
        print(f"    IDs: {', '.join([str(id) for id in result.inserted_ids[:3]])}{'...' if len(result.inserted_ids) > 3 else ''}")
        
        return len(result.inserted_ids)
        
    except OperationFailure as e:
        print(f" Error de operación en MongoDB: {e}")
        return 0
    except Exception as e:
        print(f" Error inesperado: {e}")
        return 0


def verify_data(client, db_name="gimnasio_db", collection_name="miembros"):
    """
    Verifica que los datos se hayan cargado correctamente.
    
    Args:
        client: Cliente de MongoDB
        db_name (str): Nombre de la base de datos
        collection_name (str): Nombre de la colección
    """
    try:
        db = client[db_name]
        collection = db[collection_name]
        
        count = collection.count_documents({})
        print(f"\n Verificación final:")
        print(f"    Total de documentos en la colección: {count}")
        
        if count > 0:
            # Mostrar un ejemplo de documento
            sample = collection.find_one()
            print(f"    Ejemplo de documento:")
            print(f"      - Nombre: {sample.get('nombre', 'N/A')}")
            print(f"      - Email: {sample.get('email', 'N/A')}")
            print(f"      - Membresía: {sample.get('membresia', {}).get('tipo', 'N/A')}")
            print(f"      - Fecha registro: {sample.get('fecha_registro', 'N/A')}")
            print(f"      - Entrenamientos: {len(sample.get('historial_entrenamientos', []))}")
        
        return count
        
    except Exception as e:
        print(f" Error al verificar datos: {e}")
        return 0


def main():
    """
    Función principal que coordina todo el proceso de seeding.
    """
    print("=" * 60)
    print("  SEED DE BASE DE DATOS - GIMNASIO")
    print("=" * 60)
    
    # Configuración
    JSON_PATH = os.path.join("data", "gimnasio_db.json")
    DB_NAME = "gimnasio_db"
    COLLECTION_NAME = "miembros"
    
    # Paso 1: Conectar a MongoDB
    print("\n Conectando a MongoDB...")
    client = connect_to_mongodb()
    
    # Paso 2: Cargar y procesar datos JSON
    print(f"\n Cargando datos desde: {JSON_PATH}")
    data = load_json_data(JSON_PATH)
    
    if not data:
        print(" No se pudieron cargar los datos. Saliendo...")
        sys.exit(1)
    
    # Paso 3: Cargar datos en la base de datos
    print(f"\n Cargando datos en '{DB_NAME}.{COLLECTION_NAME}'...")
    inserted_count = seed_database(client, DB_NAME, COLLECTION_NAME, data)
    
    if inserted_count > 0:
        # Paso 4: Verificar los datos
        verify_data(client, DB_NAME, COLLECTION_NAME)
        
        print("\n" + "=" * 60)
        print(" ¡PROCESO COMPLETADO CON ÉXITO!")
        print(f"   {inserted_count} documentos cargados en {DB_NAME}.{COLLECTION_NAME}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print(" ¡PROCESO FALLIDO!")
        print("   No se insertaron documentos")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
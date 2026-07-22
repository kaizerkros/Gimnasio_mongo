from pymongo import MongoClient

try:
    client = MongoClient('localhost', 27017, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✅ Conexion exitosa a MongoDB")
    print("Bases de datos:", client.list_database_names())
except Exception as e:
    print(f"❌ Error: {e}")
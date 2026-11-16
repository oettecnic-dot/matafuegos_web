from flask import Flask, render_template, request, redirect, url_for
import urllib.parse
import os
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)
app.secret_key = 'matafuegos_seguridad_consorcios_2026'

# Tu número de WhatsApp de contacto comercial
WHATSAPP_NUMERO = "5491161726657"

# Configuración de credenciales y conexión a Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
CREDENTIALS_FILE = 'credentials.json'  # Archivo JSON de tu cuenta de servicio de Google Cloud

def cargar_catalogo_desde_sheets():
    """
    Consulta en tiempo real la planilla de Google Sheets 'Catalogo_Matafuegos_1500'.
    Si ocurre algún problema de conexión, devuelve una lista vacía para evitar caídas.
    """
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            print("AVISO: No se encontró el archivo credentials.json localmente.")
            return []
            
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)
        
        # Abrimos la planilla maestra por su nombre exacto en Google Drive
        sheet = client.open("Catalogo_Matafuegos_1500").sheet1
        
        # Obtenemos todas las filas como una lista de diccionarios limpios
        registros = sheet.get_all_records()
        
        productos = []
        for index, fila in enumerate(registros):
            productos.append({
                "id": index + 1,
                "sku": str(fila.get("SKU", f"MAT-{index+1:04d}")),
                "categoria": str(fila.get("Categoría", "General")),
                "tipo": str(fila.get("Subcategoría / Tipo", "")),
                "nombre": str(fila.get("Descripción del Producto", "Artículo de Seguridad")),
                "peso": str(fila.get("Capacidad / Medida", "")),
                "stock": str(fila.get("Stock Actual", "Disponible")),
                "precio": str(fila.get("Precio Venta", "$ Consultar")),
                "norma": str(fila.get("Norma / Certificación", "IRAM"))
            })
        return productos
    except Exception as e:
        print(f"Error al conectar con Google Sheets: {e}")
        return []

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Procesamiento del formulario rápido de cotización hacia WhatsApp
        nombre = request.form.get('nombre', '').strip()
        empresa = request.form.get('empresa', '').strip()
        servicio = request.form.get('servicio', 'Recarga general de matafuegos')
        detalles = request.form.get('detalles', '').strip()
        
        texto = f"Hola! Soy {nombre}"
        if empresa:
            texto += f" de {empresa}"
        texto += f". Necesito asesoramiento / cotización urgente sobre: {servicio}."
        if detalles:
            texto += f" Detalles: {detalles}"
            
        mensaje_encoded = urllib.parse.quote(texto)
        whatsapp_url = f"https://wa.me/{WHATSAPP_NUMERO}?text={mensaje_encoded}"
        
        return redirect(whatsapp_url)
    
    # Cargamos el catálogo completo desde Google Sheets en tiempo real
    catalogo = cargar_catalogo_desde_sheets()
    
    # Manejo de búsqueda por término (SKU, nombre o categoría)
    busqueda = request.args.get('q', '').lower().strip()
    if busqueda:
        catalogo = [
            p for p in catalogo 
            if busqueda in p['nombre'].lower() or 
               busqueda in p['sku'].lower() or 
               busqueda in p['categoria'].lower() or
               busqueda in p['tipo'].lower()
        ]
    
    # Mostramos los primeros 60 productos en pantalla para agilizar la carga visual, 
    # mientras el buscador permite filtrar los 1.500 ítems al instante.
    productos_visibles = catalogo[:60]
    
    return render_template(
        'index.html', 
        productos=productos_visibles, 
        total_productos=len(catalogo), 
        busqueda=busqueda
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)

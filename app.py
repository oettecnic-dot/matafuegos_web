from flask import Flask, render_template, request, redirect, url_for
import urllib.parse
import os
import re
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)
app.secret_key = 'matafuegos_seguridad_consorcios_2026'

# Tu número de WhatsApp de contacto comercial
WHATSAPP_NUMERO = "5491161726657"

# Configuración de credenciales y conexión a Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
CREDENTIALS_FILE = 'credentials.json'

def cargar_catalogo_desde_sheets():
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            return []
            
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open("Catalogo_Matafuegos_1500").sheet1
        registros = sheet.get_all_records()
        
        productos = []
        for index, fila in enumerate(registros):
            precio_str = str(fila.get("Precio Venta", "0"))
            precio_num = re.sub(r'[^\d]', '', precio_str)
            precio_val = int(precio_num) if precio_num else 0
            
            productos.append({
                "id": index + 1,
                "sku": str(fila.get("SKU", f"MAT-{index+1:04d}")),
                "categoria": str(fila.get("Categoría", "General")),
                "tipo": str(fila.get("Subcategoría / Tipo", "")),
                "nombre": str(fila.get("Descripción del Producto", "Artículo")),
                "peso": str(fila.get("Capacidad / Medida", "")),
                "stock": str(fila.get("Stock Actual", "Disponible")),
                "precio_str": precio_str,
                "precio_val": precio_val,
                "norma": str(fila.get("Norma / Certificación", "IRAM"))
            })
        return productos
    except Exception as e:
        print(f"Error al conectar con Google Sheets: {e}")
        return []

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        empresa = request.form.get('empresa', '').strip()
        servicio = request.form.get('servicio', 'Recarga general')
        detalles = request.form.get('detalles', '').strip()
        
        catalogo = cargar_catalogo_desde_sheets()
        presupuesto_texto = ""
        total_calculado = 0
        
        if catalogo:
            texto_completo = f"{servicio} {detalles}".lower()
            texto_limpio = texto_completo.replace(" ", "")
            
            # 1. Extraer la cantidad (por defecto 1 si no se especifica)
            match_cant = re.search(r'(\d+)\s*(?:matafuegos|unidades|equipos|cargas|litros|kg)?', texto_completo)
            cantidad = int(match_cant.group(1)) if match_cant and int(match_cant.group(1)) > 0 else 1
            
            # 2. Extraer capacidad o peso (ej: 10 kg, 5 kg)
            match_peso = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:kg|lt|lts)', texto_completo)
            peso_buscado = match_peso.group(1).replace(',', '.') if match_peso else None
            peso_buscado_limpio = peso_buscado + "kg" if peso_buscado else None
            
            item_encontrado = None
            
            # Búsqueda inteligente si es recarga
            if "recarga" in texto_completo:
                if peso_buscado_limpio:
                    # Buscamos en recargas uniendo strings para ignorar espacios y diferencias (ej: "10kg")
                    item_encontrado = next((p for p in catalogo if "recarga" in p['categoria'].lower() and (peso_buscado_limpio in p['peso'].lower().replace(" ", "") or peso_buscado_limpio in p['nombre'].lower().replace(" ", ""))), None)
                if not item_encontrado:
                    # Respaldo buscando por número de kilo (ej: "10") dentro de la categoría recargas
                    item_encontrado = next((p for p in catalogo if "recarga" in p['categoria'].lower() and peso_buscado in p['nombre'] if peso_buscado), None)
                if not item_encontrado:
                    item_encontrado = next((p for p in catalogo if "recarga" in p['categoria'].lower() and "10" in p['nombre']), None)
            
            # Si no es recarga, buscamos en el catálogo general por peso
            if not item_encontrado and peso_buscado_limpio:
                item_encontrado = next((p for p in catalogo if peso_buscado_limpio in p['peso'].lower().replace(" ", "") or peso_buscado_limpio in p['nombre'].lower().replace(" ", "")), None)
            
            # Respaldo por palabras clave (Hidráulica, ABC, CO2)
            if not item_encontrado:
                if "hidráulica" in texto_completo or "hidraulica" in texto_completo:
                    item_encontrado = next((p for p in catalogo if "hidráulica" in p['nombre'].lower() or "hidraulica" in p['nombre'].lower()), None)
                elif "abc" in texto_completo:
                    item_encontrado = next((p for p in catalogo if "abc" in p['nombre'].lower() or "abc" in p['tipo'].lower()), None)
                elif "co2" in texto_completo:
                    item_encontrado = next((p for p in catalogo if "co2" in p['nombre'].lower() or "co2" in p['tipo'].lower()), None)

            # 3. Cálculo del subtotal y armado del desglose
            if item_encontrado:
                subtotal = item_encontrado['precio_val'] * cantidad
                total_calculado += subtotal
                presupuesto_texto = f"\n- [{item_encontrado['sku']}] {cantidad}x {item_encontrado['nombre']} ({item_encontrado['peso']}): ${subtotal:,.0f} (Unit: {item_encontrado['precio_str']})"

        # Armar el mensaje final para WhatsApp
        texto = f"Hola! Soy {nombre}"
        if empresa:
            texto += f" de {empresa}"
        texto += f". Solicito cotización sobre: {servicio}."
        if detalles:
            texto += f" Detalles: {detalles}."
            
        if presupuesto_texto:
            texto += f"\n\n*Presupuesto Automático Catálogo:*{presupuesto_texto}"
            if total_calculado > 0:
                texto += f"\n👉 **TOTAL ESTIMADO: ${total_calculado:,.0f}**"
            
        mensaje_encoded = urllib.parse.quote(texto)
        whatsapp_url = f"https://wa.me/{WHATSAPP_NUMERO}?text={mensaje_encoded}"
        
        return redirect(whatsapp_url)
    
    catalogo = cargar_catalogo_desde_sheets()
    busqueda = request.args.get('q', '').lower().strip()
    if busqueda:
        catalogo = [
            p for p in catalogo 
            if busqueda in p['nombre'].lower() or 
               busqueda in p['sku'].lower() or 
               busqueda in p['categoria'].lower() or
               busqueda in p['tipo'].lower()
        ]
    
    productos_visibles = catalogo[:60]
    return render_template('index.html', productos=productos_visibles, total_productos=len(catalogo), busqueda=busqueda)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

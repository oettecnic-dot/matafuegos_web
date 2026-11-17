from flask import Flask, render_template, request, redirect
import urllib.parse
import os
import json
import re
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)
app.secret_key = 'matafuegos_seguridad_consorcios_2026'

# Tu número de WhatsApp de contacto comercial
WHATSAPP_NUMERO = "5491161726657"

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def cargar_catalogo_desde_sheets():
    productos = []
    try:
        creds = None
        # 1. Si estamos en Render, lee la variable de entorno con el JSON
        if os.environ.get('GOOGLE_CREDENTIALS_JSON'):
            creds_json = json.loads(os.environ.get('GOOGLE_CREDENTIALS_JSON'))
            creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
        # 2. Si estamos en local y existe el archivo físico, usa el archivo
        elif os.path.exists('credentials.json'):
            creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
            
        if creds:
            client = gspread.authorize(creds)
            sheet = client.open("Catalogo_Matafuegos_1500").sheet1
            registros = sheet.get_all_records()
            
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
    except Exception as e:
        print(f"Error al conectar con Google Sheets: {e}")

    # Catálogo de respaldo por seguridad si llega a haber algún problema puntual
    if not productos:
        productos = [
            {"sku": "MAT-0004", "categoria": "Matafuegos", "tipo": "ABC", "nombre": "Matafuego Polvo Químico Seco ABC", "peso": "10 kg", "precio_str": "$93,840", "precio_val": 93840, "norma": "IRAM"},
            {"sku": "REC-0018", "categoria": "Recargas", "tipo": "Mantenimiento", "nombre": "Servicio Recarga Polvo ABC 10kg", "peso": "10 kg", "precio_str": "$27,750", "precio_val": 27750, "norma": "IRAM"},
            {"sku": "REC-0020", "categoria": "Recargas", "tipo": "Prueba Hidráulica", "nombre": "Ensayo Presión Hidrostática Quinquenal", "peso": "Universal", "precio_str": "$24,000", "precio_val": 24000, "norma": "IRAM"}
        ]
        
    return productos

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        empresa = request.form.get('empresa', '').strip()
        servicio = request.form.get('servicio', 'Recarga general')
        detalles = request.form.get('detalles', '').strip()
        
        texto_completo = f"{servicio} {detalles}".lower()
        
        # 1. Extraer cantidad numérica (por defecto 1)
        match_cant = re.search(r'(\d+)', texto_completo)
        cantidad = int(match_cant.group(1)) if match_cant else 1
        
        # 2. Extraer peso o capacidad (ej: 5, 10, 2.5)
        match_peso = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:kg|lt|lts)?', texto_completo)
        peso_buscado = match_peso.group(1).replace(',', '.') if match_peso else "10"
        
        # Valores por defecto de respaldo
        precio_unitario_val = 27750
        precio_str = "$27,750"
        sku_item = "REC-0018"
        nombre_item = f"Servicio / Producto ({peso_buscado}kg)"
        peso_item = f"{peso_buscado} kg"
        
        # 3. Búsqueda inteligente en Google Sheets o respaldo
        try:
            catalogo = cargar_catalogo_desde_sheets()
            if catalogo:
                item_encontrado = None
                
                # Buscar coincidencia exacta según lo que pidió el usuario (ej: hidráulica o recarga)
                for p in catalogo:
                    nombre_p = p['nombre'].lower()
                    cat_p = p['categoria'].lower()
                    peso_p = p['peso'].lower()
                    
                    # Si pide prueba hidráulica
                    if "hidráulica" in texto_completo or "hidraulica" in texto_completo:
                        if "hidráulica" in nombre_p or "hidraulica" in nombre_p or "ensayo" in nombre_p:
                            item_encontrado = p
                            break
                    # Si pide recarga y coincide el peso
                    elif "recarga" in texto_completo:
                        if "recarga" in cat_p or "recarga" in nombre_p:
                            if peso_buscado in peso_p or peso_buscado in nombre_p:
                                item_encontrado = p
                                break
                
                # Si no halló por servicio específico, buscamos por el peso exacto en cualquier ítem
                if not item_encontrado:
                    for p in catalogo:
                        if peso_buscado in p['peso'].lower() or peso_buscado in p['nombre'].lower():
                            item_encontrado = p
                            break
                
                # Si encontró un producto válido, actualizamos los datos
                if item_encontrado:
                    precio_unitario_val = item_encontrado['precio_val']
                    precio_str = item_encontrado['precio_str']
                    sku_item = item_encontrado['sku']
                    nombre_item = item_encontrado['nombre']
                    peso_item = item_encontrado['peso']
                    
        except Exception as e:
            print(f"Error al buscar en catálogo: {e}")

        # 4. Cálculo matemático exacto del subtotal
        subtotal = precio_unitario_val * cantidad
        
        # 5. Construcción del bloque de presupuesto unido al mensaje
        presupuesto_texto = f"\n- [{sku_item}] {cantidad}x {nombre_item} ({peso_item}): ${subtotal:,.0f} (Unit: {precio_str})"

        # 6. Armar el mensaje completo y unificado para WhatsApp
        texto = f"Hola! Soy {nombre}"
        if empresa:
            texto += f" de {empresa}"
        texto += f". Solicito cotización sobre: {servicio}."
        if detalles:
            texto += f" Detalles: {detalles}."
            
        texto += f"\n\n*Presupuesto Automático Catálogo:*{presupuesto_texto}"
        texto += f"\n👉 **TOTAL ESTIMADO: ${subtotal:,.0f}**"
            
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

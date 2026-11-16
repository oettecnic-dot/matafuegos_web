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
            {"sku": "REC-0018", "categoria": "Recargas", "tipo": "Mantenimiento", "nombre": "Servicio Recarga Polvo ABC 10kg", "peso": "10 kg", "precio_str": "$27,750", "precio_val": 27750, "norma": "IRAM"}
        ]
        
    return productos

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
        
        # Si por alguna razón el catálogo viene vacío, usamos un ítem por defecto garantizado
        if not catalogo:
            catalogo = [
                {"sku": "REC-0018", "categoria": "Recargas", "tipo": "Mantenimiento", "nombre": "Servicio Recarga Polvo ABC 10kg", "peso": "10 kg", "precio_str": "$27,750", "precio_val": 27750, "norma": "IRAM"}
            ]

        texto_completo = f"{servicio} {detalles}".lower()
        
        # 1. Extraer cantidad (por defecto 1)
        match_cant = re.search(r'(\d+)', texto_completo)
        cantidad = int(match_cant.group(1)) if match_cant else 1
        
        # 2. Extraer peso o capacidad (ej: 10, 5, 2.5)
        match_peso = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:kg|lt|lts)?', texto_completo)
        peso_buscado = match_peso.group(1).replace(',', '.') if match_peso else "10"
        
        item_encontrado = None
        
        # Búsqueda directa por peso y tipo en el catálogo
        for p in catalogo:
            nombre_p = p['nombre'].lower()
            peso_p = p['peso'].lower()
            cat_p = p['categoria'].lower()
            
            # Si el usuario pidió recarga y el producto es recarga y coincide el peso
            if "recarga" in texto_completo and ("recarga" in cat_p or "recarga" in nombre_p):
                if peso_buscado in peso_p or peso_buscado in nombre_p:
                    item_encontrado = p
                    break
        
        # Si no lo encontró específico, buscamos cualquier producto que tenga ese peso
        if not item_encontrado:
            for p in catalogo:
                if peso_buscado in p['peso'].lower() or peso_buscado in p['nombre'].lower():
                    item_encontrado = p
                    break
                    
        # Si aún así no hay coincidencia, tomamos el primer ítem de recarga o el primero del catálogo para que nunca falle
        if not item_encontrado:
            item_encontrado = catalogo[0]

        # 3. Cálculo del subtotal
        if item_encontrado:
            subtotal = item_encontrado['precio_val'] * cantidad
            total_calculado += subtotal
            presupuesto_texto = f"\n- [{item_encontrado['sku']}] {cantidad}x {item_encontrado['nombre']} ({item_encontrado['peso']}): ${subtotal:,.0f} (Unit: {item_encontrado['precio_str']})"

        # Armar el mensaje final para WhatsApp con el presupuesto garantizado
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

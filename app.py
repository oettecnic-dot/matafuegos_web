import json
import os
import re
import urllib.parse
import urllib.request
from flask import Flask, render_template, request

app = Flask(__name__)

WHATSAPP_NUMBER = "5491161726657"
EMPRESA_NOMBRE = "L y L MATAGUEGOS — SEGURIDAD"


def extraer_precio(fila):
    for clave in ("Precio Venta", "Precio", "Precio Unitario", "Precio_Venta", "precio"):
        if clave in fila and fila[clave] not in (None, ""):
            raw = str(fila[clave]).strip()
            if re.fullmatch(r"\d+\.0+", raw):
                raw = raw.split(".")[0]
            digitos = re.sub(r"[^\d]", "", raw)
            if digitos:
                return raw, int(digitos)
    return "", 0


def cargar_catalogo_desde_sheets():
    productos = []
    webhook_url = os.environ.get("CATALOG_WEBHOOK_URL", "").strip()

    if webhook_url:
        try:
            req = urllib.request.Request(
                webhook_url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_data = resp.read().decode("utf-8")
                registros = json.loads(raw_data)

            if isinstance(registros, list):
                for index, fila in enumerate(registros):
                    if not isinstance(fila, dict):
                        continue
                    precio_str, precio_val = extraer_precio(fila)
                    nombre = str(
                        fila.get("Descripción del Producto")
                        or fila.get("Producto")
                        or fila.get("Nombre")
                        or "Artículo"
                    ).strip()
                    peso = str(
                        fila.get("Capacidad / Medida")
                        or fila.get("Capacidad")
                        or fila.get("Medida")
                        or ""
                    ).strip()

                    productos.append({
                        "id": index + 1,
                        "sku": str(fila.get("SKU") or f"MAT-{index+1:04d}").strip(),
                        "categoria": str(fila.get("Categoría") or fila.get("Categoria") or "General").strip(),
                        "tipo": str(fila.get("Subcategoría / Tipo") or fila.get("Tipo") or "").strip(),
                        "nombre": nombre,
                        "peso": peso,
                        "stock": str(fila.get("Stock Actual") or "Disponible").strip(),
                        "precio_str": precio_str if precio_str else (f"${precio_val:,}" if precio_val else "A consultar"),
                        "precio_val": precio_val,
                        "norma": str(fila.get("Norma / Certificación") or "IRAM").strip()
                    })
        except Exception as e:
            print(f"Error al leer Apps Script ({webhook_url}): {e}")

    # Catálogo de respaldo si no hay respuesta del webhook o todavía no se cargó
    if not productos:
        productos = [
            {"sku": "MAT-0002", "categoria": "Matafuegos", "tipo": "ABC", "nombre": "Matafuego Polvo Químico Seco ABC", "peso": "5 kg", "precio_str": "$62,500", "precio_val": 62500, "norma": "IRAM"},
            {"sku": "MAT-0004", "categoria": "Matafuegos", "tipo": "ABC", "nombre": "Matafuego Polvo Químico Seco ABC", "peso": "10 kg", "precio_str": "$93,840", "precio_val": 93840, "norma": "IRAM"},
            {"sku": "REC-0015", "categoria": "Recargas", "tipo": "Mantenimiento", "nombre": "Servicio Recarga Polvo ABC 5kg", "peso": "5 kg", "precio_str": "$21,500", "precio_val": 21500, "norma": "IRAM"},
            {"sku": "REC-0018", "categoria": "Recargas", "tipo": "Mantenimiento", "nombre": "Servicio Recarga Polvo ABC 10kg", "peso": "10 kg", "precio_str": "$27,750", "precio_val": 27750, "norma": "IRAM"},
            {"sku": "REC-0020", "categoria": "Recargas", "tipo": "Prueba Hidráulica", "nombre": "Ensayo Presión Hidrostática Quinquenal", "peso": "Universal", "precio_str": "$24,000", "precio_val": 24000, "norma": "IRAM"},
            {"sku": "SEG-0101", "categoria": "Seguridad", "tipo": "Iluminación", "nombre": "Luz de Emergencia LED 60 Leds Autonomía 6hs", "peso": "Unidad", "precio_str": "$18,500", "precio_val": 18500, "norma": "IRAM"},
            {"sku": "CAR-0201", "categoria": "Cartelería", "tipo": "Señalización", "nombre": "Cartel Señalización Salida / Emergencia Fotoluminiscente", "peso": "30x15 cm", "precio_str": "$6,500", "precio_val": 6500, "norma": "IRAM"},
            {"sku": "CAR-0202", "categoria": "Cartelería", "tipo": "Señalización", "nombre": "Cartel Chapa Matafuego ABC reglamentario", "peso": "25x25 cm", "precio_str": "$5,800", "precio_val": 5800, "norma": "IRAM"},
            {"sku": "SEG-0105", "categoria": "Seguridad", "tipo": "Accesorios", "nombre": "Soporte Baliza / Gancho Pared para Matafuego", "peso": "Unidad", "precio_str": "$4,500", "precio_val": 4500, "norma": "IRAM"}
        ]

    return productos


def normalizar_texto(texto):
    texto = texto.lower().strip()
    reemplazos = (
        ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
        ("ü", "u"), ("ñ", "n")
    )
    for origen, destino in reemplazos:
        texto = texto.replace(origen, destino)
    return texto


def extraer_cantidad_y_texto(linea_texto):
    limpio = (linea_texto or "").strip()
    match = re.match(r"^\s*(\d+)\s*(?:x\s*)?(.*)$", limpio, flags=re.IGNORECASE)
    if match:
        cantidad = max(1, int(match.group(1)))
        resto = match.group(2).strip()
        return cantidad, (resto if resto else limpio)
    return 1, limpio


def buscar_producto_en_catalogo(linea_texto, catalogo):
    cantidad, texto_sin_cant = extraer_cantidad_y_texto(linea_texto)
    texto_norm = normalizar_texto(texto_sin_cant)

    peso_buscado = None
    if re.search(r"\b10\s*kg\b", texto_norm):
        peso_buscado = "10 kg"
    elif re.search(r"\b5\s*kg\b", texto_norm):
        peso_buscado = "5 kg"

    mejor_item = None
    mejor_puntaje = 0

    for prod in catalogo:
        nombre_norm = normalizar_texto(prod.get("nombre", ""))
        cat_norm = normalizar_texto(prod.get("categoria", ""))
        tipo_norm = normalizar_texto(prod.get("tipo", ""))
        peso_norm = normalizar_texto(prod.get("peso", ""))
        sku_norm = normalizar_texto(prod.get("sku", ""))

        puntaje = 0
        if sku_norm and sku_norm in texto_norm:
            puntaje += 50

        palabras = [p for p in re.findall(r"[a-z0-9]+", texto_norm) if len(p) > 2 and p != "kg"]
        for palabra in palabras:
            if palabra in nombre_norm:
                puntaje += 10
            elif palabra in tipo_norm or palabra in cat_norm or palabra in peso_norm:
                puntaje += 6

        if peso_buscado:
            if normalizar_texto(peso_buscado) in peso_norm or normalizar_texto(peso_buscado) in nombre_norm:
                puntaje += 15
            else:
                puntaje -= 10

        if "recarga" in texto_norm and ("recarga" in nombre_norm or "recarga" in cat_norm):
            puntaje += 12
        if ("hidraulica" in texto_norm or "prueba" in texto_norm) and ("hidrostatica" in nombre_norm or "hidraulica" in tipo_norm):
            puntaje += 12
        if ("luz" in texto_norm or "emergencia" in texto_norm) and "emergencia" in nombre_norm:
            puntaje += 10
        if ("cartel" in texto_norm or "senal" in texto_norm) and ("cartel" in nombre_norm or "carteleria" in cat_norm):
            puntaje += 10

        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_item = prod

    if mejor_item and mejor_puntaje > 0:
        precio_unit = int(mejor_item.get("precio_val", 0))
        subtotal = precio_unit * cantidad
        nombre_prod = mejor_item.get("nombre", "")
        peso_prod = mejor_item.get("peso", "")
        descripcion = (
            f"{nombre_prod} ({peso_prod})".strip()
            if peso_prod and peso_prod.lower() not in nombre_prod.lower()
            else nombre_prod
        )
        return {
            "cantidad": cantidad,
            "sku": mejor_item.get("sku", ""),
            "descripcion": descripcion,
            "precio_unit": precio_unit,
            "subtotal": subtotal,
            "encontrado": True
        }

    return {
        "cantidad": cantidad,
        "sku": "CONSULTA",
        "descripcion": texto_sin_cant,
        "precio_unit": 0,
        "subtotal": 0,
        "encontrado": False
    }


def armar_cotizacion(detalle_texto, catalogo):
    lineas = [l.strip() for l in re.split(r"[\n,;]+", detalle_texto or "") if l.strip()]
    items = [buscar_producto_en_catalogo(linea, catalogo) for linea in lineas]
    total = sum(item["subtotal"] for item in items)
    return items, total


def filtrar_catalogo(catalogo, consulta):
    q_norm = normalizar_texto(consulta or "")
    if not q_norm:
        return catalogo

    terminos = re.findall(r"[a-z0-9]+", q_norm)
    if not terminos:
        return catalogo

    filtrados = []
    for prod in catalogo:
        texto_prod = " ".join([
            normalizar_texto(str(prod.get("sku", ""))),
            normalizar_texto(str(prod.get("categoria", ""))),
            normalizar_texto(str(prod.get("tipo", ""))),
            normalizar_texto(str(prod.get("nombre", ""))),
            normalizar_texto(str(prod.get("peso", ""))),
            normalizar_texto(str(prod.get("norma", "")))
        ])
        if all(t in texto_prod for t in terminos):
            filtrados.append(prod)

    return filtrados


@app.route("/", methods=["GET", "POST"])
def index():
    catalogo = cargar_catalogo_desde_sheets()
    busqueda = request.args.get("q", "").strip()
    productos_visibles = filtrar_catalogo(catalogo, busqueda)

    whatsapp_url = None
    resumen_items = []
    total_estimado = 0
    mensaje_preview = ""

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        empresa_cliente = request.form.get("empresa", "").strip()
        servicio = request.form.get("servicio", "").strip()
        detalle = (request.form.get("detalles") or request.form.get("detalle") or "").strip()

        resumen_items, total_estimado = armar_cotizacion(detalle, catalogo)

        lineas_msg = [
            f"Hola *{EMPRESA_NOMBRE}*, solicito cotización:",
            f"• *Nombre:* {nombre or 'No especificado'}",
        ]
        if empresa_cliente:
            lineas_msg.append(f"• *Empresa / Consorcio:* {empresa_cliente}")
        if servicio:
            lineas_msg.append(f"• *Servicio / Solicitud:* {servicio}")

        lineas_msg.extend(["", "*Detalle solicitado:*"])

        for it in resumen_items:
            if it["encontrado"] and it["precio_unit"] > 0:
                lineas_msg.append(
                    f"- {it['cantidad']}x {it['descripcion']} (${it['precio_unit']:,} c/u) = *${it['subtotal']:,}*"
                )
            else:
                lineas_msg.append(f"- {it['cantidad']}x {it['descripcion']} _(a cotizar)_")

        if total_estimado > 0:
            lineas_msg.extend(["", f"*Total estimado:* *${total_estimado:,}*"])

        mensaje_preview = "\n".join(lineas_msg)
        whatsapp_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={urllib.parse.quote(mensaje_preview)}"

    return render_template(
        "index.html",
        empresa=EMPRESA_NOMBRE,
        productos=productos_visibles,
        busqueda=busqueda,
        total_productos=len(productos_visibles),
        whatsapp_url=whatsapp_url,
        resumen_items=resumen_items,
        total_estimado=total_estimado,
        mensaje_preview=mensaje_preview
    )


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto, debug=False)

import json
import os
import re
import urllib.parse
import urllib.request
from flask import Flask, render_template, request

app = Flask(__name__)

WHATSAPP_NUMBER = "5491161726657"
EMPRESA_NOMBRE = "L y L MATAGUEGOS — SEGURIDAD"


def parsear_entero_precio(valor) -> int:
    if valor is None or isinstance(valor, bool):
        return 0
    if isinstance(valor, (int, float)):
        return int(round(valor)) if valor > 0 else 0

    texto = str(valor).strip()
    if not texto:
        return 0

    limpio = re.sub(r"[^\d.,-]", "", texto)
    if not limpio:
        return 0

    if re.search(r",\d{1,2}$", limpio):
        limpio = limpio.split(",")[0]
    elif re.search(r"\.\d{1,2}$", limpio):
        limpio = limpio.split(".")[0]

    solo_digitos = re.sub(r"[^\d]", "", limpio)
    return int(solo_digitos) if solo_digitos else 0


def obtener_campo(fila: dict, *claves, default=""):
    for clave in claves:
        if clave in fila and fila[clave] is not None and str(fila[clave]).strip() != "":
            return str(fila[clave]).strip()

    mapa_lower = {str(k).strip().lower(): v for k, v in fila.items()}
    for clave in claves:
        val = mapa_lower.get(str(clave).strip().lower())
        if val is not None and str(val).strip() != "":
            return str(val).strip()

    return default


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

            if isinstance(registros, dict):
                for key in ("data", "items", "productos", "records"):
                    if isinstance(registros.get(key), list):
                        registros = registros[key]
                        break

            if isinstance(registros, list):
                for index, fila in enumerate(registros):
                    if not isinstance(fila, dict):
                        continue

                    nombre_prod = obtener_campo(
                        fila,
                        "Descripción del Producto",
                        "Descripcion del Producto",
                        "Producto/ Variedad",
                        "Nombre",
                        default=""
                    )
                    precio_raw = obtener_campo(
                        fila,
                        "Precio Venta",
                        "Precio ($)",
                        "Precio",
                        "precio_venta",
                        "precio",
                        default="0"
                    )
                    precio_val = parsear_entero_precio(precio_raw)

                    # Descarta filas vacías, sin descripción real o sin precio válido
                    if not nombre_prod or nombre_prod.lower() == "artículo" or precio_val <= 0:
                        continue

                    precio_str = (
                        precio_raw
                        if "$" in precio_raw
                        else f"${precio_val:,}"
                    )

                    productos.append({
                        "id": len(productos) + 1,
                        "sku": obtener_campo(fila, "SKU", "Codigo", "Código", default=f"MAT-{index+1:04d}"),
                        "categoria": obtener_campo(fila, "Categoría", "Categoria", default="General"),
                        "tipo": obtener_campo(fila, "Subcategoría / Tipo", "Subcategoria / Tipo", "Tipo", default=""),
                        "nombre": nombre_prod,
                        "peso": obtener_campo(fila, "Capacidad / Medida", "Capacidad", "Medida", "Peso", default=""),
                        "stock": obtener_campo(fila, "Stock Actual", "Stock", default="Disponible"),
                        "precio_str": precio_str,
                        "precio_val": precio_val,
                        "norma": obtener_campo(fila, "Norma / Certificación", "Norma", default="IRAM")
                    })
        except Exception as e:
            print(f"Error al leer Apps Script ({webhook_url}): {e}")

    # Catálogo de respaldo si no hay respuesta del webhook o no se cargaron filas válidas
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
    texto = str(texto or "").lower().strip()
    reemplazos = (
        ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
        ("ü", "u"), ("ñ", "n")
    )
    for origen, destino in reemplazos:
        texto = texto.replace(origen, destino)
    texto = re.sub(r"(\d+)(kg|gr|g|lts|l|cm|mm)\b", r"\1 \2", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def extraer_cantidad_y_limpiar(linea_texto: str):
    limpia = linea_texto.strip()
    cantidad = 1

    match_prefijo = re.match(r"^\s*(?:x\s*)?(\d+)\s*(?:x|\*)?\s+", limpia, re.I)
    if match_prefijo:
        cantidad = max(1, int(match_prefijo.group(1)))
        limpia = limpia[match_prefijo.end():].strip()
    else:
        match_num = re.search(r"\b(\d+)\b", limpia)
        if match_num:
            cantidad = max(1, int(match_num.group(1)))

    return cantidad, limpia


def buscar_producto_en_catalogo(linea_texto, catalogo):
    cantidad, texto_limpio = extraer_cantidad_y_limpiar(linea_texto)
    texto_norm = normalizar_texto(texto_limpio)

    peso_buscado = None
    if re.search(r"\b10\s*kg\b", texto_norm):
        peso_buscado = "10 kg"
    elif re.search(r"\b5\s*kg\b", texto_norm):
        peso_buscado = "5 kg"

    palabras = [
        p for p in re.findall(r"[a-z0-9]+", texto_norm)
        if len(p) >= 2 or p.isdigit()
    ]

    mejor_item = None
    mejor_puntaje = 0

    for prod in catalogo:
        nombre_norm = normalizar_texto(prod.get("nombre", ""))
        cat_norm = normalizar_texto(prod.get("categoria", ""))
        tipo_norm = normalizar_texto(prod.get("tipo", ""))
        peso_norm = normalizar_texto(prod.get("peso", ""))
        sku_norm = normalizar_texto(prod.get("sku", ""))
        union_prod = f"{nombre_norm} {cat_norm} {tipo_norm} {peso_norm}"

        puntaje = 0
        if sku_norm and sku_norm in texto_norm:
            puntaje += 50

        for palabra in palabras:
            if palabra in nombre_norm:
                puntaje += 10
            elif palabra in tipo_norm or palabra in cat_norm or palabra in peso

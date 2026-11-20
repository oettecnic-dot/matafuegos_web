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

  # Quita símbolos de moneda y espacios
  limpio = re.sub(r"[^\d.,-]", "", texto)
  if not limpio:
    return 0

  # Si tiene coma o punto decimal al final (ej: 62500.00 o 62.500,00)
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
  # Búsqueda insensible a mayúsculas/minúsculas como respaldo
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
          webhook_url, headers={"User-Agent": "Mozilla/5.0"}
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

          precio_raw = obtener_campo(
              fila,
              "Precio Venta",
              "Precio ($)",
              "Precio",
              "precio_venta",
              "precio",
              default="0",
          )
          precio_val = parsear_entero_precio(precio_raw)
          precio_str = (
              precio_raw
              if "$" in precio_raw
              else (f"${precio_val:,}" if precio_val > 0 else "A consultar")
          )

          productos.append({
              "id": index + 1,
              "sku": obtener_campo(
                  fila, "SKU", "Codigo", "Código", default=f"MAT-{index+1:04d}"
              ),
              "categoria": obtener_campo(
                  fila, "Categoría", "Categoria", default="General"
              ),
              "tipo": obtener_campo(
                  fila,
                  "Subcategoría / Tipo",
                  "Subcategoria / Tipo",
                  "Tipo",
                  default="",
              ),
              "nombre": obtener_campo(
                  fila,
                  "Descripción del Producto",
                  "Descripcion del Producto",
                  "Producto/ Variedad",
                  "Nombre",
                  default="Artículo",
              ),
              "peso": obtener_campo(
                  fila,
                  "Capacidad / Medida",
                  "Capacidad",
                  "Medida",
                  "Peso",
                  default="",
              ),
              "stock": obtener_campo(
                  fila, "Stock Actual", "Stock", default="Disponible"
              ),
              "precio_str": precio_str,
              "precio_val": precio_val,
              "norma": obtener_campo(
                  fila, "Norma / Certificación", "Norma", default="IRAM"
              ),
          })
    except Exception as e:
      print(f"Error al leer Apps Script ({webhook_url}): {e}")

  if not productos:
    productos = [
        {
            "sku": "MAT-0002",
            "categoria": "Matafuegos",
            "tipo": "ABC",
            "nombre": "Matafuego Polvo Químico Seco ABC",
            "peso": "5 kg",
            "precio_str": "$62,500",
            "precio_val": 62500,
            "norma": "IRAM",
        },
        {
            "sku": "MAT-0004",
            "categoria": "Matafuegos",
            "tipo": "ABC",
            "nombre": "Matafuego Polvo Químico Seco ABC",
            "peso": "10 kg",
            "precio_str": "$93,840",
            "precio_val": 93840,
            "norma": "IRAM",
        },
        {
            "sku": "REC-0015",
            "categoria": "Recargas",
            "tipo": "Mantenimiento",
            "nombre": "Servicio Recarga Polvo ABC 5kg",
            "peso": "5 kg",
            "precio_str": "$21,500",
            "precio_val": 21500,
            "norma": "IRAM",
        },
        {
            "sku": "REC-0018",
            "categoria": "Recargas",
            "tipo": "Mantenimiento",
            "nombre": "Servicio Recarga Polvo ABC 10kg",
            "peso": "10 kg",
            "precio_str": "$27,750",
            "precio_val": 27750,
            "norma": "IRAM",
        },
        {
            "sku": "REC-0020",
            "categoria": "Recargas",
            "tipo": "Prueba Hidráulica",
            "nombre": "Ensayo Presión Hidrostática Quinquenal",
            "peso": "Universal",
            "precio_str": "$24,000",
            "precio_val": 24000,
            "norma": "IRAM",
        },
        {
            "sku": "SEG-0101",
            "categoria": "Seguridad",
            "tipo": "Iluminación",
            "nombre": "Luz de Emergencia LED 60 Leds Autonomía 6hs",
            "peso": "Unidad",
            "precio_str": "$18,500",
            "precio_val": 18500,
            "norma": "IRAM",
        },
        {
            "sku": "CAR-0201",
            "categoria": "Cartelería",
            "tipo": "Señalización",
            "nombre": "Cartel Señalización Salida / Emergencia Fotoluminiscente",
            "peso": "30x15 cm",
            "precio_str": "$6,500",
            "precio_val": 6500,
            "norma": "IRAM",
        },
        {
            "sku": "CAR-0202",
            "categoria": "Cartelería",
            "tipo": "Señalización",
            "nombre": "Cartel Chapa Matafuego ABC reglamentario",
            "peso": "25x25 cm",
            "precio_str": "$5,800",
            "precio_val": 5800,
            "norma": "IRAM",
        },
        {
            "sku": "SEG-0105",
            "categoria": "Seguridad",
            "tipo": "Accesorios",
            "nombre": "Soporte Baliza / Gancho Pared para Matafuego",
            "peso": "Unidad",
            "precio_str": "$4,500",
            "precio_val": 4500,
            "norma": "IRAM",
        },
    ]

  return productos


def normalizar_texto(texto):
  texto = str(texto or "").lower().strip()
  reemplazos = (
      ("á", "a"),
      ("é", "e"),
      ("í", "i"),
      ("ó", "o"),
      ("ú", "u"),
      ("ü", "u"),
      ("ñ", "n"),
  )
  for origen, destino in reemplazos:
    texto = texto.replace(origen, destino)
  # Une números pegados a unidades comunes como "5kg" -> "5 kg" y normaliza espacios
  texto = re.sub(r"(\d+)(kg|gr|g|lts|l|cm|mm)\b", r"\1 \2", texto)
  texto = re.sub(r"\s+", " ", texto).strip()
  return texto


def extraer_cantidad_y_limpiar(linea_texto: str):
  limpia = linea_texto.strip()
  cantidad = 1

  # Detecta patrones como "5x", "5 x", "x5" al inicio
  match_prefijo = re.match(r"^\s*(?:x\s*)?(\d+)\s*(?:x|\*)?\s+", limpia, re.I)
  if match_prefijo:
    cantidad = max(1, int(match_prefijo.group(1)))
    limpia = limpia[match_prefijo.end() :].strip()
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

  # Conserva palabras de >= 2 letras o números (incluye "kg", "abc", "5", "10")
  palabras = [
      p
      for p in re.findall(r"[a-z0-9]+", texto_norm)
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
      elif palabra in tipo_norm or palabra in cat_norm or palabra in peso_norm:
        puntaje += 6

    if peso_buscado:
      p_norm = normalizar_texto(peso_buscado)
      if p_norm in peso_norm or p_norm in nombre_norm:
        puntaje += 15
      else:
        puntaje -= 10

    if "recarga" in texto_norm and (
        "recarga" in nombre_norm or "recarga" in cat_norm
    ):
      puntaje += 12
    if ("hidraulica" in texto_norm or "prueba" in texto_norm) and (
        "hidrostatica" in union_prod or "hidraulica" in union_prod
    ):
      puntaje += 12
    if ("luz" in texto_norm or "emergencia" in texto_norm) and (
        "emergencia" in nombre_norm
    ):
      puntaje += 10
    if ("cartel" in texto_norm or "senal" in texto_norm) and (
        "cartel" in nombre_norm or "carteleria" in cat_norm
    ):
      puntaje += 10

    if puntaje > mejor_puntaje:
      mejor_puntaje = puntaje
      mejor_item = prod

  if mejor_item and mejor_puntaje > 0:
    precio_unit = parsear_entero_precio(mejor_item.get("precio_val", 0))
    subtotal = precio_unit * cantidad
    peso_txt = f" ({mejor_item.get('peso', '')})" if mejor_item.get("peso") else ""
    return {
        "cantidad": cantidad,
        "sku": mejor_item.get("sku", ""),
        "descripcion": f"{mejor_item.get('nombre', '')}{peso_txt}".strip(),
        "precio_unit": precio_unit,
        "subtotal": subtotal,
        "encontrado": True,
    }

  return {
      "cantidad": cantidad,
      "sku": "CONSULTA",
      "descripcion": texto_limpio or linea_texto.strip(),
      "precio_unit": 0,
      "subtotal": 0,
      "encontrado": False,
  }


def armar_cotizacion(detalle_texto, catalogo):
  lineas = [
      l.strip() for l in re.split(r"[\n,;]+", detalle_texto or "") if l.strip()
  ]
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
        normalizar_texto(str(prod.get("norma", ""))),
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
    detalle = (
        request.form.get("detalles") or request.form.get("detalle") or ""
    ).strip()

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
            f"- {it['cantidad']}x {it['descripcion']}"
            f" (${it['precio_unit']:,} c/u) = *${it['subtotal']:,}*"
        )
      else:
        lineas_msg.append(
            f"- {it['cantidad']}x {it['descripcion']} _(a cotizar)_"
        )

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
      mensaje_preview=mensaje_preview,
  )


if __name__ == "__main__":
  puerto = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=puerto, debug=False)

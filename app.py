from flask import Flask, render_template, request, redirect
import urllib.parse

app = Flask(__name__)
app.secret_key = 'clave_secreta_seguridad_matafuegos'

# Tu número de contacto registrado para el negocio
WHATSAPP_NUMERO = "5491161726657"

# Catálogo de productos para mostrar en la web
PRODUCTOS = [
    {
        "id": 1,
        "nombre": "Matafuego ABC 1 kg",
        "tipo": "Polvo Químico Seco (Vehicular)",
        "peso": "1 kg",
        "descripcion": "Ideal para automóviles, utilitarios y exigencias de VTV. Compacto y fácil de ubicar.",
        "icono": "fa-car"
    },
    {
        "id": 2,
        "nombre": "Matafuego ABC 2.5 kg",
        "tipo": "Polvo Químico Seco",
        "peso": "2.5 kg",
        "descripcion": "Recomendado para comercios pequeños, oficinas y vehículos de mayor porte.",
        "icono": "fa-store"
    },
    {
        "id": 3,
        "nombre": "Matafuego ABC 5 kg",
        "tipo": "Polvo Químico Seco (Triclase)",
        "peso": "5 kg",
        "descripcion": "El estándar obligatorio para consorcios, locales comerciales, industrias y garajes.",
        "icono": "fa-building-shield"
    },
    {
        "id": 4,
        "nombre": "Matafuego CO2 3.5 kg",
        "tipo": "Anhídrido Carbónico",
        "peso": "3.5 kg",
        "descripcion": "Especial para equipos eléctricos, tableros, servidores y espacios con electrónica sensible.",
        "icono": "fa-bolt"
    }
]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        empresa = request.form.get('empresa', '').strip()
        servicio = request.form.get('servicio', 'Recarga general')
        detalles = request.form.get('detalles', '').strip()
        
        # Armar mensaje preconfigurado para WhatsApp
        texto = f"Hola! Soy {nombre}"
        if empresa:
            texto += f" de la empresa/consorcio {empresa}"
        texto += f". Necesito cotización para: {servicio}."
        if detalles:
            texto += f" Detalles: {detalles}"
            
        mensaje_encoded = urllib.parse.quote(texto)
        whatsapp_url = f"https://wa.me/{WHATSAPP_NUMERO}?text={mensaje_encoded}"
        
        return redirect(whatsapp_url)
        
    return render_template('index.html', productos=PRODUCTOS)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

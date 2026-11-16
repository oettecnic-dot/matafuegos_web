from flask import Flask, render_template, request, redirect, flash
import urllib.parse

app = Flask(__name__)
app.secret_key = 'clave_secreta_seguridad_matafuegos'

# Tu número de contacto registrado para el negocio
WHATSAPP_NUMERO = "5491161726657"

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

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)

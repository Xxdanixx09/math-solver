from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google import genai
from PIL import Image
import io
import os

app = Flask(__name__)
CORS(app) 

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# NUEVA RUTA: Esta es la que sirve tu página web cuando entras desde el celular
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/resolver', methods=['POST'])
def resolver_problema():
    if 'imagen' not in request.files:
        return jsonify({"error": "No se subió ninguna imagen"}), 400

    file = request.files['imagen']
    modo = request.form.get('modo', 'detallado')
    
    try:
        image = Image.open(io.BytesIO(file.read()))

        instruccion_modo = ""
        if modo == 'solo_respuesta':
            instruccion_modo = "Devuelve ÚNICAMENTE la respuesta final del problema. Cero texto explicativo."
        elif modo == 'procedimiento_directo':
            instruccion_modo = "Devuelve ÚNICAMENTE las ecuaciones matemáticas paso a paso hasta llegar a la respuesta. NO uses texto explicativo."
        else:
            instruccion_modo = "Resuelve el problema paso a paso de forma detallada."

        prompt = f"""
        Eres un experto en matemáticas. El usuario te enviará una imagen con un problema.
        1. Leer e interpretar el problema.
        2. {instruccion_modo}
        3. Retornar TODO el resultado en formato HTML.
        4. Usa MathJax para TODAS las fórmulas matemáticas (usa $ para fórmulas en línea y $$ para bloques).
        5. Devuelve SOLO el texto HTML limpio sin Markdown.
        """

        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[prompt, image]
        )
        
        raw_html = response.text.strip()
        if raw_html.startswith("```html"): raw_html = raw_html.replace("```html", "", 1)
        if raw_html.startswith("```"): raw_html = raw_html.replace("```", "", 1)
        if raw_html.endswith("```"): raw_html = raw_html[::-1].replace("```", "", 1)[::-1]
            
        return jsonify({"solucion_html": raw_html.strip()})
        
    except Exception as e:
        print(f"Error interno: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # CAMBIO AQUÍ: host='0.0.0.0' permite conexiones desde tu red Wi-Fi
    app.run(host='0.0.0.0', debug=True, port=5000)
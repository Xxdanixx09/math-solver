from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google import genai
from PIL import Image
import io
import os

app = Flask(__name__)
CORS(app) 

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/resolver', methods=['POST'])
def resolver_problema():
    modo = request.form.get('modo', 'detallado')
    
    # Recogemos los datos (puede venir una imagen o un texto escrito)
    file = request.files.get('imagen')
    texto_usuario = request.form.get('codigo_texto', '').strip()

    if not file and not texto_usuario:
        return jsonify({"error": "No se subió ninguna imagen ni se escribió código."}), 400

    try:
        instruccion_modo = ""
        if modo == 'solo_respuesta':
            instruccion_modo = "Devuelve ÚNICAMENTE la respuesta final o la solución directa."
        elif modo == 'procedimiento_directo':
            instruccion_modo = "Devuelve ÚNICAMENTE el procedimiento paso a paso o código corregido, sin explicaciones extensas."
        else:
            instruccion_modo = "Resuelve el problema o explica el código paso a paso de forma detallada."

        prompt = f"""
        Eres un profesor experto en matemáticas y un desarrollador de software senior.
        Tu tarea es:
        1. {instruccion_modo}
        2. Si la respuesta incluye código, utiliza etiquetas HTML estándar <pre><code>...</code></pre> para mostrarlo limpio.
        3. Retornar TODO el resultado en formato HTML.
        4. Usa MathJax para TODAS las fórmulas matemáticas (usa $ para fórmulas en línea y $$ para bloques).
        5. Devuelve SOLO el texto HTML limpio sin usar bloques de código Markdown externos como ```html.
        """

        # Preparamos el contenido dependiendo de si envió imagen o texto
        contents = [prompt]
        if file:
            image = Image.open(io.BytesIO(file.read()))
            contents.append(image)
        if texto_usuario:
            contents.append(f"Fragmento de código o problema escrito por el usuario:\n{texto_usuario}")

        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=contents
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', debug=False, port=port)
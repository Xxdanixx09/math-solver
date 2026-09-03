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
    categoria = request.form.get('categoria', 'matematicas') # matematicas o codigo
    modo = request.form.get('modo', 'detallado')
    
    file = request.files.get('imagen')
    texto_usuario = request.form.get('codigo_texto', '').strip()

    if not file and not texto_usuario:
        return jsonify({"error": "No se proporcionó ninguna imagen ni texto."}), 400

    try:
        # Definir instrucciones según el modo de detalle
        instruccion_modo = ""
        if modo == 'solo_respuesta':
            instruccion_modo = "Devuelve ÚNICAMENTE la respuesta final o el resultado directo de forma concisa."
        elif modo == 'procedimiento_directo':
            instruccion_modo = "Devuelve ÚNICAMENTE los pasos lógicos o las ecuaciones/código de forma directa, sin texto de relleno."
        else:
            instruccion_modo = "Explica todo el proceso de forma detallada y pedagógica."

        # SEPARACIÓN DE LÓGICA: Prompt especializado para Matemáticas vs Código
        if categoria == 'matematicas':
            prompt = f"""
            Eres un profesor experto en matemáticas. El usuario te envía un problema matemático (en imagen o texto).
            Tu tarea es:
            1. {instruccion_modo}
            2. REGLA ESTRICTA DE FORMATO MATEMÁTICO: Usa fórmulas en línea ($...$) para variables sueltas o partes de oraciones, y bloques independientes ($$...$$) SOLO en líneas separadas fuera de viñetas o listas. NUNCA pongas bloques $$ dentro de viñetas <li>.
            3. Retornar TODO el resultado limpio en formato HTML.
            4. Devuelve SOLO el texto HTML limpio sin usar bloques de código Markdown externos como ```html.
            """
        else:
            prompt = f"""
            Eres un desarrollador de software senior y experto en programación. El usuario te envía un fragmento o imagen de código.
            Tu tarea es:
            1. {instruccion_modo}
            2. Analiza, corrige o explica el código fuente (Java, Python, CSS, etc.).
            3. Utiliza obligatoriamente etiquetas HTML <pre><code>...</code></pre> estilizadas para mostrar los bloques de código limpios.
            4. Retornar TODO el resultado en formato HTML.
            5. Devuelve SOLO el texto HTML limpio sin usar bloques de código Markdown externos como ```html.
            """

        contents = [prompt]
        if file:
            image = Image.open(io.BytesIO(file.read()))
            contents.append(image)
        if texto_usuario:
            contents.append(f"Contenido ingresado por el usuario:\n{texto_usuario}")

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
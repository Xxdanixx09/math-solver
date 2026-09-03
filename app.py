from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from google import genai
from PIL import Image
import io
import os

app = Flask(__name__)
CORS(app) 
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-key-math-solver")

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route('/')
def home():
    session.clear()
    return render_template('index.html')

@app.route('/resolver', methods=['POST'])
def resolver_problema():
    categoria = request.form.get('categoria', 'matematicas')
    modo = request.form.get('modo', 'detallado')
    
    file = request.files.get('imagen')
    texto_usuario = request.form.get('codigo_texto', '').strip()

    if not file and not texto_usuario:
        return jsonify({"error": "No se proporcionó ninguna imagen ni texto."}), 400

    try:
        instruccion_modo = ""
        if modo == 'solo_respuesta':
            instruccion_modo = "Devuelve ÚNICAMENTE la respuesta final o el resultado directo de forma concisa."
        elif modo == 'procedimiento_directo':
            instruccion_modo = "Devuelve ÚNICAMENTE los pasos lógicos o las ecuaciones/código de forma directa, sin texto de relleno."
        else:
            instruccion_modo = "Explica todo el proceso de forma detallada y pedagógica."

        if categoria == 'matematicas':
            prompt = f"""
            Eres un profesor experto en matemáticas. El usuario te envía un problema inicial.
            Instrucción: {instruccion_modo}
            REGLA DE FORMATO: Usa fórmulas en línea ($...$) para variables y bloques ($$...$$) SOLO en líneas separadas, nunca dentro de listas <li>.
            Retorna el resultado limpio en formato HTML (sin ```html ni markdown).
            """
        else:
            prompt = f"""
            Eres un desarrollador de software senior. El usuario te envía código o un problema de programación inicial.
            Instrucción: {instruccion_modo}
            Usa obligatoriamente etiquetas HTML <pre><code>...</code></pre> para bloques de código.
            Retorna el resultado en formato HTML limpio (sin ```html ni markdown).
            """

        contents = [prompt]
        if file:
            image = Image.open(io.BytesIO(file.read()))
            contents.append(image)
        if texto_usuario:
            contents.append(f"Problema o código inicial:\n{texto_usuario}")

        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=contents
        )
        
        raw_html = response.text.strip()
        if raw_html.startswith("```html"): raw_html = raw_html.replace("```html", "", 1)
        if raw_html.startswith("```"): raw_html = raw_html.replace("```", "", 1)
        if raw_html.endswith("```"): raw_html = raw_html[::-1].replace("```", "", 1)[::-1]
            
        session['historial'] = f"Problema inicial:\n{texto_usuario if texto_usuario else 'Imagen adjunta'}\nRespuesta inicial:\n{raw_html}"

        return jsonify({
            "solucion_html": raw_html.strip(),
            "contexto_backend": session['historial'] # Enviamos el contexto al frontend para guardarlo
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def continuar_chat():
    data = request.get_json()
    mensaje_usuario = data.get('mensaje', '').strip()

    if not mensaje_usuario:
        return jsonify({"error": "El mensaje está vacío."}), 400

    try:
        historial_previo = session.get('historial', '')

        prompt_seguimiento = f"""
        Contexto previo de la conversación:
        {historial_previo}

        Nueva duda o ajuste solicitado por el usuario:
        {mensaje_usuario}

        Responde a esta nueva duda manteniendo el formato HTML limpio, usando MathJax para matemáticas ($...$) o etiquetas <pre><code> para código según corresponda. No uses bloques ```html.
        """

        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt_seguimiento
        )

        raw_html = response.text.strip()
        if raw_html.startswith("```html"): raw_html = raw_html.replace("```html", "", 1)
        if raw_html.startswith("```"): raw_html = raw_html.replace("```", "", 1)
        if raw_html.endswith("```"): raw_html = raw_html[::-1].replace("```", "", 1)[::-1]

        session['historial'] = f"{historial_previo}\nPregunta: {mensaje_usuario}\nRespuesta: {raw_html}"

        return jsonify({
            "respuesta_html": raw_html.strip(),
            "contexto_backend": session['historial'] # Actualizamos el contexto
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# NUEVA RUTA: Permite al navegador decirle al servidor de qué problema viejo estamos hablando
@app.route('/restaurar_historial', methods=['POST'])
def restaurar_historial():
    data = request.get_json()
    session['historial'] = data.get('contexto', '')
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', debug=False, port=port)
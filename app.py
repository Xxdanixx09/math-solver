from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from google import genai
from PIL import Image
import io
import os

app = Flask(__name__)
CORS(app) 
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clave-secreta-temporal-123") # Necesario para recordar la sesión del chat

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route('/')
def home():
    session.clear() # Limpiar chat al cargar de nuevo
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

        # Usamos chat de Gemini para mantener el hilo de la conversación
        chat = client.chats.create(model="gemini-3.6-flash")
        response = chat.send_message(contents)
        
        # Guardamos el historial del chat en la sesión de Flask serializado lógicamente
        # (Guardamos los mensajes recientes o mantenemos la instancia activa si prefieres)
        session['historial_prompt'] = response.text

        raw_html = response.text.strip()
        if raw_html.startswith("```html"): raw_html = raw_html.replace("```html", "", 1)
        if raw_html.startswith("```"): raw_html = raw_html.replace("```", "", 1)
        if raw_html.endswith("```"): raw_html = raw_html[::-1].replace("```", "", 1)[::-1]
            
        return jsonify({"solucion_html": raw_html.strip()})
        
    except Exception as e:
        print(f"Error interno: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def continuar_chat():
    data = request.get_json()
    mensaje_usuario = data.get('mensaje', '').strip()

    if not mensaje_usuario:
        return jsonify({"error": "El mensaje está vacío."}), 400

    try:
        # Creamos un nuevo chat contextual o enviamos el mensaje de seguimiento
        chat = client.chats.create(model="gemini-3.6-flash")
        
        prompt_seguimiento = f"""
        Contexto previo de la solución generada: {session.get('historial_prompt', '')}
        
        El usuario realiza la siguiente consulta o ajuste sobre la respuesta anterior:
        {mensaje_usuario}
        
        Responde a esta nueva duda manteniendo el formato HTML limpio, usando MathJax para matemáticas ($...$) o etiquetas <pre><code> para código según corresponda. No uses bloques ```html.
        """

        response = chat.send_message(prompt_seguimiento)
        session['historial_prompt'] = response.text

        raw_html = response.text.strip()
        if raw_html.startswith("```html"): raw_html = raw_html.replace("```html", "", 1)
        if raw_html.startswith("```"): raw_html = raw_html.replace("```", "", 1)
        if raw_html.endswith("```"): raw_html = raw_html[::-1].replace("```", "", 1)[::-1]

        return jsonify({"respuesta_html": raw_html.strip()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', debug=False, port=port)
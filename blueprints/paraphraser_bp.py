from flask import Blueprint, render_template, request, session, current_app, jsonify
from utils import gemini_module
import json
import traceback

paraphraser_bp = Blueprint('paraphraser_bp', 
                           __name__, 
                           template_folder='../templates', 
                           url_prefix='/paraphraser')

def get_paraphrase_prompt(text_to_paraphrase, style="Standar"):
    style_instructions = {
        "Standar": "Tulis ulang teks ini dengan tetap menjaga makna intinya. Fokus pada kejelasan dan alur yang alami.",
        "Formal": "Tulis ulang teks ini dengan gaya bahasa yang lebih formal, profesional, dan baku. Hindari bahasa gaul dan gunakan struktur kalimat yang lebih lengkap.",
        "Santai": "Tulis ulang teks ini dengan gaya bahasa yang lebih santai, kasual, dan mudah didekati, seolah-olah sedang berbicara dengan teman.",
        "Sederhana": "Tulis ulang teks ini dengan kalimat yang lebih pendek dan kosakata yang lebih sederhana agar sangat mudah dipahami oleh semua orang."
    }

    prompt = (
        "Anda adalah seorang penulis dan ahli linguistik yang sangat kreatif. Tugas Anda adalah memparafrasakan teks yang diberikan dalam 3 variasi yang berbeda, sesuai dengan gaya yang diminta.\n\n"
        f"**Gaya yang Diinginkan**: {style_instructions.get(style, style_instructions['Standar'])}\n\n"
        "**Instruksi Output (WAJIB):**\n"
        "Anda HARUS memberikan output HANYA dalam format JSON yang valid, tanpa teks atau markdown tambahan. Strukturnya harus seperti ini:\n"
        "```json\n"
        "{\n"
        '  "variations": [\n'
        "    {\n"
        '      "title": "Variasi 1 (Sesuai Gaya yang Diminta)",\n'
        '      "text": "Teks parafrase pertama di sini."\n'
        "    },\n"
        "    {\n"
        '      "title": "Variasi 2 (Alternatif Kreatif)",\n'
        '      "text": "Teks parafrase kedua dengan pendekatan yang sedikit berbeda di sini."\n'
        "    },\n"
        "    {\n"
        '      "title": "Variasi 3 (Paling Ringkas)",\n'
        '      "text": "Teks parafrase ketiga yang paling singkat dan padat di sini."\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "```\n\n"
        "**Teks untuk Diparafrasekan:**\n"
        "```\n"
        f"{text_to_paraphrase}\n"
        "```"
    )
    return prompt

@paraphraser_bp.route('/', methods=['GET'])
def paraphrase_page_get():
    gemini_is_ready = current_app.config.get('GEMINI_READY', False)
    form_data = {
        'text_to_paraphrase': session.get('paraphraser_text', ''),
        'paraphrase_style': session.get('paraphraser_style', 'Standar')
    }
    return render_template('paraphraser_page.html', 
                           title="Parafrase Teks AI",
                           form_data=form_data,
                           gemini_ready=gemini_is_ready)

@paraphraser_bp.route('/', methods=['POST'])
def paraphrase_page_post():
    if not current_app.config.get('GEMINI_READY', False):
        return jsonify({"error": "Layanan AI tidak tersedia saat ini."}), 503

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body tidak valid."}), 400

        text = data.get('text_to_paraphrase', "").strip()
        style = data.get('paraphrase_style', 'Standar')

        if not text:
            return jsonify({"error": "Teks untuk diparafrase tidak boleh kosong."}), 400

        session['paraphraser_text'] = text
        session['paraphraser_style'] = style

        prompt = get_paraphrase_prompt(text, style)
        
        gemini_client = current_app.config.get('GEMINI_CLIENT')
        raw_output = gemini_module.panggil_gemini_model(prompt, gemini_client)

        if raw_output.startswith("STATUS_ERROR:"):
            return jsonify({"error": raw_output.replace("STATUS_ERROR:", "").strip()}), 500
            
        try:
            clean_json_string = raw_output.strip().replace('```json', '', 1).replace('```', '', 1).strip()
            parsed_data = json.loads(clean_json_string)
            return jsonify(parsed_data)
        except json.JSONDecodeError:
            return jsonify({"error": "AI gagal memberikan respons dalam format yang diharapkan. Silakan coba lagi."})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Terjadi kesalahan internal: {str(e)}"}), 500
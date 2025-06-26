from flask import Blueprint, render_template, request, session, current_app, jsonify
from utils import gemini_module
import json
import traceback

proofreader_bp = Blueprint('proofreader_bp', 
                           __name__, 
                           template_folder='../templates', 
                           url_prefix='/proofreader')

def get_proofread_prompt(text_to_proofread, style="Standar"):
    style_instruction = {
        "Standar": "Perbaiki semua kesalahan tata bahasa, ejaan, dan tanda baca dengan tetap mempertahankan gaya asli penulis semaksimal mungkin.",
        "Formal": "Perbaiki semua kesalahan dan tingkatkan teks agar terdengar lebih formal, profesional, dan cocok untuk lingkungan bisnis atau akademik. Ganti bahasa gaul dengan kosa kata yang lebih baku.",
        "Sederhana": "Perbaiki semua kesalahan dan sederhanakan struktur kalimat serta pilihan kata agar teks menjadi lebih mudah dipahami oleh audiens yang lebih luas."
    }

    prompt = (
        "Anda adalah seorang editor dan ahli linguistik yang sangat teliti. Tugas Anda adalah mengoreksi teks yang diberikan dan memberikan laporan perubahan yang terperinci.\n\n"
        f"**Gaya Koreksi yang Diinginkan**: {style_instruction.get(style, style_instruction['Standar'])}\n\n"
        "**Instruksi Output (WAJIB):**\n"
        "Anda HARUS memberikan output HANYA dalam format JSON yang valid dan terstruktur, tanpa teks atau markdown tambahan. Strukturnya harus seperti ini:\n"
        "```json\n"
        "{\n"
        '  "corrected_text": "Teks lengkap yang sudah diperbaiki di sini.",\n'
        '  "changes": [\n'
        "    {\n"
        '      "original": "frasa/kata asli yang salah",\n'
        '      "correction": "frasa/kata yang sudah benar",\n'
        '      "reason": "Penjelasan singkat alasan perbaikan (misal: \'Kesalahan Ejaan\', \'Tata Bahasa: Subjek-Kata Kerja\', \'Gaya: Pilihan Kata\')"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "```\n"
        "Jika tidak ada kesalahan sama sekali dalam teks, kembalikan `corrected_text` yang sama dengan teks asli dan `changes` sebagai array kosong `[]`.\n\n"
        "**Teks untuk Dikoreksi:**\n"
        "```\n"
        f"{text_to_proofread}\n"
        "```"
    )
    return prompt

@proofreader_bp.route('/', methods=['GET'])
def proofread_page_get():
    gemini_is_ready = current_app.config.get('GEMINI_READY', False)
    form_data = {
        'text_to_proofread': session.get('proofreader_text', ''),
        'correction_style': session.get('proofreader_style', 'Standar')
    }
    return render_template('proofreader_page.html', 
                           title="Koreksi & Perbaikan Teks AI",
                           form_data=form_data,
                           gemini_ready=gemini_is_ready)

@proofreader_bp.route('/', methods=['POST'])
def proofread_page_post():
    if not current_app.config.get('GEMINI_READY', False):
        return jsonify({"error": "Layanan AI tidak tersedia saat ini."}), 503

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body tidak valid."}), 400

        text = data.get('text_to_proofread', "").strip()
        style = data.get('correction_style', 'Standar')

        if not text:
            return jsonify({"error": "Teks untuk diperiksa tidak boleh kosong."}), 400

        session['proofreader_text'] = text
        session['proofreader_style'] = style

        prompt = get_proofread_prompt(text, style)
        
        gemini_client = current_app.config.get('GEMINI_CLIENT')
        raw_output = gemini_module.panggil_gemini_model(prompt, gemini_client)

        if raw_output.startswith("STATUS_ERROR:"):
            return jsonify({"error": raw_output.replace("STATUS_ERROR:", "").strip()}), 500
            
        try:
            clean_json_string = raw_output.strip().replace('```json', '', 1).replace('```', '', 1).strip()
            parsed_data = json.loads(clean_json_string)
            return jsonify(parsed_data)
        except json.JSONDecodeError:
            return jsonify({
                "corrected_text": raw_output,
                "changes": [{
                    "original": "-",
                    "correction": "-",
                    "reason": "AI tidak memberikan laporan perubahan dalam format yang diharapkan."
                }]
            })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Terjadi kesalahan internal: {str(e)}"}), 500
from flask import Blueprint, render_template, request, jsonify, session, current_app
import textstat 
import json 
from utils import gemini_module

readability_bp = Blueprint('readability_bp', 
                           __name__, 
                           template_folder='../templates', 
                           url_prefix='/readability')

def get_readability_scores(text):
    if not text or not text.strip():
        return None, "STATUS_INFO: Teks kosong, tidak ada yang bisa dianalisis."
    try:
        scores = {
            'flesch_reading_ease': round(textstat.flesch_reading_ease(text), 2),
            'flesch_kincaid_grade': round(textstat.flesch_kincaid_grade(text), 2)
        }
        f_ease = scores['flesch_reading_ease']
        if f_ease >= 90:
            scores['flesch_reading_ease_interpretation'] = "Sangat Mudah Dibaca."
        elif f_ease >= 60:
            scores['flesch_reading_ease_interpretation'] = "Bahasa Standar."
        elif f_ease >= 30:
            scores['flesch_reading_ease_interpretation'] = "Cukup Sulit Dibaca."
        else:
            scores['flesch_reading_ease_interpretation'] = "Sangat Sulit Dibaca."
        return scores, ""
    except Exception as e:
        return None, f"STATUS_ERROR: Gagal menganalisis keterbacaan: {str(e)}"

@readability_bp.route('/', methods=['GET'])
def readability_page_get():
    gemini_is_ready = current_app.config.get('GEMINI_READY', False)
    default_method = 'gemini' if gemini_is_ready else 'classic'
    form_data = {
        'analysis_method': session.get('readability_analysis_method', default_method)
    }
    return render_template('readability_page.html', 
                           title="Analisis Keterbacaan", 
                           form_data=form_data, 
                           gemini_ready=gemini_is_ready)

@readability_bp.route('/process', methods=['POST'])
def process_readability():
    gemini_is_ready = current_app.config.get('GEMINI_READY', False)
    data = request.get_json()
    text_input = data.get('text_to_analyze', '').strip()
    method = data.get('analysis_method', 'classic')

    if not text_input:
        return jsonify({'success': False, 'error': 'Teks untuk dianalisis tidak boleh kosong.'}), 400

    results = {}
    error_message = ""

    if method == 'gemini':
        if not gemini_is_ready:
            return jsonify({'success': False, 'error': 'Metode Analisis AI tidak tersedia.'}), 400
        
        prompt_json = (
            "Anda adalah seorang ahli linguistik. Lakukan analisis keterbacaan untuk teks berikut. "
            "Anda HARUS mengembalikan respons dalam format JSON yang valid dan mentah tanpa ```json.\n"
            "Skema JSON:\n"
            "{\n"
            '  "skor_keterbacaan": (angka 1-100),\n'
            '  "level_pembaca": "(string, contoh: \'Sangat Mudah\', \'Anak SMP\', \'Standar Umum\')",'
            '\n'
            '  "analisis_singkat": "(string, satu kalimat ringkas tentang alasan penilaian Anda)",\n'
            '  "saran_perbaikan": "(string, 2-3 poin saran perbaikan dalam Markdown, atau string kosong jika tidak ada saran)"\n'
            "}\n\n"
            f"Teks untuk dianalisis:\n```\n{text_input}\n```\n\nJSON Respons:"
        )

        gemini_client = current_app.config.get('GEMINI_CLIENT')
        if not gemini_client:
            return jsonify({'success': False, 'error': 'Klien Gemini tidak terkonfigurasi di server.'}), 500
        
        response_text = gemini_module.panggil_gemini_model(prompt_json, gemini_client)
        
        if response_text.startswith("STATUS_ERROR:"):
            error_message = response_text
        else:
            try:
                clean_response = response_text.strip().lstrip('```json').rstrip('```').strip()
                json_response = json.loads(clean_response)
                results['gemini_analysis'] = json_response
            except json.JSONDecodeError:
                error_message = "STATUS_ERROR: Gagal mem-parsing respons dari AI."
                print(f"Failed to decode JSON from Gemini: {response_text}")

    else:
        classic_scores, err_msg = get_readability_scores(text_input)
        if err_msg:
            error_message = err_msg
        else:
            results['classic_analysis'] = classic_scores

    if error_message:
        return jsonify({'success': False, 'error': error_message.replace('STATUS_ERROR:', '').strip()}), 400

    return jsonify({'success': True, 'results': results})



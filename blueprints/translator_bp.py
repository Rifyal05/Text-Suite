from flask import Blueprint, render_template, request, session, current_app, jsonify
from utils import gemini_module, classic_translator, generative_models, judges
import json
import traceback
import asyncio

translator_bp = Blueprint('translator_bp',
                          __name__,
                          template_folder='../templates',
                          url_prefix='/translator')

def get_ai_translation_prompt(text, source, target):
    return (
        f"Anda adalah seorang penerjemah dan analis bahasa ahli. Tugas Anda adalah menerjemahkan teks dan memberikan penjelasan konteks tentangnya. "
        f"Terjemahkan teks berikut dari bahasa '{source}' (deteksi otomatis jika 'auto') ke dalam bahasa '{target}'.\n"
        "Setelah itu, berikan penjelasan yang detail tapi mudah dipahami tentang konteks, nuansa, atau makna ganda dari teks asli jika ada. Jika teksnya sederhana, jelaskan bahwa teks tersebut lugas.\n"
        "Berikan jawaban Anda **HANYA** dalam format JSON yang valid dengan struktur berikut:\n"
        "{\n"
        '  "translation": "hasil terjemahan di sini",\n'
        '  "context_explanation": "penjelasan konteks ada di sini dan bahasa yang digunakan di bagian penjelasan konteks adalah bahasa yang menjadi tujuan terjemahan."\n'
        "}\n\n"
        f"Teks untuk dianalisis:\n```\n{text}\n```"
    )

def parse_ai_output(raw_output):
    """Membersihkan dan parsing output JSON dari model AI."""
    try:
        clean_json_string = raw_output.strip().replace('```json', '', 1).replace('```', '', 1).strip()
        parsed_data = json.loads(clean_json_string)
        return {
            'translation_result': parsed_data.get('translation', '[Terjemahan tidak ditemukan]'),
            'context_explanation': parsed_data.get('context_explanation', '[Penjelasan tidak ditemukan]')
        }
    except (json.JSONDecodeError, AttributeError):
        return {
            'translation_result': raw_output,
            'context_explanation': "AI tidak memberikan jawaban dalam format JSON yang diharapkan."
        }

@translator_bp.route('/', methods=['GET'])
def translate_page_get():
    gemini_is_ready = current_app.config.get('GEMINI_READY', False)
    openai_is_ready = current_app.config.get('OPENAI_READY', False)
    
    default_model = 'classic'
    if gemini_is_ready:
        default_model = 'gemini'
    elif openai_is_ready:
        default_model = 'gpt'

    form_data = {
        'text_to_translate': session.get('translator_text_to_translate', ''),
        'translation_model': session.get('translator_model', default_model),
        'comparison_model_translate': session.get('translator_comparison_model', 'none'),
        'source_language_translate': session.get('translator_source_lang', 'auto'),
        'target_language_translate': session.get('translator_target_lang', 'English')
    }
    
    return render_template('translator_page.html',
                           form_data=form_data,
                           gemini_ready=gemini_is_ready,
                           openai_ready=openai_is_ready)

@translator_bp.route('/', methods=['POST'])
def translate_page_post():
    data = request.get_json()
    if not data:
        return jsonify({'error_message': "Permintaan tidak valid."}), 400

    text_to_translate = data.get('text_to_translate', '').strip()
    source_lang = data.get('source_language_translate', 'auto')
    target_lang = data.get('target_language_translate', 'English')
    model_choice = data.get('translation_model', 'classic')

    session['translator_text_to_translate'] = text_to_translate
    session['translator_model'] = data.get('translation_model')
    session['translator_comparison_model'] = data.get('comparison_model_translate') 
    session['translator_source_lang'] = source_lang
    session['translator_target_lang'] = target_lang
    
    if not text_to_translate:
        return jsonify({'error_message': "STATUS_ERROR: Teks tidak boleh kosong."}), 400

    ai_models = ['gemini', 'gpt']

    if model_choice in ai_models:
        prompt = get_ai_translation_prompt(text_to_translate, source_lang, target_lang)
        
        if model_choice == 'gemini':
            if not current_app.config.get('GEMINI_READY', False):
                return jsonify({'error_message': "STATUS_ERROR: Model Gemini tidak tersedia."}), 503
            client = current_app.config.get('GEMINI_CLIENT')
            raw_output = gemini_module.panggil_gemini_model(prompt, client)
        
        elif model_choice == 'gpt':
            if not current_app.config.get('OPENAI_READY', False):
                return jsonify({'error_message': "STATUS_ERROR: Model OpenAI tidak tersedia."}), 503
            raw_output, error_msg = generative_models.call_generative_model_blocking(
                model_id='gpt', prompt=prompt, app_config=current_app.config
            )
            if error_msg:
                raw_output = f"STATUS_ERROR: {error_msg}"
        
        else:
            return jsonify({'error_message': f"Model AI '{model_choice}' tidak dikenal."}), 400
            
        if raw_output.startswith("STATUS_ERROR:"):
            return jsonify({'error_message': raw_output}), 500
        
        parsed_result = parse_ai_output(raw_output)
        return jsonify(parsed_result)
        
    else: # Model 'classic'
        translation_output = classic_translator.translate_text(
            text_to_translate, 
            target_language=target_lang, 
            source_language=source_lang
        )
        
        if translation_output.startswith("STATUS_ERROR:"):
            return jsonify({'error_message': translation_output}), 500
        else:
            return jsonify({'translation_result': translation_output})

@translator_bp.route('/evaluate', methods=['POST'])
def evaluate_translation():
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Request body tidak valid."}), 400
        
        original_text = data.get('original_text')
        translated_text = data.get('translated_text')
        source_lang = data.get('source_lang', 'auto')
        target_lang = data.get('target_lang', 'English')

        if not original_text or not translated_text:
            return jsonify({"error": "Teks asli dan teks terjemahan dibutuhkan."}), 400
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        ai_evaluations = loop.run_until_complete(
            judges.get_all_translation_evaluations_async(
                original_text, translated_text, source_lang, target_lang, current_app.config
            )
        )
        final_results = {"ai_judges": ai_evaluations}
        return jsonify(final_results)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Terjadi kesalahan internal saat evaluasi: {e}"}), 500
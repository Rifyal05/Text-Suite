from flask import Blueprint, render_template, request, session, current_app
from utils import gemini_module

proofreader_bp = Blueprint('proofreader_bp', 
                           __name__, 
                           template_folder='../templates', 
                           url_prefix='/proofreader')

@proofreader_bp.route('/', methods=['GET', 'POST'])
def proofread_page():
    gemini_is_ready = current_app.config.get('GEMINI_READY', False)

    form_data = {
        'text_to_proofread': session.get('proofreader_text', ''),
    }
    results = {
        'corrected_text': "",
        'error_message': ""
    }

    if request.method == 'POST':
        if not gemini_is_ready:
            results['error_message'] = "STATUS_ERROR: Mohon maaf, fitur Proofreader tidak tersedia saat ini karena layanan AI belum siap."
        else:
            form_data['text_to_proofread'] = request.form.get('text_to_proofread', "").strip()
            session['proofreader_text'] = form_data['text_to_proofread']

            if not form_data['text_to_proofread']:
                results['error_message'] = "STATUS_INFO: Teks untuk diperiksa masih kosong, Kak..."
            else:
                prompt = (
                    "Anda adalah seorang editor profesional yang sangat teliti. "
                    "Perbaiki teks berikut ini dari segala kesalahan ejaan (typo), tata bahasa (grammar), dan tanda baca (punctuation). "
                    "Hanya kembalikan teks yang sudah diperbaiki, tanpa tambahan komentar, penjelasan, atau pemformatan markdown apa pun.\n\n"
                    "Teks Asli:\n"
                    "```\n"
                    f"{form_data['text_to_proofread']}\n"
                    "```\n\n"
                    "Teks yang Sudah Diperbaiki:"
                )
                
                correction_result = gemini_module.panggil_gemini_model(prompt)

                if correction_result.startswith("STATUS_ERROR:"):
                    results['error_message'] = correction_result
                else:
                    results['corrected_text'] = correction_result
            
    return render_template('proofreader_page.html', 
                           title="Koreksi & Perbaikan Teks AI", 
                           form_data=form_data, 
                           results=results,
                           gemini_ready=gemini_is_ready)
from flask import Blueprint, render_template, request, session, current_app, Response, jsonify
import asyncio
import traceback
from utils import summarizer_module, judges, generative_models
from langdetect import detect, lang_detect_exception

# Inisialisasi Blueprint untuk modul summarizer
summarizer_bp = Blueprint('summarizer_bp',
                          __name__,
                          template_folder='../templates',
                          url_prefix='/summarizer')

@summarizer_bp.route('/', methods=['POST'])
def summarize_page_post():
    """
    Menangani permintaan POST untuk meringkas teks.
    Fungsi ini menerima teks asli dan parameter lainnya, lalu memilih antara
    model AI (seperti Gemini, GPT) atau algoritma tradisional (seperti TextRank)
    untuk melakukan peringkasan. Mendukung response streaming untuk model AI tertentu.
    """
    try:
        # Ekstrak data dari payload JSON yang dikirim oleh klien
        data = request.get_json()
        if not data:
            return jsonify({"error": "Payload JSON tidak valid."}), 400

        # Ambil teks asli dan algoritma yang dipilih dari data
        original_text = data.get('original_text', "").strip()
        algo = data.get('summarizer_algo', 'textrank')

        # Validasi bahwa teks tidak kosong
        if not original_text:
            return jsonify({"error": "Teks untuk diproses tidak boleh kosong."}), 400

        # Daftar model AI yang didukung
        ai_models = ['gemini', 'learnlm', 'gpt', 'gpt-4o', 'gpt-4o-nano']

        # Blok logika jika algoritma yang dipilih adalah model AI
        if algo in ai_models:
            # Ambil parameter spesifik untuk model AI
            language_code = data.get('lang_summarizer', 'auto')
            num_sentences = data.get('num_sentences_summary', 3)
            max_keywords = data.get('max_keywords_summary', 10)

            # Atur instruksi bahasa berdasarkan pilihan pengguna (auto-detect atau spesifik)
            language_map = {'indonesian': 'Indonesia', 'english': 'Inggris (English)'}
            if language_code == 'auto':
                language_instruction = "Secara otomatis deteksi bahasa dari teks yang diberikan dan berikan semua respons dalam bahasa yang terdeteksi tersebut."
            else:
                language_name = language_map.get(language_code, "Inggris")
                language_instruction = f"Teks ini ditulis dalam Bahasa {language_name}. Anda HARUS memberikan semua hasil dalam Bahasa {language_name}."

            # Buat prompt yang detail untuk dikirim ke model AI
            prompt_template = f"""
            Anda adalah seorang **Analis Riset ahli** yang sangat pandai dalam menyuling informasi kompleks menjadi intisari yang padat dan berwawasan. Tugas Anda adalah menganalisis teks berikut dan menghasilkan ringkasan serta kata kunci berkualitas tinggi.
            Jika input terlalu singkat, berikan penjelasan singkat tentang input yang dimasukkan dan informasikan bahwa input terlalu singkat untuk diringkas, dan tidak perlu memberikan kata-kunci.

            **Instruksi:**
            1.  **Analisis Mendalam**: Baca dan pahami seluruh teks. Identifikasi tesis utama, argumen pendukung, dan kesimpulan.
            2.  **Penyusunan Ringkasan**: Tulis ringkasan dalam sekitar **{num_sentences} kalimat** yang mencerminkan hasil analisis Anda.
            3.  **Ekstraksi Kata Kunci**: Berdasarkan analisis, ekstrak hingga **{max_keywords} kata atau frasa kunci** yang paling representatif.

            **Kriteria Output:**
            - **Informatif & Padat**: Hindari kalimat pengisi yang tidak perlu.
            - **Akurasi Faktual**: Jangan mengubah atau salah menginterpretasikan fakta.
            - **Struktur Markdown**: Output HARUS mengikuti format Markdown yang rapi di bawah ini, tanpa teks tambahan.
            - **ATURAN WAJIB**: Selalu pastikan ada spasi tunggal di antara setiap kata. **JANGAN PERNAH** menggabungkan dua kata menjadi satu (Contoh salah: "katabaru", contoh benar: "kata baru").

            **Teks untuk dianalisis:**
            ---
            {original_text}
            ---

            **Output Akhir (Wajib dalam Bahasa {language_instruction}):**
            **RINGKASAN** [HEADER RINGKASAN BISA DISESUAIKAN SESUAI BAHASA ORIGINAL TEXT DAN DALAM KAPITAL]

            [Tulis hasil ringkasan Anda yang berkualitas tinggi di sini]

            **KATA KUNCI** [HEADER KATA KUNCI BISA DISESUAIKAN SESUAI BAHASA ORIGINAL TEXT DAN DALAM KAPITAL]

            - [Kata Kunci 1]
            - [Kata Kunci 2]
            - ...
            """
            # Tentukan apakah model AI mendukung streaming untuk respons real-time
            streaming_models = ['gemini', 'learnlm']

            if algo in streaming_models:
                # Jika model mendukung streaming, panggil fungsi streaming dan kembalikan responsnya
                stream_response = generative_models.call_generative_model_streaming(
                    model_id=algo, prompt=prompt_template, app_config=current_app.config
                )
                return Response(stream_response, mimetype='text/event-stream')
            else: 
                # Jika model tidak streaming (blocking), panggil dan tunggu hasil lengkapnya
                result_text, error_msg = generative_models.call_generative_model_blocking(
                    model_id=algo, prompt=prompt_template, app_config=current_app.config
                )
                if error_msg:
                    return jsonify({"error": error_msg}), 500
                return jsonify({"result": result_text})

        # Blok logika jika algoritma yang dipilih adalah tradisional (non-AI)
        else:
            # Ambil parameter untuk algoritma tradisional
            num_sentences = int(data.get('num_sentences_summary', 3))
            max_keywords = int(data.get('max_keywords_summary', 10))
            lang_summarizer = data.get('lang_summarizer', 'indonesian')
            sastrawi_stemmer = current_app.config.get('SASTRAWI_STEMMER_INSTANCE')
            
            # Panggil modul summarizer lokal untuk mendapatkan ringkasan dan kata kunci
            summary_text, keywords_list, err_sum, err_kw = summarizer_module.get_summary_and_keywords(
                original_text, num_sentences, lang_summarizer,
                sastrawi_stemmer, max_keywords, algo
            )

            # Tangani potensi error dari proses summarizer
            error_message = ""
            if err_sum and "STATUS_ERROR:" in err_sum:
                error_message += err_sum.replace("STATUS_ERROR:", "").strip()
            if err_kw and "STATUS_ERROR:" in err_kw:
                error_message += (" " + err_kw.replace("STATUS_ERROR:", "").strip()).strip()
            if error_message:
                return jsonify({"error": error_message}), 400
            
            # Format output ke dalam format Markdown yang konsisten
            markdown_output = f"## Ringkasan (Metode: {algo.upper()})\n{summary_text}\n\n## Kata Kunci\n"
            if keywords_list:
                for kw in keywords_list:
                    markdown_output += f"- {kw}\n"
            return jsonify({"result": markdown_output})

    except Exception as e:
        # Penanganan error umum untuk menangkap masalah tak terduga
        traceback.print_exc()
        return jsonify({"error": f"Terjadi kesalahan internal: {e}"}), 500

@summarizer_bp.route('/evaluate', methods=['POST'])
def evaluate_summary():
    """
    Menangani permintaan POST untuk mengevaluasi kualitas sebuah ringkasan
    terhadap teks aslinya menggunakan beberapa model AI sebagai "juri".
    """
    try:
        data = request.get_json()
        if not data: return jsonify({"error": "Request body tidak valid."}), 400
        
        # Ambil teks asli dan ringkasan dari request body
        original_text = data.get('original_text')
        summary_text = data.get('summary_text')
        lang_code_from_form = data.get('lang_summarizer', 'indonesian')
        
        if not original_text or not summary_text:
            return jsonify({"error": "Teks asli dan teks ringkasan dibutuhkan."}), 400
        
        # Tentukan bahasa untuk prompt evaluasi, dengan default ke Inggris jika gagal deteksi
        lang_iso = lang_code_from_form
        ui_lang_name = 'English'
        try:
            if lang_code_from_form == 'auto':
                detected_lang = detect(original_text)
                lang_iso = detected_lang
                ui_lang_name = 'Indonesia' if detected_lang == 'id' else 'English'
            else:
                ui_lang_name = 'Indonesia' if 'indonesian' in lang_code_from_form.lower() else 'English'
        except lang_detect_exception.LangDetectException:
            print("[WARNING] Gagal mendeteksi bahasa, menggunakan English sebagai default untuk evaluasi.")
            lang_iso = 'en' # Fallback language
            ui_lang_name = 'English'

        # Jalankan evaluasi AI secara asinkron untuk efisiensi
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # Jika tidak ada event loop yang berjalan
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        ai_evaluations = loop.run_until_complete(
            judges.get_all_evaluations_async(original_text, summary_text, ui_lang_name, current_app.config)
        )
        
        final_results = {"ai_judges": ai_evaluations}
        return jsonify(final_results)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Terjadi kesalahan internal: {e}"}), 500

@summarizer_bp.route('/', methods=['GET'])
def summarize_page_get():
    """
    Menangani permintaan GET untuk menampilkan halaman utama peringkas teks.
    Fungsi ini mengisi form dengan data dari sesi terakhir pengguna untuk
    pengalaman pengguna yang lebih baik dan menentukan algoritma default
    berdasarkan ketersediaan model AI.
    """
    # Cek ketersediaan model AI dari konfigurasi aplikasi
    gemini_is_ready = current_app.config.get('GEMINI_READY', False)
    openai_is_ready = current_app.config.get('OPENAI_READY', False)
    
    # Tentukan algoritma default berdasarkan model yang paling canggih yang tersedia
    default_method = 'gemini'
    if not gemini_is_ready and openai_is_ready:
        default_method = 'gpt'
    elif not gemini_is_ready and not openai_is_ready:
        default_method = 'textrank'
        
    # Ambil data dari sesi pengguna untuk mengisi kembali form (meningkatkan UX)
    form_data = {
        'original_text': session.get('summarizer_original_text_last_input', ''),
        'num_sentences_summary': session.get('summarizer_num_sentences', 3),
        'lang_summarizer': session.get('summarizer_lang', 'auto' if default_method in ['gemini', 'gemma', 'gpt', 'gpt-4o', 'gpt-4o-nano'] else 'indonesian'),
        'max_keywords_summary': session.get('summarizer_max_keywords', 10),
        'summarizer_algo': session.get('summarizer_algo', default_method)
    }
    
    # Render template halaman dengan data yang relevan
    return render_template('summarizer_page.html',
                           title="Peringkas Teks & Kata Kunci",
                           form_data=form_data,
                           gemini_ready=gemini_is_ready,
                           openai_ready=openai_is_ready)
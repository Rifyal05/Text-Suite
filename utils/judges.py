import asyncio
import json
import re
from google import genai
import cohere
from google.genai.types import GenerateContentConfig as GenerationConfig

# Blok: Template Prompt untuk Evaluasi Ringkasan
# Ini adalah template 'perintah' yang akan diberikan kepada AI Juri.
# Isinya sangat terstruktur, mendefinisikan peran AI, data yang harus dievaluasi (teks asli dan ringkasan),
# kriteria penilaian yang detail, dan format output JSON yang ketat.
# Menggunakan template memastikan konsistensi dan keandalan hasil dari AI.
JUDGE_PROMPT_TEMPLATE = """
Anda adalah seorang Analis Kualitas AI yang sangat teliti, objektif, dan ahli dalam linguistik. Tugas Anda adalah memberikan evaluasi terstruktur terhadap kualitas sebuah ringkasan teks yang dihasilkan oleh sebuah metode AI.
**DATA EVALUASI:**
- **Teks Asli**: ```{input_text}```
- **Ringkasan untuk Dinilai**: ```{output_text}```
**INSTRUKSI:**
Anda **WAJIB** memberikan penilaian berdasarkan 5 kriteria di bawah ini. Untuk setiap kriteria, berikan skor dari 1 hingga 100 dan justifikasi singkat.
1.  **Relevansi & Cakupan (Relevance & Coverage)**: Seberapa baik ringkasan menangkap ide pokok dan informasi krusial dari teks asli? (100 = Sangat lengkap dan relevan).
2.  **Kepadatan & Ringkas (Conciseness)**: Seberapa efisien ringkasan dalam menyampaikan informasi tanpa kata-kata atau kalimat yang berlebihan/tidak perlu? (100 = Sangat padat dan to-the-point).
3.  **Koherensi (Coherence)**: Apakah alur ringkasan logis dan mudah dipahami sebagai teks yang mandiri? (100 = Sangat koheren dan mengalir dengan baik).
4.  **Konsistensi Faktual (Factual Consistency)**: Apakah ringkasan akurat dan tidak mengandung informasi yang bertentangan atau tidak ada di teks asli? (100 = Sepenuhnya konsisten secara faktual).
5.  **Kefasihan (Fluency)**: Apakah tata bahasa, ejaan, dan pilihan katanya benar dan alami? (100 = Sangat fasih, tanpa kesalahan).
**FORMAT OUTPUT:**
Berikan output **HANYA** dalam format JSON yang valid tanpa markdown ```json atau penjelasan lainnya. Gunakan Bahasa **{target_lang}** untuk semua teks justifikasi dan evaluasi.
**Struktur JSON yang WAJIB diikuti:**
{{
  "skor_keseluruhan": (angka 1-100, penilaian holistik Anda berdasarkan rata-rata tertimbang dari kriteria di bawah),
  "evaluasi_singkat": "Penjelasan umum dalam satu kalimat mengenai kualitas ringkasan.",
  "skor_rinci": {{
    "relevansi": {{ "skor": <angka>, "justifikasi": "Justifikasi singkat untuk skor relevansi." }},
    "kepadatan": {{ "skor": <angka>, "justifikasi": "Justifikasi singkat untuk skor kepadatan." }},
    "koherensi": {{ "skor": <angka>, "justifikasi": "Justifikasi singkat untuk skor koherensi." }},
    "konsistensi_faktual": {{ "skor": <angka>, "justifikasi": "Justifikasi singkat untuk skor konsistensi faktual." }},
    "kefasihan": {{ "skor": <angka>, "justifikasi": "Justifikasi singkat untuk skor kefasihan." }}
  }},
  "saran_perbaikan_utama": "Satu saran paling penting untuk meningkatkan kualitas ringkasan ini."
}}
"""

# Blok: Template Prompt untuk Evaluasi Terjemahan
# Serupa dengan template sebelumnya, namun ini dikhususkan untuk mengevaluasi kualitas terjemahan.
# Kriterianya disesuaikan untuk penerjemahan, seperti akurasi makna, kefasihan, dan pelestarian nuansa.
# Template ini juga memaksakan output JSON yang ketat.
TRANSLATION_JUDGE_PROMPT_TEMPLATE = """
Anda adalah seorang ahli linguistik dan penerjemah profesional multibahasa. Tugas Anda adalah mengevaluasi kualitas sebuah terjemahan yang dihasilkan oleh AI secara objektif dan terstruktur.

**DATA UNTUK EVALUASI:**
- **Bahasa Asli**: {source_lang}
- **Bahasa Target**: {target_lang}
- **Teks Asli**: ```{original_text}```
- **Teks Terjemahan (untuk dinilai)**: ```{translated_text}```

**INSTRUKSI PENILAIAN:**
Anda **HARUS** memberikan penilaian berdasarkan 4 kriteria utama. Untuk setiap kriteria, berikan skor (1-100) dan justifikasi singkat.
1.  **Akurasi Makna (Meaning Accuracy)**: Apakah terjemahan secara akurat menyampaikan makna, niat, dan pesan inti dari teks asli? (100 = Terjemahan sempurna tanpa kehilangan atau perubahan makna).
2.  **Kefasihan & Alami (Fluency & Naturalness)**: Apakah hasil terjemahan terdengar alami dan fasih di bahasa target, seolah-olah ditulis oleh penutur asli? (100 = Sangat alami, tata bahasa dan pilihan kata sempurna).
3.  **Kesesuaian Konteks & Nuansa (Context & Nuance Preservation)**: Apakah terjemahan berhasil mempertahankan gaya, nada (formal/informal), dan nuansa budaya dari teks asli? (100 = Semua nuansa dan konteks tersampaikan dengan baik).
4.  **Tata Bahasa & Ejaan (Grammar & Spelling)**: Apakah terjemahan bebas dari kesalahan tata bahasa, ejaan, dan tanda baca? (100 = Tidak ada kesalahan sama sekali).

**FORMAT OUTPUT (WAJIB):**
Berikan output **HANYA** dalam format JSON yang valid tanpa markdown ```json atau penjelasan lainnya. Semua teks justifikasi dan evaluasi **HARUS** dalam **Bahasa {target_lang}**.

**Struktur JSON yang WAJIB diikuti:**
{{
  "skor_keseluruhan": (angka 1-100, penilaian holistik Anda berdasarkan rata-rata tertimbang dari kriteria di bawah),
  "evaluasi_singkat": "Penjelasan umum dalam satu kalimat mengenai kualitas terjemahan.",
  "skor_rinci": {{
    "relevansi": {{ "skor": <skor_akurasi>, "justifikasi": "Justifikasi singkat untuk skor Akurasi Makna." }},
    "kepadatan": {{ "skor": <skor_kefasihan>, "justifikasi": "Justifikasi singkat untuk skor Kefasihan & Alami." }},
    "koherensi": {{ "skor": <skor_konteks>, "justifikasi": "Justifikasi singkat untuk skor Kesesuaian Konteks." }},
    "konsistensi_faktual": {{ "skor": <skor_tata_bahasa>, "justifikasi": "Justifikasi singkat untuk skor Tata Bahasa & Ejaan." }}
  }},
  "saran_perbaikan_utama": "Satu saran paling penting untuk meningkatkan kualitas terjemahan ini."
}}
"""

# Blok: Fungsi Pemformatan Prompt
# Fungsi-fungsi ini adalah pembantu (helper) sederhana yang mengambil data input
# dan memasukkannya ke dalam template yang sesuai untuk menciptakan prompt final yang siap dikirim ke AI.
def format_judge_prompt(input_text, output_text, target_lang):
    return JUDGE_PROMPT_TEMPLATE.format(input_text=input_text, output_text=output_text, target_lang=target_lang)

def format_translation_judge_prompt(original_text, translated_text, source_lang, target_lang):
    return TRANSLATION_JUDGE_PROMPT_TEMPLATE.format(
        original_text=original_text,
        translated_text=translated_text,
        source_lang=source_lang,
        target_lang=target_lang
    )

# Blok: Fungsi Evaluasi dengan Model Google (Gemini/Gemma)
# Fungsi asinkron ini bertanggung jawab untuk mengirim prompt ke API Google GenAI dan memproses hasilnya.
async def judge_with_google_model(prompt, client, model_path):
    if not client: return {"error": f"Klien Google tidak siap untuk model {model_path}."}
    raw_text = ""
    try:
        # Mencoba meminta output dalam format JSON secara langsung (fitur yang lebih baru).
        generation_config = GenerationConfig(response_mime_type="application/json")
        response = await client.aio.models.generate_content(
            model=f'models/{model_path}',
            contents=prompt,
            generation_config=generation_config
        )
        raw_text = response.text
    except Exception as e:
        # Jika model tidak mendukung JSON mode, coba lagi tanpa konfigurasi khusus (fallback).
        if "generation_config" in str(e) or "unsupported" in str(e):
            try:
                response = await client.aio.models.generate_content(model=f'models/{model_path}', contents=prompt)
                raw_text = response.text
            except Exception as fallback_e:
                return {"error": f"Google Judge Error (Fallback): {fallback_e}"}
        else:
            return {"error": f"Google Judge Error: {e}"}
    
    # Setelah mendapatkan teks mentah, coba ekstrak dan parse JSON-nya.
    try:
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        clean_text = match.group(0) if match else raw_text
        return json.loads(clean_text)
    except Exception as parse_err:
        return {"error": f"Gagal parsing JSON: {parse_err}. Respons: '{raw_text[:200]}...'"}

# Blok: Fungsi Evaluasi dengan Model Cohere
# Mirip dengan fungsi Google, tapi ini untuk API Cohere.
# Menggunakan `run_in_executor` karena library Cohere untuk Python belum sepenuhnya asinkron.
async def judge_with_cohere(prompt, client: cohere.Client):
    if not client: return {"error": "Klien Cohere tidak siap."}
    raw_text = ""
    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat(
                message=prompt,
                model="command-r-plus",
                preamble="Your sole function is to output a single, valid JSON object that strictly adheres to the user's requested schema. Do not add any text, comments, or markdown formatting.",
                temperature=0.1
            )
        )
        raw_text = response.text.strip()
        # Mencari objek JSON di dalam respons teks.
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if not match:
            return {"error": f"Cohere Judge Error: Tidak ada objek JSON di dalam respons. Respons: '{raw_text[:200]}...'"}
        json_string = match.group(0)
        # Membersihkan kemungkinan koma ekstra di akhir JSON yang bisa menyebabkan error parsing.
        json_string_cleaned = re.sub(r',\s*([\}\]])', r'\1', json_string)
        return json.loads(json_string_cleaned)
    except json.JSONDecodeError as e:
        return {"error": f"Cohere Judge Error (Gagal Parsing JSON): {e}. Respons mentah: '{raw_text[:200]}...'"}
    except Exception as e:
        return {"error": f"Cohere Judge Error: {e}"}

# Blok: Fungsi Evaluasi dengan Model Groq (Llama)
# Fungsi ini berinteraksi dengan API Groq, yang dikenal sangat cepat.
# API Groq mendukung output JSON secara native, menyederhanakan proses.
async def judge_with_groq(prompt, client):
    if not client: return {"error": "Klien Groq tidak siap."}
    try:
        loop = asyncio.get_running_loop()
        chat_completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                temperature=0.1,
                response_format={"type": "json_object"},
            )
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        return {"error": f"Groq Judge Error: {e}"}

# Blok: Orkestrator Evaluasi Ringkasan
# Fungsi ini adalah "manajer" yang menjalankan semua evaluasi secara paralel.
async def get_all_evaluations_async(input_text, output_text, target_lang, app_config):
    prompt = format_judge_prompt(input_text, output_text, target_lang)
    tasks = []
    model_names_for_ui = []
    
    # Memeriksa klien API mana yang aktif dan menambahkan tugas evaluasi untuk masing-masing.
    google_client = app_config.get('GEMINI_CLIENT')
    cohere_client = app_config.get('COHERE_CLIENT')
    groq_client = app_config.get('GROQ_CLIENT')
    
    if google_client:
        tasks.append(judge_with_google_model(prompt, google_client, model_path="gemma-3-27b-it"))
        model_names_for_ui.append("Google Gemma 3")
    if cohere_client:
        tasks.append(judge_with_cohere(prompt, cohere_client))
        model_names_for_ui.append("Cohere Command A 2025")
    if groq_client:
        tasks.append(judge_with_groq(prompt, groq_client))
        model_names_for_ui.append("Meta Llama 4 Maverick")
        
    if not tasks:
        return {"Error": {"error": "Tidak ada juri AI yang aktif untuk melakukan evaluasi."}}
    
    # Menjalankan semua tugas evaluasi secara bersamaan menggunakan asyncio.gather.
    results = await asyncio.gather(*tasks)
    
    # Menggabungkan hasil dengan nama modelnya menjadi satu kamus (dictionary) akhir.
    final_evaluations = {model_names_for_ui[i]: result for i, result in enumerate(results)}
    return final_evaluations

# Blok: Orkestrator Evaluasi Terjemahan
# Sama seperti fungsi sebelumnya, tapi ini khusus untuk mengelola evaluasi terjemahan.
async def get_all_translation_evaluations_async(original_text, translated_text, source_lang, target_lang, app_config):
    prompt = format_translation_judge_prompt(original_text, translated_text, source_lang, target_lang)
    
    tasks = []
    model_names_for_ui = []
    google_client = app_config.get('GEMINI_CLIENT')
    cohere_client = app_config.get('COHERE_CLIENT')
    groq_client = app_config.get('GROQ_CLIENT')
    
    if google_client:
        tasks.append(judge_with_google_model(prompt, google_client, model_path="gemma-3-27b-it"))
        model_names_for_ui.append("Google Gemma 3")
    if cohere_client:
        tasks.append(judge_with_cohere(prompt, cohere_client))
        model_names_for_ui.append("Cohere Command A 2025")
    if groq_client:
        tasks.append(judge_with_groq(prompt, groq_client))
        model_names_for_ui.append("Meta Llama 4 Maverick")
        
    if not tasks:
        return {"Error": {"error": "Tidak ada juri AI yang aktif untuk melakukan evaluasi."}}
        
    # Menjalankan tugas secara paralel dan menangani kemungkinan exception.
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Memproses hasil dengan lebih hati-hati, memeriksa apakah ada exception atau format respons yang salah.
    final_evaluations = {}
    for i, result in enumerate(results):
        model_name = model_names_for_ui[i]
        if isinstance(result, Exception):
            final_evaluations[model_name] = {"error": f"Async task failed: {str(result)}"}
        elif isinstance(result, dict) and "skor_rinci" not in result:
             final_evaluations[model_name] = {"error": result.get("error", "Format respons tidak valid.")}
        else:
            final_evaluations[model_name] = result
            
    return final_evaluations
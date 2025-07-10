import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, SnowballStemmer
from collections import Counter
import math
import csv
import os
import traceback
from rake_nltk import Rake
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer as SumyTokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.nlp.stemmers import Stemmer as SumyBaseStemmer

# Blok: Fungsi untuk memuat kamus normalisasi dari file CSV.
# Tujuannya adalah untuk mengubah singkatan atau kata slang menjadi bentuk standarnya (misal: 'ga' -> 'tidak').
def load_normalization_dict(csv_file_path_relative_to_utils):
    normalization_map = {}
    try:
        # Mencari path absolut ke file CSV agar bisa dijalankan dari mana saja.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_csv_path = os.path.join(base_dir, csv_file_path_relative_to_utils)
        if not os.path.exists(full_csv_path):
            return normalization_map
        
        # Membuka dan membaca file CSV, baris per baris.
        with open(full_csv_path, mode='r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            # Mengecek header untuk memastikan format file benar, dan me-skip-nya.
            try:
                header = next(reader)
                if header[0].strip().lower() != 'contraction' or header[1].strip().lower() != 'expansion':
                    infile.seek(0)
            except StopIteration:
                return normalization_map
            
            # Memproses setiap baris untuk mengisi kamus, mengubah singkatan (contraction) menjadi ekspansinya.
            for rows in reader:
                if len(rows) == 2:
                    contraction, expansion = rows[0].strip().lower(), rows[1].strip().lower()
                    if contraction: normalization_map[contraction] = expansion
    except Exception:
        # Menangani error jika terjadi masalah saat membaca file (misal, file tidak ada atau format salah).
        pass
    return normalization_map

# Blok: Inisialisasi Global
# Mendefinisikan nama file kamus dan memuatnya ke dalam variabel global agar bisa diakses oleh fungsi lain sekali saja.
NORMALIZATION_DICT_FILE = 'normalization_dict.csv'
normalization_map_global = load_normalization_dict(NORMALIZATION_DICT_FILE)

# Blok: Fungsi Pemilih Stemmer NLTK
# Stemming adalah proses mengubah kata ke bentuk dasarnya (misal: 'berlari', 'pelari' -> 'lari').
# Fungsi ini memilih algoritma stemmer NLTK yang tepat (Snowball atau Porter) berdasarkan bahasa yang diberikan.
def get_nltk_stemmer(language):
    lang_lower = language.lower()
    if lang_lower in SnowballStemmer.languages:
        try:
            return SnowballStemmer(lang_lower, ignore_stopwords=False)
        except Exception:
            if lang_lower == 'english':
                return PorterStemmer()
    elif lang_lower == 'english':
        return PorterStemmer()
    return None

import re
# Blok: Tokenizer Kalimat Khusus untuk Bahasa Indonesia
# Fungsi ini memecah teks Bahasa Indonesia menjadi kalimat.
# Dibuat khusus karena tokenizer standar sering salah mengenali titik pada singkatan (e.g., 'Bpk.', 'Jl.') sebagai akhir kalimat.
def rule_based_sentence_tokenizer_id(text):
    if not text or not text.strip():
        return []
    text = re.sub(r'\s{2,}', ' ', text).strip()
    
    # Daftar singkatan umum dalam Bahasa Indonesia yang menggunakan titik.
    abbreviations = [
        "bpk", "ibu", "sdr", "prof", "dr", "ir", "sh", "se", "h", "hj", "dll", "dsb", "yt",
        "no", "hlm", "dkk", "alm", "almarhumah", "a.n", "u.p", "ykh", "ybs", "thn", "tgl",
        "rp", "rs", "jl", "apt", "kab", "kec", "kel", "prov", "drs", "dra", "dllsb", "yth"
    ]
    
    # Melindungi titik pada singkatan dengan menggantinya sementara dengan placeholder.
    placeholder = "<SENTENCE_PERIOD_PLACEHOLDER>"
    for abbr in abbreviations:
        text = re.sub(r"(?<=\b" + re.escape(abbr) + r")\.(?!\s+[A-ZÀ-Ú]|[\"\'\(\[\¿\¡]|\s*$)", placeholder, text, flags=re.IGNORECASE)
        text = re.sub(r"(?<=\b" + re.escape(abbr) + r")\.$", placeholder, text, flags=re.IGNORECASE)
    
    # Memecah teks menjadi kalimat berdasarkan tanda baca akhir (titik, tanda tanya, seru).
    text = re.sub(r'([.?!…])\1*', r'\1<SPLIT_HERE>', text)
    sentences = text.split('<SPLIT_HERE>')
    
    # Membersihkan setiap kalimat dan mengembalikan titik yang tadi dilindungi.
    cleaned_sentences = []
    for sentence in sentences:
        s = sentence.strip()
        if s:
            s = s.replace(placeholder, ".")
            cleaned_sentences.append(s)
            
    if not cleaned_sentences and text.replace(placeholder, ".").strip():
        return [text.replace(placeholder, ".").strip()]
        
    return cleaned_sentences

# Blok: Kelas Stemmer Kustom untuk Library Sumy
# Kelas ini berfungsi sebagai 'jembatan' (wrapper) agar stemmer dari NLTK atau Sastrawi
# bisa digunakan oleh library Sumy, yang mengharapkan format stemmer tertentu.
class CustomSumyStemmer(SumyBaseStemmer):
    def __init__(self, language_for_sumy_base, stem_function_callable):
        self._stem_function = stem_function_callable
        if self._stem_function is None:
            self._stem_function = lambda word: word 
        super(CustomSumyStemmer, self).__init__(language_for_sumy_base)

    def __call__(self, word):
        return self._stem_function(word)

# Blok: Pra-pemrosesan Teks
# Fungsi ini membersihkan dan mengubah teks mentah menjadi format yang siap dianalisis.
# Prosesnya meliputi: tokenisasi kalimat, tokenisasi kata, normalisasi, penghapusan stopwords, dan stemming.
def preprocess_text_for_summary(text, language, sastrawi_stemmer_instance, stop_words_list):
    # Langkah 1: Memecah teks mentah menjadi kalimat. Menggunakan tokenizer khusus untuk Bahasa Indonesia atau NLTK untuk bahasa lain.
    sentences = []
    if language.lower() == 'indonesian':
        try:
            sentences = rule_based_sentence_tokenizer_id(text)
        except Exception as e:
            raise ValueError(f"Rule-based sentence tokenizer gagal untuk Bahasa Indonesia: {e}")
    else:
        try:
            sentences = sent_tokenize(text, language=language.lower())
        except LookupError:
            sentences = sent_tokenize(text, language='english')
        except Exception as e:
            raise ValueError(f"NLTK sent_tokenize gagal untuk bahasa '{language}': {e}")

    processed_sentences_tokens = []
    original_sentences_list = []
    nltk_generic_stemmer = None
    if language != 'indonesian':
        nltk_generic_stemmer = get_nltk_stemmer(language)

    # Langkah 2: Memproses setiap kalimat satu per satu.
    for original_sentence_text in sentences:
        original_sentences_list.append(original_sentence_text)
        current_sentence_lower = original_sentence_text.lower()
        words_in_current_sentence = word_tokenize(current_sentence_lower)
        
        # Membersihkan kalimat: normalisasi (misal: 'don't' -> 'do not'), dan membuang stopwords (kata umum seperti 'yang', 'di', 'dan').
        normalized_words = [normalization_map_global.get(word_token, word_token) for word_token in words_in_current_sentence] if normalization_map_global else words_in_current_sentence
        filtered_words_after_stopwords_and_norm = [word for word in normalized_words if word.isalnum() and word not in stop_words_list]

        if not filtered_words_after_stopwords_and_norm:
            processed_sentences_tokens.append([])
            continue

        # Langkah 3: Stemming. Mengubah setiap kata ke bentuk dasarnya.
        # Menggunakan Sastrawi untuk Indonesia atau NLTK stemmer untuk bahasa lain.
        final_word_tokens = []
        if language == 'indonesian' and sastrawi_stemmer_instance:
            sentence_for_sastrawi = ' '.join(filtered_words_after_stopwords_and_norm)
            stemmed_sentence_from_sastrawi = sastrawi_stemmer_instance.stem(sentence_for_sastrawi)
            words_after_sastrawi_stemming = word_tokenize(stemmed_sentence_from_sastrawi)
            final_word_tokens = [word for word in words_after_sastrawi_stemming if word.isalnum() and word not in stop_words_list]
        elif nltk_generic_stemmer:
            stemmed_nltk_words = []
            for word in filtered_words_after_stopwords_and_norm:
                try: stemmed_nltk_words.append(nltk_generic_stemmer.stem(word))
                except: stemmed_nltk_words.append(word)
            final_word_tokens = stemmed_nltk_words
        else:
            final_word_tokens = filtered_words_after_stopwords_and_norm

        if final_word_tokens: processed_sentences_tokens.append(final_word_tokens)
        else: processed_sentences_tokens.append([])
    return processed_sentences_tokens, original_sentences_list

# Blok: Kalkulasi TF (Term Frequency)
# Menghitung seberapa sering sebuah kata muncul dalam satu kalimat.
# Skor TF = (jumlah kemunculan kata) / (total kata dalam kalimat).
def calculate_tf_for_summary(processed_sentences):
    tf_scores = []
    for sentence_tokens in processed_sentences:
        tf_sent = {}
        if not sentence_tokens: tf_scores.append(tf_sent); continue
        word_counts = Counter(sentence_tokens)
        total_words_in_sentence = len(sentence_tokens)
        for word, count in word_counts.items(): tf_sent[word] = count / total_words_in_sentence
        tf_scores.append(tf_sent)
    return tf_scores

# Blok: Kalkulasi IDF (Inverse Document Frequency)
# Menghitung seberapa penting atau unik sebuah kata di seluruh dokumen (teks).
# Kata yang muncul di banyak kalimat akan punya skor IDF rendah.
def calculate_idf_for_summary(processed_sentences):
    idf_scores = {}
    total_sentences = len(processed_sentences)
    if total_sentences == 0: return idf_scores
    word_in_sentence_count = Counter()
    all_unique_words = set(word for sentence_tokens in processed_sentences for word in sentence_tokens)
    for word in all_unique_words:
        for sentence_tokens in processed_sentences:
            if word in sentence_tokens: word_in_sentence_count[word] += 1
    for word, count in word_in_sentence_count.items(): idf_scores[word] = math.log((total_sentences + 0.5) / (count + 0.5))
    return idf_scores

# Blok: Kalkulasi Skor Kalimat (TF-IDF)
# Memberi skor pada setiap kalimat dengan menggabungkan skor TF dan IDF (TF-IDF).
# Kalimat yang mengandung kata-kata dengan skor TF-IDF tinggi dianggap lebih penting.
def calculate_sentence_scores_for_summary(processed_sentences, tf_scores, idf_scores):
    sentence_scores = []
    for i, sentence_tokens in enumerate(processed_sentences):
        score = 0
        if not sentence_tokens: sentence_scores.append(0); continue
        for word in sentence_tokens:
            if word in idf_scores and word in tf_scores[i]: score += tf_scores[i][word] * idf_scores[word]
        sentence_scores.append(score / (len(sentence_tokens) + 1e-6))
    return sentence_scores

# Blok: Ekstraksi Kata Kunci dengan TF-IDF
# Mengekstrak kata kunci dari teks dengan mencari kata-kata yang memiliki skor TF-IDF global tertinggi.
# Kata kunci yang dihasilkan biasanya berupa kata tunggal.
def extract_keywords_with_tfidf(processed_sentences, idf_scores, max_keywords=10):
    if not processed_sentences or not idf_scores:
        return [], "STATUS_INFO: Tidak ada data untuk ekstraksi kata kunci TF-IDF."

    word_tfidf_scores = {}
    all_words = [word for sentence in processed_sentences for word in sentence]
    word_counts = Counter(all_words)
    total_words = len(all_words)

    if total_words == 0:
        return [], "STATUS_INFO: Tidak ada kata untuk dihitung skor TF-IDF nya."

    for word, count in word_counts.items():
        if word in idf_scores:
            tf = count / total_words
            word_tfidf_scores[word] = tf * idf_scores[word]

    sorted_keywords = sorted(word_tfidf_scores.items(), key=lambda item: item[1], reverse=True)
    top_keywords = [word for word, score in sorted_keywords[:max_keywords]]
    
    if not top_keywords:
        return [], "STATUS_INFO: Tidak ditemukan kata kunci signifikan dengan TF-IDF."
        
    return top_keywords, ""

# Blok: Ekstraksi Kata Kunci dengan RAKE
# Mengekstrak kata kunci menggunakan algoritma RAKE (Rapid Automatic Keyword Extraction).
# RAKE sangat baik dalam menemukan frasa kunci (terdiri dari beberapa kata) daripada hanya kata tunggal.
def extract_keywords_with_rake(text, language='english', max_keywords=10):
    if not text or not text.strip():
        return [], "STATUS_INFO: Teks kosong, tidak ada kata kunci untuk diekstrak."
    nltk_lang_for_stopwords_rake = language.lower()
    try:
        current_stopwords_rake = stopwords.words(nltk_lang_for_stopwords_rake)
    except OSError:
        current_stopwords_rake = stopwords.words('english')
    
    try:
        r = Rake(language=nltk_lang_for_stopwords_rake, stopwords=current_stopwords_rake, min_length=1, max_length=3)
        r.extract_keywords_from_text(text)
        ranked_phrases = r.get_ranked_phrases_with_scores()
        keywords = [phrase for score, phrase in ranked_phrases[:max_keywords]]
        if not keywords:
            return [], "STATUS_INFO: Tidak ditemukan kata kunci signifikan dari teks ini."
        return keywords, ""
    except Exception as e:
        return [], f"STATUS_ERROR: Gagal mengekstrak kata kunci dengan RAKE: {str(e)}"

# Blok: Utilitas Pemformatan Paragraf
# Fungsi bantuan untuk mengubah daftar kalimat hasil ringkasan menjadi teks yang lebih rapi dan mudah dibaca
# dengan menggabungkannya ke dalam paragraf.
def _format_summary_into_paragraphs(sentences_list, sentences_per_paragraph=3):
    if not sentences_list:
        return ""
    
    paragraphs = []
    for i in range(0, len(sentences_list), sentences_per_paragraph):
        chunk = sentences_list[i : i + sentences_per_paragraph]
        paragraphs.append(" ".join(chunk))
        
    return "\n\n".join(paragraphs)

# Blok: Peringkasan dengan Algoritma TextRank (menggunakan Sumy)
# Fungsi ini melakukan peringkasan menggunakan algoritma TextRank. TextRank melihat kalimat sebagai
# node dalam sebuah graf dan memberi peringkat berdasarkan hubungan antar kalimat.
def summarize_with_textrank_sumy(text_input, num_sentences, actual_language_of_text, sastrawi_stemmer_instance_for_sumy_tr, max_keywords=10):
    if not text_input or not text_input.strip():
        return "STATUS_ERROR: Teksnya kosong, Kak...", [], ""

    # Menyiapkan teks untuk parser Sumy. Untuk Bahasa Indonesia, kalimat dipisahkan dulu dengan tokenizer khusus.
    processed_text_for_sumy_parser = text_input
    language_for_sumy_tokenizer = 'english' 
    language_for_custom_stemmer_base = 'english'

    if actual_language_of_text.lower() == 'indonesian':
        try:
            indonesian_sentences = rule_based_sentence_tokenizer_id(text_input)
            if not indonesian_sentences:
                return "STATUS_INFO: Tidak dapat memecah teks menjadi kalimat (rule-based).", [], ""
            processed_text_for_sumy_parser = "\n".join(indonesian_sentences)
        except Exception as e_rule_based_tok:
             return f"STATUS_ERROR: Gagal tokenisasi rule-based untuk Bahasa Indonesia: {str(e_rule_based_tok)}", [], ""
    else:
        try:
            sentences_other_lang = sent_tokenize(text_input, language=actual_language_of_text.lower())
            processed_text_for_sumy_parser = "\n".join(sentences_other_lang)
            language_for_sumy_tokenizer = actual_language_of_text.lower()
            language_for_custom_stemmer_base = actual_language_of_text.lower()
        except LookupError:
            processed_text_for_sumy_parser = text_input.replace('.', '.\n').replace('?', '?\n').replace('!', '!\n')
        except Exception as e_nltk_other_lang:
            return f"STATUS_ERROR: Gagal tokenisasi NLTK untuk '{actual_language_of_text}': {str(e_nltk_other_lang)}", [], ""

    # Menyiapkan stemmer yang akan digunakan oleh Sumy, memakai kelas kustom 'CustomSumyStemmer'.
    stemmer_function_to_pass = None
    if actual_language_of_text.lower() == 'indonesian' and sastrawi_stemmer_instance_for_sumy_tr:
        stemmer_function_to_pass = sastrawi_stemmer_instance_for_sumy_tr.stem
        language_for_custom_stemmer_base = 'english' 
    elif actual_language_of_text.lower() != 'indonesian':
        generic_nltk_stemmer = get_nltk_stemmer(actual_language_of_text)
        if generic_nltk_stemmer:
            stemmer_function_to_pass = generic_nltk_stemmer.stem
            language_for_custom_stemmer_base = actual_language_of_text.lower()

    sumy_custom_stemmer_instance = CustomSumyStemmer(language_for_custom_stemmer_base, stemmer_function_to_pass)

    try:
        # Inti proses: membuat parser, menjalankan TextRank summarizer, dan mendapatkan kalimat-kalimat ringkasan.
        sumy_tokenizer = SumyTokenizer(language_for_sumy_tokenizer)
        parser = PlaintextParser.from_string(processed_text_for_sumy_parser, sumy_tokenizer)
        summarizer = TextRankSummarizer(stemmer=sumy_custom_stemmer_instance)
        summary_sentences_sumy = summarizer(parser.document, num_sentences)
        summary_result_list = [str(sentence) for sentence in summary_sentences_sumy]
        
        # Memformat hasil ringkasan menjadi paragraf dan mengekstrak kata kunci menggunakan RAKE.
        summary_text = _format_summary_into_paragraphs(summary_result_list)
        if not summary_text:
            return "STATUS_INFO: TextRank tidak menghasilkan ringkasan.", [], ""
        keywords_list_tr, kw_error_msg_tr = extract_keywords_with_rake(text_input, actual_language_of_text, max_keywords)
        
        return summary_text, keywords_list_tr, kw_error_msg_tr
    except Exception as e_sumy:
        # Menangani error yang mungkin terjadi selama proses peringkasan dengan Sumy.
        tb_str = traceback.format_exc()
        return f"STATUS_ERROR: Kesulitan meringkas dengan TextRank (Sumy): {str(e_sumy)}\nTraceback: {tb_str}", [], ""

# Blok: Fungsi Utama (Pintu Gerbang)
# Ini adalah fungsi utama yang akan dipanggil dari luar.
# Fungsinya adalah sebagai 'dispatcher' yang mengarahkan proses ke algoritma yang dipilih (TF-IDF atau TextRank).
def get_summary_and_keywords(text_to_process, num_sentences, language, sastrawi_stemmer_instance, max_keywords=10, algo_choice='tfidf'):
    summary_text_result = "STATUS_ERROR: Gagal memproses ringkasan."
    keywords_list_result = []
    final_error_message_summary = ""
    final_error_message_keywords = ""

    # Memeriksa apakah teks input kosong atau tidak. Jika ya, langsung kembalikan pesan error.
    if not text_to_process or not text_to_process.strip():
        final_error_message_summary = "STATUS_ERROR: Teksnya kosong, Kak... Tidak bisa memproses kekosongan (￣ω￣;)"
        final_error_message_keywords = "STATUS_INFO: Teks kosong, tidak ada kata kunci."
        return summary_text_result, keywords_list_result, final_error_message_summary, final_error_message_keywords

    # Jika pengguna memilih 'textrank', panggil fungsi `summarize_with_textrank_sumy`.
    if algo_choice.lower() == 'textrank':
        summary_output, keywords_output_data, kw_err_msg_from_tr_func = \
            summarize_with_textrank_sumy(text_to_process, num_sentences, language, sastrawi_stemmer_instance, max_keywords)
        
        # Mengelola hasil dan pesan error dari fungsi TextRank.
        if summary_output.startswith("STATUS_ERROR:") or summary_output.startswith("STATUS_INFO:"):
            final_error_message_summary = summary_output
            if not final_error_message_summary.startswith("STATUS_ERROR:"):
                 summary_text_result = ""
            else:
                summary_text_result = "Gagal dengan TextRank."
        else:
            summary_text_result = summary_output
        
        keywords_list_result = keywords_output_data
        if kw_err_msg_from_tr_func:
            final_error_message_keywords = kw_err_msg_from_tr_func
    
    # Jika pengguna memilih 'tfidf', jalankan seluruh alur TF-IDF.
    elif algo_choice.lower() == 'tfidf':
        try:
            # Menyiapkan daftar stopwords (kata-kata umum yang akan diabaikan).
            current_stopwords_lang = language.lower()
            try: stop_words_list = set(stopwords.words(current_stopwords_lang))
            except OSError:
                stop_words_list = set(stopwords.words('english'))

            if language == 'indonesian':
                stop_words_list.update(['yg', 'dg', 'rt', 'dgn', 'ny', 'd', 'klo', 'kalo', 'amp', 'biar', 'bikin', 'bilang', 'gak', 'ga', 'krn', 'nya', 'nih', 'sih', 'si', 'tau', 'tdk', 'tuh', 'utk', 'ya', 'jd', 'jgn', 'sdh', 'aja', 'n', 't','hehe', 'dll', 'dst', 'sbg'])

            # Menjalankan pra-pemrosesan teks.
            processed_tokens_list, original_sentences = preprocess_text_for_summary(
                text_to_process, language, sastrawi_stemmer_instance, stop_words_list
            )
            if not processed_tokens_list or all(not s for s in processed_tokens_list):
                final_error_message_summary = "STATUS_ERROR: Setelah diproses (TFIDF), teksnya tidak punya kata-kata penting."
                summary_text_result = final_error_message_summary
            else:
                # Menghitung skor TF, IDF, dan skor akhir untuk setiap kalimat.
                tf_scores = calculate_tf_for_summary(processed_tokens_list)
                idf_scores = calculate_idf_for_summary(processed_tokens_list)
                sentence_scores = calculate_sentence_scores_for_summary(processed_tokens_list, tf_scores, idf_scores)
                
                # Menggabungkan skor dengan kalimat aslinya dan memberi peringkat.
                min_len_check = min(len(sentence_scores), len(original_sentences))
                if len(sentence_scores) != len(original_sentences):
                     scored_original_sentences_with_index = list(zip(sentence_scores[:min_len_check], original_sentences[:min_len_check], range(min_len_check)))
                else:
                    scored_original_sentences_with_index = list(zip(sentence_scores, original_sentences, range(len(original_sentences))))
                
                scored_original_sentences_with_index.sort(key=lambda x: x[0], reverse=True)
                
                # Memilih kalimat dengan skor tertinggi sesuai jumlah yang diminta.
                num_to_summarize = min(num_sentences, len(scored_original_sentences_with_index))
                if num_to_summarize == 0 and len(scored_original_sentences_with_index) > 0:
                    num_to_summarize = 1
                
                # Mengurutkan kembali kalimat ringkasan sesuai urutan aslinya di teks.
                top_sentences_data = scored_original_sentences_with_index[:num_to_summarize]
                top_sentences_data.sort(key=lambda x: x[2])
                
                # Memformat ringkasan dan mengekstrak kata kunci TF-IDF.
                top_sentences_list = [sent_data[1] for sent_data in top_sentences_data]
                temp_summary = _format_summary_into_paragraphs(top_sentences_list)
                summary_text_result = temp_summary.strip() if temp_summary else "STATUS_INFO: TF-IDF tidak menghasilkan ringkasan."

                kw_list, kw_err = extract_keywords_with_tfidf(processed_tokens_list, idf_scores, max_keywords)
                keywords_list_result = kw_list
                if kw_err: final_error_message_keywords = kw_err

        except ValueError as ve:
            # Menangani error yang bisa terjadi selama proses TF-IDF.
            final_error_message_summary = f"STATUS_ERROR: {str(ve)}"
            summary_text_result = final_error_message_summary
        except Exception as e_tfidf:
            final_error_message_summary = f"STATUS_ERROR: Error internal saat peringkasan TF-IDF: {str(e_tfidf)}"
            summary_text_result = final_error_message_summary

    else:
        # Jika pengguna memasukkan nama algoritma yang tidak dikenal.
        final_error_message_summary = f"STATUS_ERROR: Algoritma peringkasan '{algo_choice}' tidak dikenal."
        summary_text_result = final_error_message_summary

    # Mengembalikan hasil akhir: teks ringkasan, daftar kata kunci, dan pesan error (jika ada).
    return summary_text_result, keywords_list_result, final_error_message_summary, final_error_message_keywords
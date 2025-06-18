from deep_translator import GoogleTranslator
from deep_translator.exceptions import NotValidLength
import traceback
import time 

MAX_CHARS_PER_CHUNK = 4800 

def split_text_into_chunks(text, max_length=MAX_CHARS_PER_CHUNK):
    chunks = []
    current_chunk = ""
    
    paragraphs = text.split('\n')
    sentences_to_process = []
    for para in paragraphs:
        if para.strip(): 
            sentences_in_para = para.split('. ')
            for i, sentence in enumerate(sentences_in_para):
                sentence_with_period = sentence + ('.' if i < len(sentences_in_para) - 1 and sentence.strip() else '')
                sentences_to_process.append(sentence_with_period)
        else: 
            if current_chunk.strip():
                 sentences_to_process.append("\n")
    
    for sentence_text in sentences_to_process:
        if sentence_text == "\n": 
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
                current_chunk = "" 
            continue

        if len(current_chunk) + len(sentence_text) + 1 <= max_length:
            current_chunk += sentence_text + " "
        else:
            if len(sentence_text) > max_length: 
                words = sentence_text.split(' ')
                temp_sub_chunk = ""
                for word in words:
                    if len(temp_sub_chunk) + len(word) + 1 <= max_length:
                        temp_sub_chunk += word + " "
                    else:
                        if temp_sub_chunk.strip(): chunks.append(temp_sub_chunk.strip())
                        temp_sub_chunk = word + " "
                if temp_sub_chunk.strip(): chunks.append(temp_sub_chunk.strip())
                current_chunk = "" 
            else: 
                if current_chunk.strip(): chunks.append(current_chunk.strip())
                current_chunk = sentence_text + " "
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        
    final_chunks = []
    for chunk in chunks:
        if len(chunk) > max_length: 
            for i in range(0, len(chunk), max_length):
                final_chunks.append(chunk[i:i+max_length])
        elif chunk.strip(): 
            final_chunks.append(chunk)
            
    return final_chunks


def translate_text(text_to_translate, target_language='en', source_language='auto'):
    if not text_to_translate or not text_to_translate.strip():
        return "STATUS_ERROR: Tidak ada teks untuk diterjemahkan oleh Kami, Kak (・へ・)"
    

    try:
        translator_instance = GoogleTranslator(source=source_language, target=target_language)
    except Exception as e_init:
        traceback.print_exc()
        return f"STATUS_ERROR: Kami gagal menyiapkan alat penerjemah: {str(e_init)}"

    try:
        if not target_language or len(target_language) < 2:
            return f"STATUS_ERROR: Bahasa target '{target_language}' tidak valid, Kak. Kami jadi bingung! (＠_＠;)"

        if len(text_to_translate) > MAX_CHARS_PER_CHUNK:
            chunks = split_text_into_chunks(text_to_translate, MAX_CHARS_PER_CHUNK)
            if not chunks:
                return "STATUS_ERROR: Kami gagal memecah teks, Kak. Kami jadi bingung, teksnya jadi kosong setelah coba dipecah. (・_・ヾ"

            translated_chunks = []
            for i, chunk in enumerate(chunks):
                if not chunk.strip(): 
                    continue
                
                # time.sleep(0.2)
                
                try:
                    translated_chunk = translator_instance.translate(chunk)
                    if translated_chunk:
                        translated_chunks.append(translated_chunk)
                    else:
                        translated_chunks.append(f"[Kami tidak mendapat hasil terjemahan untuk bagian ini: '{chunk[:50]}...']")
                except NotValidLength as nvl_err:
                    translated_chunks.append(f"[Bagian ini ('{chunk[:50]}...') gagal terjemah karena masalah panjang: {str(nvl_err)}]")
                except Exception as chunk_err:
                    traceback.print_exc()
                    translated_chunks.append(f"[Kamin gagal menerjemahkan bagian ini ('{chunk[:50]}...'): {str(chunk_err)}]")
            
            final_translation = " ".join(translated_chunks)
            return final_translation if final_translation.strip() else "STATUS_ERROR: Kami sudah mencoba, tapi hasil terjemahan akhirnya kosong, Kak. (´･ω･`)"
        else:
            translated_text = translator_instance.translate(text_to_translate)
            return translated_text if translated_text else "STATUS_ERROR: Kami mencoba menerjemahkan, tapi hasilnya kosong. Aneh... (・・？)"

    except NotValidLength as nvl_main_err: 
        traceback.print_exc()
        return f"STATUS_ERROR: Oops, ada masalah dengan panjang teks untuk diterjemahkan, Kakr. ({str(nvl_main_err)})"
    except Exception as e:
        traceback.print_exc()
        if "invalid destination language" in str(e).lower():
            return f"STATUS_ERROR: Oops, bahasa target '{target_language}' sepertinya tidak didukung, Kak ( T Д T )"
        return f"STATUS_ERROR: Oops, Kami gagal menerjemahkan teksnya karena error tak terduga: {str(e)}"
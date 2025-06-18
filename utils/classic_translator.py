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


LANGUAGE_MAP = {
    'English': 'en',
    'Indonesian': 'id',
    'Japanese': 'ja',
    'Korean': 'ko',
    'Chinese': 'zh-CN',
    'Arabic': 'ar',
    'German': 'de',
    'auto': 'auto' 
}

def translate_text(text_to_translate, target_language='English', source_language='auto'):
    if not text_to_translate or not text_to_translate.strip():
        return "STATUS_ERROR: Tidak ada teks untuk diterjemahkan oleh Kami, Kak (・へ・)"

    source_code = LANGUAGE_MAP.get(source_language, source_language.lower())
    target_code = LANGUAGE_MAP.get(target_language, target_language.lower())
    
    try:
        translator_instance = GoogleTranslator(source=source_code, target=target_code)
    except Exception as e_init:
        return f"STATUS_ERROR: Kami gagal menyiapkan alat penerjemah: {str(e_init)}"

    try:
        if not target_code or len(target_code) < 2:
            return f"STATUS_ERROR: Bahasa target '{target_language}' tidak valid, Kak."

        if len(text_to_translate) > MAX_CHARS_PER_CHUNK:
            chunks = split_text_into_chunks(text_to_translate, MAX_CHARS_PER_CHUNK)
            if not chunks:
                return "STATUS_ERROR: Kami gagal memecah teks, Kak."

            translated_chunks = []
            for i, chunk in enumerate(chunks):
                if not chunk.strip(): continue
                try:
                    translated_chunk = translator_instance.translate(chunk)
                    if translated_chunk: translated_chunks.append(translated_chunk)
                except Exception as chunk_err:
                    translated_chunks.append(f"[Gagal menerjemahkan bagian: {str(chunk_err)}]")
            
            return " ".join(translated_chunks)
        else:
            return translator_instance.translate(text_to_translate)

    except Exception as e:
        traceback.print_exc()
        if "invalid destination language" in str(e).lower():
            return f"STATUS_ERROR: Bahasa target '{target_language}' sepertinya tidak didukung, Kak."
        return f"STATUS_ERROR: Oops, Kami gagal menerjemahkan teksnya karena: {str(e)}"
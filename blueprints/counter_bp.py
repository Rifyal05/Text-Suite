from flask import Blueprint, render_template, request, session
import re
import textstat

counter_bp = Blueprint('counter_bp', 
                       __name__, 
                       template_folder='../templates', 
                       url_prefix='/counter')

def count_stats(text):
    """Menghitung berbagai statistik dari teks."""
    if not text or not text.strip():
        return {
            'char_count_with_spaces': 0,
            'char_count_without_spaces': 0,
            'word_count': 0,
            'sentence_count': 0,
            'paragraph_count': 0,
            'syllable_count': 0,
            'avg_word_length': 0,
            'avg_sentence_length': 0,
        }

    char_count_with_spaces = len(text)
    char_count_without_spaces = len(text.replace(" ", "").replace("\n", "").replace("\r", ""))
    
    words = re.findall(r'\b\w+\b', text.lower()) 
    word_count = len(words)
    
    sentences = re.split(r'[.!?]\s+|\n', text)
    sentence_count = len([s for s in sentences if s.strip()])
    if sentence_count == 0 and word_count > 0 :
        sentence_count = 1

    paragraphs = re.split(r'\n\s*\n+', text.strip()) 
    paragraph_count = len([p for p in paragraphs if p.strip()])
    if paragraph_count == 0 and word_count > 0: 
        paragraph_count = 1

    try:
        syllable_count_val = textstat.syllable_count(text)
    except Exception as e:
        syllable_count_val = "N/A (error)" 

    total_word_length = sum(len(word) for word in words)
    avg_word_length = round(total_word_length / word_count, 2) if word_count > 0 else 0
    
    avg_sentence_length = round(word_count / sentence_count, 2) if sentence_count > 0 else 0

    return {
        'char_count_with_spaces': char_count_with_spaces,
        'char_count_without_spaces': char_count_without_spaces,
        'word_count': word_count,
        'sentence_count': sentence_count,
        'paragraph_count': paragraph_count,
        'syllable_count': syllable_count_val,
        'avg_word_length': avg_word_length,
        'avg_sentence_length': avg_sentence_length,
    }


@counter_bp.route('/', methods=['GET', 'POST'])
def counter_page():
    form_data = {
        'text_to_count': session.get('counter_text_to_count', ''),
    }
    stats_results = None 

    if request.method == 'POST':
        form_data['text_to_count'] = request.form.get('text_to_count', "")
        session['counter_text_to_count'] = form_data['text_to_count']

        if not form_data['text_to_count'].strip():
            stats_results = count_stats("")
        else:
            stats_results = count_stats(form_data['text_to_count'])
            
    return render_template('counter_page.html', 
                           title="Penghitung Kata & Karakter", 
                           form_data=form_data, 
                           stats_results=stats_results)
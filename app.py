from flask import Flask
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
import os
import datetime
from dotenv import load_dotenv
import groq
import cohere
import openai
from transformers import AutoTokenizer, AutoModel

try:
    from google import genai
    GOOGLE_GENAI_MODULE_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_MODULE_AVAILABLE = False

from blueprints.home_bp import home_bp
from blueprints.summarizer_bp import summarizer_bp
from blueprints.translator_bp import translator_bp
from blueprints.counter_bp import counter_bp
from blueprints.readability_bp import readability_bp 
from blueprints.proofreader_bp import proofreader_bp
from blueprints.api_bp import api_bp
from blueprints.paraphraser_bp import paraphraser_bp

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)


GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_GENAI_MODULE_AVAILABLE:
    if GEMINI_API_KEY:
        try:
            gemini_client = genai.Client() 
            app.config['GEMINI_CLIENT'] = gemini_client
            app.config['GEMINI_READY'] = True
            print("✅ Gemini Client berhasil diinisialisasi (SDK Baru).")
        except Exception as e:
            print(f"❌ Gagal inisialisasi Gemini Client: {e}")
            app.config['GEMINI_CLIENT'] = None
            app.config['GEMINI_READY'] = False
    else:
        print("⚠️ PERINGATAN: GOOGLE_API_KEY tidak ditemukan. Fitur Gemini tidak akan berfungsi.")
        app.config['GEMINI_READY'] = False
else:
    print("🚨 GAGAL mengimpor 'google.genai'. Fitur Gemini tidak akan berfungsi.")
    app.config['GEMINI_READY'] = False

# Klien Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    app.config['GROQ_CLIENT'] = groq.Groq(api_key=GROQ_API_KEY)
    print("✅ Groq Client berhasil diinisialisasi.")
else:
    app.config['GROQ_CLIENT'] = None
    print("⚠️ PERINGATAN: GROQ_API_KEY tidak ditemukan.")

COHERE_API_KEY = os.getenv("COHERE_KEY")
if COHERE_API_KEY:
    try:
        app.config['COHERE_CLIENT'] = cohere.Client(COHERE_API_KEY)
        print("✅ Cohere Client berhasil diinisialisasi.")
    except Exception as e:
        app.config['COHERE_CLIENT'] = None
        print(f"❌ Gagal inisialisasi Cohere Client: {e}")
else:
    app.config['COHERE_CLIENT'] = None
    print("⚠️ PERINGATAN: COHERE_API_KEY tidak ditemukan.")
    
# Klien OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    try:
        app.config['OPENAI_CLIENT'] = openai.OpenAI(api_key=OPENAI_API_KEY)
        app.config['OPENAI_READY'] = True
        print("✅ OpenAI Client berhasil diinisialisasi.")
    except Exception as e:
        app.config['OPENAI_CLIENT'] = None
        app.config['OPENAI_READY'] = False
        print(f"❌ Gagal inisialisasi OpenAI Client: {e}")
else:
    app.config['OPENAI_CLIENT'] = None
    app.config['OPENAI_READY'] = False
    print("⚠️ PERINGATAN: OPENAI_API_KEY tidak ditemukan.")

sastrawi_factory = StemmerFactory()
app.config['SASTRAWI_STEMMER_INSTANCE'] = sastrawi_factory.create_stemmer()

app.register_blueprint(home_bp)
app.register_blueprint(summarizer_bp)
app.register_blueprint(translator_bp)
app.register_blueprint(counter_bp)
app.register_blueprint(readability_bp)
app.register_blueprint(proofreader_bp)
app.register_blueprint(api_bp) 
app.register_blueprint(paraphraser_bp)


if __name__ == '__main__': 
    app.run(debug=True, host='0.0.0.0', port=5000)
from flask import Blueprint, render_template

home_bp = Blueprint('home_bp', __name__, template_folder='../templates') 

@home_bp.route('/')
def home():
    return render_template('home.html', title="Selamat Datang di Shinny Suite Teks!")
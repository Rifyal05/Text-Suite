from flask import Blueprint, request, jsonify, current_app


api_bp = Blueprint('api_bp', __name__, url_prefix='/api')

@api_bp.route('/count_tokens', methods=['POST'])
def count_tokens():

    gemini_client = current_app.config.get('GEMINI_CLIENT')
    

    if not gemini_client:

        return jsonify({"error": "Gemini client tidak siap"}), 500

    try:

        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "Data 'text' tidak ditemukan di request"}), 400

        text_to_count = data['text']
        
        model_path = 'gemini-2.5-flash-preview-05-20'
        response = gemini_client.models.count_tokens(contents=text_to_count, model=model_path)
        return jsonify({
            "token_count": response.total_tokens
        })

    except Exception as e:
        print(f"Error di count_tokens: {e}")
        return jsonify({"error": str(e)}), 500
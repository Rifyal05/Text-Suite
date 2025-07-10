import time
import traceback

def call_openai_response_blocking(prompt, client, model_name="gpt-4.1-mini-2025-04-14"):
    if not client:
        return None, "Klien OpenAI tidak siap."
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
        content = response.choices[0].message.content
        return content, None
    except Exception as e:
        traceback.print_exc()
        error_message = f"Kegagalan server saat memanggil OpenAI '{model_name}': {str(e)}"
        return None, error_message

def call_generative_model_blocking(model_id, prompt, app_config):
    if model_id == 'gpt':
        client = app_config.get('OPENAI_CLIENT')
        model_name = "gpt-4.1-mini-2025-04-14"
        return call_openai_response_blocking(prompt, client, model_name)

    elif model_id == 'gpt-4o-nano':
        client = app_config.get('OPENAI_CLIENT')
        model_name = "gpt-4.1-nano-2025-04-14"
        return call_openai_response_blocking(prompt, client, model_name)
        
    else:
        return None, f"Model blocking '{model_id}' tidak dikenal atau tidak didukung."

def stream_gemini_response(prompt, client, model_path='gemini-2.5-flash'):
    if not client:
        yield "event: error\ndata: Klien Google AI tidak siap.\n\n"
        return
    try:
        from . import gemini_module
        response_stream = gemini_module.panggil_gemini_model_streaming(prompt, client, model_path=model_path)
        for item in response_stream:
            if isinstance(item, str) and item.startswith("STATUS_ERROR:"):
                yield f"event: error\ndata: {item.replace('STATUS_ERROR:', '').strip()}\n\n"
                return
            elif hasattr(item, 'text'):
                text_to_send = item.text.replace('\n', '\\n')
                yield f"data: {text_to_send}\n\n"
                time.sleep(0.01)
    except Exception as e:
        traceback.print_exc()
        error_message = f"Kegagalan server saat streaming dari model Google '{model_path}': {str(e)}"
        yield f"event: error\ndata: {error_message}\n\n"

def call_generative_model_streaming(model_id, prompt, app_config):
    if model_id == 'gemini':
        client = app_config.get('GEMINI_CLIENT')
        model_path = 'gemini-2.5-flash'
        return stream_gemini_response(prompt, client, model_path)
    
    elif model_id == 'learnlm':
        client = app_config.get('GEMINI_CLIENT')
        model_path = 'gemini-2.0-flash'
        return stream_gemini_response(prompt, client, model_path)
    
    else:
        def unknown_model_stream():
            yield f"event: error\ndata: Model streaming '{model_id}' tidak dikenal atau tidak didukung.\n\n"
        return unknown_model_stream()
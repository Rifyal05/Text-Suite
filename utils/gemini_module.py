import traceback
import re
import ast
import json

try:
    from google.genai.errors import ClientError, PermissionDenied
except ImportError:
    from google.api_core import exceptions as core_exceptions
    ClientError = core_exceptions.GoogleAPIError
    PermissionDenied = core_exceptions.PermissionDenied

MAX_TOKENS = 50000 

def panggil_gemini_model(prompt_text, gemini_client, model_path='gemini-2.5-flash-preview-05-20'):
    if not gemini_client:
        return "STATUS_ERROR: Layanan Google AI tidak siap atau tidak terkonfigurasi."
    
    try:
        token_check_response = gemini_client.models.count_tokens(contents=prompt_text, model=model_path)
        if token_check_response.total_tokens > MAX_TOKENS:
            return f"STATUS_ERROR: Input terlalu panjang ({token_check_response.total_tokens:,} tokens). Batas maksimum adalah {MAX_TOKENS:,} tokens untuk model ini."

        response = gemini_client.models.generate_content(
            model=model_path,
            contents=prompt_text
        )
        
        if not response.candidates or not hasattr(response.candidates[0], 'content') or not response.candidates[0].content.parts:
            block_reason = "Unknown"
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                block_reason = response.prompt_feedback.block_reason.name
            return f"STATUS_ERROR: Output dari model '{model_path}' tidak valid atau diblokir. Alasan: {block_reason}. Coba ubah teks input Anda."

        return response.text

    except ClientError as e:
        error_string = str(e)
        if "429" in error_string and "RESOURCE_EXHAUSTED" in error_string:
            retry_delay = None
            try:
                json_start_index = error_string.find('{')
                if json_start_index != -1:
                    json_substring = error_string[json_start_index:]
                    error_details_dict = json.loads(json_substring)
                    details_list = error_details_dict.get('error', {}).get('details', [])
                    for detail_item in details_list:
                        if isinstance(detail_item, dict) and 'retryDelay' in detail_item:
                            retry_delay = detail_item.get('retryDelay')
                            break
            except Exception:
                pass 
            
            if retry_delay:
                delay_seconds = retry_delay.replace('s', '')
                return (f"STATUS_ERROR: Lalu lintas sangat padat! Batas penggunaan API tercapai. "
                        f"Silakan coba lagi dalam {delay_seconds} detik.")
            else:
                return ("STATUS_ERROR: Lalu lintas sangat padat! Batas penggunaan API tercapai. "
                        "Silakan tunggu beberapa saat sebelum mencoba kembali.")
        else:
            return f"STATUS_ERROR: Terjadi kesalahan dari sisi Gemini (Client Error): {e}"

    except PermissionDenied:
        return "STATUS_ERROR: API Key Gemini tidak valid atau izin ditolak. Mohon periksa kembali API Key Anda."

    except Exception as e:
        return "STATUS_ERROR: Terjadi kesalahan tak terduga saat menghubungi layanan Gemini. Silakan coba lagi nanti."


def panggil_gemini_model_streaming(prompt_text, gemini_client, model_path='gemini-2.5-flash-preview-05-20'):
    if not gemini_client:
        yield "STATUS_ERROR: Klien Google AI tidak valid."
        return

    try:
        token_check_response = gemini_client.models.count_tokens(contents=prompt_text, model=model_path)
        if token_check_response.total_tokens > MAX_TOKENS:
            yield f"STATUS_ERROR: Input terlalu panjang ({token_check_response.total_tokens:,} tokens)."
            return

        response_stream = gemini_client.models.generate_content_stream(
            model=model_path,
            contents=prompt_text
        )
        
        for chunk in response_stream:
            yield chunk

    except ClientError as e:
        error_string = str(e)
        
        if "429" in error_string and "RESOURCE_EXHAUSTED" in error_string:
            retry_delay = None
            try:
                json_start_index = error_string.find('{')
                if json_start_index != -1:
                    json_substring = error_string[json_start_index:]
                    error_details_dict = json.loads(json_substring)
                    
                    details_list = error_details_dict.get('error', {}).get('details', [])
                    for detail_item in details_list:
                        if isinstance(detail_item, dict) and 'retryDelay' in detail_item:
                            retry_delay = detail_item.get('retryDelay')
                            break
            
            except (json.JSONDecodeError, AttributeError, IndexError):
                pass
            
            if retry_delay:
                delay_seconds = retry_delay.replace('s', '')
                yield (f"STATUS_ERROR: Lalu lintas sangat padat! Batas penggunaan API tercapai. "
                       f"Silakan coba lagi dalam {delay_seconds} detik.")
            else:
                yield ("STATUS_ERROR: Lalu lintas sangat padat! Batas penggunaan API tercapai. "
                       "Silakan tunggu beberapa saat sebelum mencoba kembali.")
        else:
            yield f"STATUS_ERROR: Terjadi kesalahan dari sisi Gemini (Client Error): {e}"

    except PermissionDenied:
        yield "STATUS_ERROR: API Key Gemini tidak valid atau izin ditolak. Mohon periksa kembali API Key Anda."

    except Exception as e:
        error_string = str(e)
        if "429" in error_string and "RESOURCE_EXHAUSTED" in error_string:
            retry_delay = None
            try:
                json_start_index = error_string.find("{")
                if json_start_index != -1:
                    json_substring = error_string[json_start_index:]
                    error_details_dict = ast.literal_eval(json_substring)
                    details_list = error_details_dict.get('error', {}).get('details', [])
                    for detail_item in details_list:
                        if (
                            isinstance(detail_item, dict) and
                            detail_item.get('@type') == 'type.googleapis.com/google.rpc.RetryInfo'
                        ):
                            retry_delay = detail_item.get('retryDelay')
                            break

            except Exception:
                pass

            if retry_delay:
                delay_seconds = retry_delay.replace('s', '').strip()
                yield (f"STATUS_ERROR: Lalu lintas sangat padat! Batas penggunaan API tercapai. "
                    f"Silakan coba lagi dalam {delay_seconds} detik.")
            else:
                yield ("STATUS_ERROR: Lalu lintas sangat padat! Batas penggunaan API tercapai. "
                    "Silakan tunggu beberapa saat sebelum mencoba kembali.")
        else:
            yield f"STATUS_ERROR: Terjadi kesalahan dari sisi Gemini (Client Error): {e}"

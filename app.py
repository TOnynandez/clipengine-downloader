from flask import Flask, request, jsonify
import yt_dlp
import os
import uuid
from urllib.parse import urlparse
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

# Configurar Cloudinary (storage gratuito)
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "ok",
        "service": "ClipEngine Video Downloader",
        "endpoints": {
            "/download": "POST - Download YouTube video",
            "/health": "GET - Health check"
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})

@app.route('/download', methods=['POST'])
def download_video():
    try:
        data = request.json
        video_url = data.get('url')
        start_time = data.get('start', '00:00')
        end_time = data.get('end', None)
        
        if not video_url:
            return jsonify({"error": "URL is required"}), 400
        
        # Generar nombre único
        video_id = str(uuid.uuid4())[:8]
        output_path = f'/tmp/{video_id}.mp4'
        
        # Configurar yt-dlp
        ydl_opts = {
            'format': 'best[height<=720]',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
        }
        
        # Nota: descargamos el video completo
        # Creatomate se encargará de cortar en el timestamp correcto
        
        # Descargar video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'video')
        
        # Subir a Cloudinary
        upload_result = cloudinary.uploader.upload(
            output_path,
            resource_type="video",
            public_id=f"clipengine/{video_id}",
            folder="clipengine"
        )
        
        # Limpiar archivo temporal
        if os.path.exists(output_path):
            os.remove(output_path)
        
        return jsonify({
            "status": "success",
            "video_id": video_id,
            "title": title,
            "url": upload_result['secure_url'],
            "duration": upload_result.get('duration'),
            "format": "mp4"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def parse_time(time_str):
    """Convierte MM:SS o HH:MM:SS a segundos"""
    parts = time_str.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

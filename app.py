from flask import Flask, request, jsonify
import yt_dlp
import os
import uuid
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "ok",
        "service": "ClipEngine Video Downloader v2",
        "endpoints": {
            "/download": "POST - Download YouTube clip",
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
        end_time = data.get('end', '01:00')
        
        if not video_url:
            return jsonify({"error": "URL is required"}), 400
        
        start_sec = parse_time(start_time)
        end_sec = parse_time(end_time)
        duration = end_sec - start_sec
        
        if duration > 120:
            duration = 120
        
        video_id = str(uuid.uuid4())[:8]
        output_path = f'/tmp/{video_id}.mp4'
        
        ydl_opts = {
            'format': 'worst[ext=mp4]/worst',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 3,
            'download_ranges': lambda info, ydl: [{'start_time': start_sec, 'end_time': end_sec}],
            'force_keyframes_at_cuts': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
            },
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'video')
        
        if not os.path.exists(output_path):
            return jsonify({"error": "Download failed - file not created"}), 500
        
        file_size = os.path.getsize(output_path)
        if file_size < 1000:
            return jsonify({"error": f"Download failed - file too small ({file_size} bytes)"}), 500
        
        upload_result = cloudinary.uploader.upload(
            output_path,
            resource_type="video",
            public_id=f"clips/{video_id}",
            eager=[{'format': 'mp4', 'quality': 'auto'}],
            eager_async=False
        )
        
        if os.path.exists(output_path):
            os.remove(output_path)
        
        return jsonify({
            "status": "success",
            "video_id": video_id,
            "title": title,
            "url": upload_result['secure_url'],
            "duration": upload_result.get('duration'),
            "clip_range": f"{start_time} - {end_time}"
        })
        
    except Exception as e:
        try:
            if 'output_path' in locals() and os.path.exists(output_path):
                os.remove(output_path)
        except:
            pass
        return jsonify({"error": str(e)}), 500

def parse_time(time_str):
    try:
        parts = str(time_str).split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0
    except:
        return 0

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

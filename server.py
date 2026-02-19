import os
from flask import Flask, request, jsonify, render_template
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION ---
# Please set your GEMINI API KEY in the environment variable 'GEMINI_API_KEY'
# For local development, run: export GEMINI_API_KEY="your_key_here"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in environment variables.")

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def get_video_id(url):
    """Extracts video ID from various YouTube URL formats."""
    # Simple extraction logic - can be improved with regex
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return None

def fetch_transcript(video_id):
    try:
        api = YouTubeTranscriptApi()
        # Get list of transcripts
        transcript_list = api.list(video_id)
        
        # Find transcript: priority PT, then EN, then auto-generated
        try:
             # We prioritize explicit Portuguese, then English.
             # The existing find_transcript logic respects the order.
             transcript = transcript_list.find_transcript(['pt-BR', 'en'])
             print(f"Transcript found! Language: {transcript.language_code}")
        except Exception:
             # If priority languages not found, fall back to the first available transcript
             transcript = next(iter(transcript_list))
             print(f"Fallback transcript used. Language: {transcript.language_code}")

        fetched = transcript.fetch()
        
        # Combine text from snippets
        # fetched.snippets is a list of FetchedTranscriptSnippet objects
        full_text = " ".join([snippet.text for snippet in fetched.snippets])
        return full_text
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None

def summarize_text(text):
    if not GEMINI_API_KEY:
        return "Error: API Key missing on server."
        
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        # Updated prompt to explicitly handle translation if input is English
        prompt = (
            "Analyze the following YouTube video transcript (which may be in Portuguese or English). "
            "Ignore any intro/outro fluff. "
            "Write a detailed and structured summary in **Brazilian Portuguese** (Português do Brasil). "
            "Ensure the output is entirely in Portuguese, even if the source is English.\n\n"
            f"Transcript Text: \n\n{text}"
        )
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error summarizing: {e}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/summarize', methods=['POST'])
def summarize_endpoint():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request: JSON body expected"}), 400

    url = data.get('url')

    if not url:
        return jsonify({"error": "No URL provided"}), 400
        
    video_id = get_video_id(url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400
        
    print(f"Processing URL: {url} (ID: {video_id})")
    
    transcript = fetch_transcript(video_id)
    if not transcript:
        return jsonify({"error": "Could not retrieve transcript (maybe no captions available?)"}), 404
        
    # Cap transcript length if necessary for token limits (Gemini Pro has 32k context, usually enough for most vids)
    # Simple truncation if extremely large
    if len(transcript) > 100000: 
        transcript = transcript[:100000] + "..."
        
    summary = summarize_text(transcript)
    
    return jsonify({"summary": summary})

if __name__ == '__main__':
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(port=5001, debug=debug_mode)

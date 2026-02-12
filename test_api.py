from youtube_transcript_api import YouTubeTranscriptApi

def test_fallback_logic(video_id, expected_lang_code):
    print(f"\n--- Testing Fallback Logic for {video_id} (Expect: {expected_lang_code}) ---")
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        # This is the exact priority list from server.py
        priority_languages = ['pt-BR', 'en']
        
        print(f"Available languages: {[t.language_code for t in transcript_list]}")
        
        transcript = transcript_list.find_transcript(priority_languages)
        print(f"Selected Transcript Language: {transcript.language_code}")
        
        if transcript.language_code == expected_lang_code:
            print("✅ SUCCESS: Correct fallback language selected.")
        else:
            print(f"❌ FAILURE: Expected {expected_lang_code}, got {transcript.language_code}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_fallback_logic('HwKDe80NydA', 'en')
    test_fallback_logic('hlkYw4kL9A0', 'pt-BR')

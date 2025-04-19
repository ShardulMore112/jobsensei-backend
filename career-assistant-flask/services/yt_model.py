import requests
import os
from dotenv import load_dotenv

load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def search_youtube_tutorials(skill, language=None, max_results=5):
    base_url = "https://www.googleapis.com/youtube/v3/search"
    query = f"{skill} tutorial" + (f" {language}" if language else "")

    language_codes = {
        "hindi": "hi",
        "tamil": "ta",
        "telugu": "te",
        "kannada": "kn",
        "marathi": "mr"
    }

    params = {
        "part": "snippet",
        "q": query,
        "maxResults": max_results,
        "type": "video",
        "videoDefinition": "high",
        "videoDuration": "medium",
        "key": YOUTUBE_API_KEY
    }

    if language and language.lower() in language_codes:
        params["relevanceLanguage"] = language_codes[language.lower()]

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        results = []

        for item in data.get("items", []):
            video_id = item["id"]["videoId"]
            results.append({
                "title": item["snippet"]["title"],
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
                "description": item["snippet"]["description"]
            })

        return results

    except requests.exceptions.RequestException as err:
        return {"error": str(err)}

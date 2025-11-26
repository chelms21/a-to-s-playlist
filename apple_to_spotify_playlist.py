import requests
from bs4 import BeautifulSoup
import os
import time
import base64

# ------------------------------
# CONFIGURATION
# ------------------------------
APPLE_PLAYLIST_URL = "https://music.apple.com/us/playlist/favorite-songs/pl.u-ovURBX17aZ"
NEW_PLAYLIST_NAME = "Imported from Apple Music"

SPOTIFY_CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
SPOTIFY_REFRESH_TOKEN = os.environ["SPOTIFY_REFRESH_TOKEN"]
SPOTIFY_USER_ID = os.environ["SPOTIFY_USER_ID"]

SPOTIFY_API_BASE = "https://api.spotify.com/v1"

# ------------------------------
# STEP 0: Get fresh access token
# ------------------------------
def get_access_token(client_id, client_secret, refresh_token):
    url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_header}"}
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    resp = requests.post(url, headers=headers, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]

# ------------------------------
# STEP 1: Scrape Apple Music Playlist
# ------------------------------
def get_songs_from_apple_playlist(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    songs = []
    for item in soup.select('div.songs-list-row__song-name'):
        title = item.get_text(strip=True)
        parent = item.find_parent('div.songs-list-row')
        artist = None
        if parent:
            art_el = parent.select_one('div.songs-list-row__byline a')
            if art_el:
                artist = art_el.get_text(strip=True)
        if title and artist:
            songs.append((title, artist))
    return songs

# ------------------------------
# STEP 2: Search Spotify
# ------------------------------
def search_spotify_track(access_token, track_name, artist_name):
    query = f"track:{track_name} artist:{artist_name}"
    url = f"{SPOTIFY_API_BASE}/search"
    params = {"q": query, "type": "track", "limit": 1}
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers, params=params).json()
    items = resp.get("tracks", {}).get("items", [])
    if items:
        return items[0]["uri"]
    return None

# ------------------------------
# STEP 3: Create Playlist
# ------------------------------
def create_spotify_playlist(access_token, user_id, name):
    url = f"{SPOTIFY_API_BASE}/users/{user_id}/playlists"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"name": name, "public": True}
    resp = requests.post(url, headers=headers, json=payload).json()
    return resp["id"]

# ------------------------------
# STEP 4: Add Tracks
# ------------------------------
def add_tracks_to_playlist(access_token, playlist_id, uris):
    url = f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    for i in range(0, len(uris), 100):
        chunk = uris[i:i+100]
        payload = {"uris": chunk}
        requests.post(url, headers=headers, json=payload)

# ------------------------------
# MAIN SCRIPT
# ------------------------------
def main():
    print("Getting Spotify access token...")
    access_token = get_access_token(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN)

    print("Fetching Apple Music playlist...")
    songs = get_songs_from_apple_playlist(APPLE_PLAYLIST_URL)
    print(f"Found {len(songs)} songs")

    track_uris = []
    for i, (title, artist) in enumerate(songs, start=1):
        print(f"Searching Spotify: {title} by {artist} ({i}/{len(songs)})")
        uri = search_spotify_track(access_token, title, artist)
        if uri:
            track_uris.append(uri)
        else:
            print(f"  ⚠️ Could not find {title} by {artist}")
        time.sleep(0.2)

    if not track_uris:
        print("No tracks found. Exiting.")
        return

    playlist_id = create_spotify_playlist(access_token, SPOTIFY_USER_ID, NEW_PLAYLIST_NAME)
    add_tracks_to_playlist(access_token, playlist_id, track_uris)
    print(f"Playlist created with {len(track_uris)} tracks!")

if __name__ == "__main__":
    main()

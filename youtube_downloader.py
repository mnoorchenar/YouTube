import os
import yt_dlp

def download_youtube_content():
    # Ask the user to input the YouTube URL
    url = input("Please enter the YouTube URL (video or playlist): ").strip()
    
    try:
        # Check if the URL is a playlist or a single video using yt-dlp
        with yt_dlp.YoutubeDL() as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:  # Playlist contains 'entries' key
                download_playlist(url)
            else:
                download_single_video(url)
    except Exception as e:
        print(f"An error occurred: {e}")

def create_folder_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def download_single_video(url):
    with yt_dlp.YoutubeDL() as ydl:
        info = ydl.extract_info(url, download=False)
        video_title = info['title']
        channel_name = info['uploader']
        
        # Create a folder for the channel if it doesn't exist
        folder_path = os.path.join(os.getcwd(), channel_name)
        create_folder_if_not_exists(folder_path)

        # Define the full path for the video file
        video_file = os.path.join(folder_path, f"{video_title}.mp4")

        # Skip if the video already exists
        if os.path.exists(video_file):
            print(f"Video '{video_title}' already exists. Skipping download.")
            return
        
        # Download the video
        print(f"Downloading video: {video_title}")
        ydl_opts = {
            'outtmpl': os.path.join(folder_path, f"{video_title}.mp4"),
            'format': 'best',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"Downloaded: {video_title}")

def download_playlist(url):
    with yt_dlp.YoutubeDL() as ydl:
        playlist_info = ydl.extract_info(url, download=False)
        channel_name = playlist_info['uploader']
        playlist_title = playlist_info['title']

        # Create a folder for the channel
        channel_folder_path = os.path.join(os.getcwd(), channel_name)
        create_folder_if_not_exists(channel_folder_path)

        # Create a subfolder for the playlist
        playlist_folder_path = os.path.join(channel_folder_path, playlist_title)
        create_folder_if_not_exists(playlist_folder_path)

        print(f"Downloading playlist: {playlist_title}")

        # Loop through videos in the playlist and download each one
        for idx, video in enumerate(playlist_info['entries'], start=1):
            video_title = video['title']
            video_filename = f"{idx:02d}. {video_title}.mp4"  # Prefix video order number
            video_path = os.path.join(playlist_folder_path, video_filename)

            # Skip if the video already exists
            if os.path.exists(video_path):
                print(f"Video '{video_title}' already exists in playlist. Skipping download.")
                continue

            # Download the video
            print(f"Downloading {video_title} as {video_filename}")
            ydl_opts = {
                'outtmpl': os.path.join(playlist_folder_path, video_filename),
                'format': 'best',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video['webpage_url']])
            print(f"Downloaded: {video_filename}")

# Start the program
download_youtube_content()
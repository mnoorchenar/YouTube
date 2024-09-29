
# YouTube Video & Playlist Downloader with `yt-dlp`

This Python script allows you to download YouTube videos and playlists using the `yt-dlp` library. The script automatically organizes videos by channel name and playlist (if applicable) into folders, and it skips any files that already exist.

## Features
- Downloads individual YouTube videos.
- Downloads entire YouTube playlists.
- Automatically creates folders for channels and playlists.
- Saves videos in proper order for playlists, prefixing video filenames with numbers (e.g., `01. Video Title`).
- Skips videos that have already been downloaded to avoid duplicates.

## Requirements
- Python 3.x
- `yt-dlp` library

## Installation

1. Clone the repository or download the script.

    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2. Install the required dependencies. You can install the `yt-dlp` package via `pip`:

    ```bash
    pip install yt-dlp
    ```

## Usage

1. Run the script:

    ```bash
    python youtube_downloader.py
    ```

2. Enter the YouTube URL (video or playlist) when prompted:

    ```bash
    Please enter the YouTube URL (video or playlist):
    ```

3. The script will determine whether the URL is for a single video or a playlist:
    - If it's a video, it will create a folder with the channel name and save the video.
    - If it's a playlist, it will create a subfolder with the playlist name and save the videos in order.

### Example

For a single video:

```
Please enter the YouTube URL (video or playlist):
https://www.youtube.com/watch?v=example_video

Output:
Downloading video: Example Video Title
Downloaded: Example Video Title
```

For a playlist:

```
Please enter the YouTube URL (video or playlist):
https://www.youtube.com/playlist?list=example_playlist

Output:
Downloading playlist: Example Playlist Title
Downloading 01. First Video Title
Downloaded: 01. First Video Title
Downloading 02. Second Video Title
Downloaded: 02. Second Video Title
```

## Folder Structure

- If the URL is for a **single video**, the folder structure will look like this:

  ```
  /Channel Name/
    - Video Title.mp4
  ```

- If the URL is for a **playlist**, the folder structure will look like this:

  ```
  /Channel Name/
    /Playlist Name/
      - 01. First Video Title.mp4
      - 02. Second Video Title.mp4
  ```

## Dependencies

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - A command-line program to download videos from YouTube and other video platforms.

You can install it using:

```bash
pip install yt-dlp
```

## Contributing

Feel free to submit issues or pull requests if you'd like to contribute!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

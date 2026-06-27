import os
import logging
import yt_dlp
from config import TEMP_FOLDER
from utils import ensure_temp_folder

logger = logging.getLogger(__name__)


def _base_opts(extra: dict = None) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    if extra:
        opts.update(extra)
    return opts


def get_video_info(url: str) -> dict | None:
    try:
        with yt_dlp.YoutubeDL(_base_opts({"skip_download": True})) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        logger.error(f"YouTube get_info error: {e}")
        return None


def get_available_qualities(info: dict) -> list[dict]:
    """
    Returns list of dicts:
    { label, format_id, ext, filesize, height, fps }
    """
    formats = info.get("formats", [])
    seen = {}

    for f in formats:
        height = f.get("height")
        if not height:
            continue
        vcodec = f.get("vcodec", "none")
        if vcodec == "none":
            continue
        fps = f.get("fps") or 0
        label = f"{height}p"
        if fps and fps > 30:
            label = f"{height}p{int(fps)}"

        filesize = f.get("filesize") or f.get("filesize_approx") or 0
        fid = f.get("format_id", "")

        if label not in seen or filesize > seen[label]["filesize"]:
            seen[label] = {
                "label": label,
                "format_id": fid,
                "ext": f.get("ext", "mp4"),
                "filesize": filesize,
                "height": height,
                "fps": fps,
            }

    # Sort descending by height then fps
    result = sorted(seen.values(), key=lambda x: (x["height"], x["fps"]), reverse=True)
    return result


def download_video(url: str, format_id: str, video_id: str) -> str | None:
    """Downloads video+audio merged. Returns file path or None."""
    ensure_temp_folder()
    out_template = os.path.join(TEMP_FOLDER, f"{video_id}.%(ext)s")

    opts = _base_opts({
        "format": f"{format_id}+bestaudio/best",
        "outtmpl": out_template,
        "merge_output_format": "mp4",
    })

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Might be .mp4 after merge
            if not os.path.exists(filename):
                filename = filename.rsplit(".", 1)[0] + ".mp4"
            if os.path.exists(filename):
                return filename
            # Fallback: find any file with video_id
            for f in os.listdir(TEMP_FOLDER):
                if video_id in f:
                    return os.path.join(TEMP_FOLDER, f)
    except Exception as e:
        logger.error(f"YouTube download_video error: {e}")
    return None


def download_audio(url: str, video_id: str) -> str | None:
    """Downloads best audio as mp3. Returns file path or None."""
    ensure_temp_folder()
    out_template = os.path.join(TEMP_FOLDER, f"{video_id}_audio.%(ext)s")

    opts = _base_opts({
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    })

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
        mp3_path = os.path.join(TEMP_FOLDER, f"{video_id}_audio.mp3")
        if os.path.exists(mp3_path):
            return mp3_path
        for f in os.listdir(TEMP_FOLDER):
            if video_id in f and f.endswith(".mp3"):
                return os.path.join(TEMP_FOLDER, f)
    except Exception as e:
        logger.error(f"YouTube download_audio error: {e}")
    return None


def get_thumbnail_url(info: dict) -> str | None:
    return info.get("thumbnail") or None
# tiktok.py
import os
import requests
import yt_dlp
import logging
from typing import Dict, Optional
from config import TEMP_FOLDER, COBALT_API, DOWNLOAD_TIMEOUT
from utils import get_unique_filename

logger = logging.getLogger(__name__)


class TikTokDownloader:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'prefer_insecure': True,
            'socket_timeout': DOWNLOAD_TIMEOUT,
        }

    def get_video_info(self, url: str) -> Optional[Dict]:
        """Получение информации о видео"""
        try:
            # Пробуем yt-dlp
            info = self._get_info_ytdlp(url)
            if info:
                return info

            # Резерв - Cobalt API
            info = self._get_info_cobalt(url)
            if info:
                return info

        except Exception as e:
            logger.error(f"Ошибка получения информации TikTok: {e}")

        return None

    def _get_info_ytdlp(self, url: str) -> Optional[Dict]:
        """Получение информации через yt-dlp"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return None

                # Получение доступных форматов
                formats = []
                for f in info.get('formats', []):
                    if f.get('vcodec') != 'none':
                        if 'mp4' in f.get('ext', '') or 'mov' in f.get('ext', ''):
                            format_note = f.get('format_note', '')
                            formats.append({
                                'format_id': f['format_id'],
                                'quality': format_note or '720p',
                                'ext': f.get('ext', 'mp4'),
                                'filesize': f.get('filesize') or f.get('filesize_approx', 0)
                            })

                return {
                    'id': info.get('id'),
                    'title': info.get('title', 'TikTok Video'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'thumbnail': info.get('thumbnail', ''),
                    'description': info.get('description', '')[:200],
                    'view_count': info.get('view_count', 0),
                    'formats': formats,
                    'is_short': True
                }

        except Exception as e:
            logger.error(f"Ошибка yt-dlp для TikTok: {e}")
            return None

    def _get_info_cobalt(self, url: str) -> Optional[Dict]:
        """Получение информации через Cobalt API"""
        try:
            payload = {
                "url": url,
                "vCodec": "h264",
                "vQuality": "720",
                "aFormat": "mp3",
                "isNoWatermark": True,
                "isTTFullAudio": True
            }

            response = requests.post(
                COBALT_API,
                json=payload,
                headers={'Accept': 'application/json'},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'error':
                    return None

                video_url = data.get('url')
                if not video_url:
                    return None

                return {
                    'id': data.get('id', ''),
                    'title': data.get('title', 'TikTok Video'),
                    'duration': data.get('duration', 0),
                    'uploader': data.get('author', 'Unknown'),
                    'thumbnail': data.get('thumbnail', ''),
                    'description': '',
                    'view_count': 0,
                    'formats': [{
                        'format_id': 'best',
                        'quality': '720p',
                        'ext': 'mp4',
                        'filesize': 0
                    }],
                    'is_short': True,
                    'direct_url': video_url,
                    'audio_url': data.get('audio')
                }

        except Exception as e:
            logger.error(f"Ошибка Cobalt API: {e}")
            return None

    def download_video(self, url: str, format_id: str = 'best') -> Optional[str]:
        """Скачивание видео"""
        try:
            # Пробуем yt-dlp
            filepath = self._download_ytdlp(url, format_id)
            if filepath:
                return filepath

            # Резерв - Cobalt API
            filepath = self._download_cobalt(url)
            if filepath:
                return filepath

        except Exception as e:
            logger.error(f"Ошибка скачивания TikTok видео: {e}")

        return None

    def _download_ytdlp(self, url: str, format_id: str) -> Optional[str]:
        """Скачивание через yt-dlp"""
        try:
            filename = get_unique_filename('mp4')
            filepath = os.path.join(TEMP_FOLDER, filename)

            ydl_opts = {
                **self.ydl_opts,
                'format': format_id,
                'outtmpl': filepath,
                'merge_output_format': 'mp4'
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
                if os.path.exists(filepath):
                    return filepath

        except Exception as e:
            logger.error(f"Ошибка yt-dlp скачивания TikTok: {e}")

        return None

    def _download_cobalt(self, url: str) -> Optional[str]:
        """Скачивание через Cobalt API"""
        try:
            payload = {
                "url": url,
                "vCodec": "h264",
                "vQuality": "720",
                "aFormat": "mp3",
                "isNoWatermark": True,
                "isTTFullAudio": True
            }

            response = requests.post(
                COBALT_API,
                json=payload,
                headers={'Accept': 'application/json'},
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'error':
                    return None

                video_url = data.get('url')
                if not video_url:
                    return None

                # Скачиваем видео
                filename = get_unique_filename('mp4')
                filepath = os.path.join(TEMP_FOLDER, filename)

                response = requests.get(video_url, stream=True, timeout=60)
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    if os.path.exists(filepath):
                        return filepath

        except Exception as e:
            logger.error(f"Ошибка Cobalt скачивания TikTok: {e}")

        return None

    def download_audio(self, url: str) -> Optional[str]:
        """Скачивание аудио"""
        try:
            # Пробуем yt-dlp
            filepath = self._download_audio_ytdlp(url)
            if filepath:
                return filepath

            # Резерв - Cobalt API
            filepath = self._download_audio_cobalt(url)
            if filepath:
                return filepath

        except Exception as e:
            logger.error(f"Ошибка скачивания TikTok аудио: {e}")

        return None

    def _download_audio_ytdlp(self, url: str) -> Optional[str]:
        """Скачивание аудио через yt-dlp"""
        try:
            filename = get_unique_filename('mp3')
            filepath = os.path.join(TEMP_FOLDER, filename)

            ydl_opts = {
                **self.ydl_opts,
                'format': 'bestaudio/best',
                'outtmpl': filepath.rsplit('.', 1)[0],
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
                if os.path.exists(filepath):
                    return filepath

        except Exception as e:
            logger.error(f"Ошибка yt-dlp скачивания TikTok аудио: {e}")

        return None

    def _download_audio_cobalt(self, url: str) -> Optional[str]:
        """Скачивание аудио через Cobalt API"""
        try:
            payload = {
                "url": url,
                "vCodec": "h264",
                "vQuality": "720",
                "aFormat": "mp3",
                "isNoWatermark": True,
                "isTTFullAudio": True
            }

            response = requests.post(
                COBALT_API,
                json=payload,
                headers={'Accept': 'application/json'},
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'error':
                    return None

                audio_url = data.get('audio')
                if not audio_url:
                    return None

                # Скачиваем аудио
                filename = get_unique_filename('mp3')
                filepath = os.path.join(TEMP_FOLDER, filename)

                response = requests.get(audio_url, stream=True, timeout=60)
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    if os.path.exists(filepath):
                        return filepath

        except Exception as e:
            logger.error(f"Ошибка Cobalt скачивания TikTok аудио: {e}")

        return None

    def download_thumbnail(self, url: str) -> Optional[str]:
        """Скачивание превью"""
        try:
            info = self.get_video_info(url)
            if not info or not info.get('thumbnail'):
                return None

            thumbnail_url = info['thumbnail']
            filename = get_unique_filename('jpg')
            filepath = os.path.join(TEMP_FOLDER, filename)

            response = requests.get(thumbnail_url, timeout=30)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return filepath

        except Exception as e:
            logger.error(f"Ошибка скачивания превью TikTok: {e}")

        return None
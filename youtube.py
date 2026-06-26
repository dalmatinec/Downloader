# youtube.py
import os
import yt_dlp
import logging
from typing import Dict, List, Optional
from config import TEMP_FOLDER, DOWNLOAD_TIMEOUT
from utils import get_unique_filename, format_duration

logger = logging.getLogger(__name__)


class YouTubeDownloader:
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
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return None

                # Получение доступных форматов
                formats = []
                for f in info.get('formats', []):
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        if 'mp4' in f.get('ext', ''):
                            format_note = f.get('format_note', '')
                            if format_note:
                                formats.append({
                                    'format_id': f['format_id'],
                                    'quality': format_note,
                                    'ext': f.get('ext', 'mp4'),
                                    'filesize': f.get('filesize') or f.get('filesize_approx', 0)
                                })

                # Получение уникальных качеств
                unique_qualities = {}
                for f in formats:
                    quality = f['quality']
                    if quality and quality not in unique_qualities:
                        unique_qualities[quality] = f

                # Сортировка качеств
                quality_order = ['144p', '240p', '360p', '480p', '720p', '1080p', '2K', '4K']
                sorted_qualities = []
                for q in quality_order:
                    if q in unique_qualities:
                        sorted_qualities.append({
                            'quality': q,
                            'format_id': unique_qualities[q]['format_id'],
                            'ext': unique_qualities[q]['ext'],
                            'filesize': unique_qualities[q]['filesize']
                        })

                return {
                    'id': info.get('id'),
                    'title': info.get('title', 'Без названия'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Неизвестно'),
                    'thumbnail': info.get('thumbnail', ''),
                    'description': info.get('description', '')[:500],
                    'view_count': info.get('view_count', 0),
                    'formats': sorted_qualities,
                    'is_short': info.get('duration', 0) < 60
                }

        except Exception as e:
            logger.error(f"Ошибка получения информации: {e}")
            return None

    def download_video(self, url: str, format_id: str) -> Optional[str]:
        """Скачивание видео"""
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
                
                # Поиск файла с другим расширением
                for ext in ['mp4', 'webm', 'mkv']:
                    test_path = filepath.rsplit('.', 1)[0] + '.' + ext
                    if os.path.exists(test_path):
                        return test_path
                return None

        except Exception as e:
            logger.error(f"Ошибка скачивания видео: {e}")
            return None

    def download_audio(self, url: str) -> Optional[str]:
        """Скачивание аудио в MP3"""
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
                
                for ext in ['mp3', 'm4a', 'webm']:
                    test_path = filepath.rsplit('.', 1)[0] + '.' + ext
                    if os.path.exists(test_path):
                        return test_path
                return None

        except Exception as e:
            logger.error(f"Ошибка скачивания аудио: {e}")
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

            import requests
            response = requests.get(thumbnail_url, timeout=30)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return filepath

        except Exception as e:
            logger.error(f"Ошибка скачивания превью: {e}")
        
        return None
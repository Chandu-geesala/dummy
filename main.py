import os
import json
import asyncio
import aiohttp
import logging
import tempfile
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import random
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import threading
import mimetypes


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)





class TelegramDownloaderBot:
    SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.webm', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.3gp', '.ogv'}
    storage_lock = threading.Lock()
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        api_url = "https://chandugeesala0-str.hf.space/random"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        random_links = data.get("random_links") or data.get("links") or []
                    else:
                        random_links = []
        except Exception as e:
            logger.error(f"Failed to call /random API: {e}")
            random_links = []
    
        if not random_links:
            await update.message.reply_text("No link history found yet. Start sharing links!")
            return
    
        # Send each link as a separate message for preview
        for i, link in enumerate(random_links):
            await update.message.reply_text(f"{i+1}. {link}")
    
        # Optionally, you can also send a summary message before or after:
        # await update.message.reply_text("🕑 Sent 10 random links from history!")





    async def save_user_link(self, user_id, username, link):
        """
        Send user_id, username, and the link to the external API.
        """
        api_url = "https://chandugeesala0-str.hf.space/input"
        # Build the payload in the same structure as before
        payload = {
            str(user_id): {
                "username": username,
                "links": [link]
            }
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload) as resp:
                    if resp.status != 200:
                        logger.error(f"API /input returned status {resp.status}")
        except Exception as e:
            logger.error(f"Failed to send to /input API: {e}")




    

    def get_user_links(self, user_id):
        """
        Return list of links for user_id (as str), or [].
        """
        filename = "abc.txt"
        try:
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except Exception:
            data = {}
        return data.get(str(user_id), {}).get("links", [])






    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.video_callback_params = {}
        self.terabox_api_url = "https://teradl-api.dapuntaratya.com/generate_file"
        self.terabox_link_api_url = "https://teradl-api.dapuntaratya.com/generate_link"
        self.vkr_api_url = "https://vkrdownloader.xyz/server/"
        self.vkr_api_key = "vkrdownloader"
        self.supported_sites = [
            "YouTube", "Facebook", "Instagram", "TikTok", "Twitter", "TeraBox",
            "Google Drive", "Dropbox", "OneDrive", "Mega", "MediaFire",
            "Dailymotion", "Vimeo", "SoundCloud", "Spotify", "Pinterest",
        ]
        # We'll keep a session dict in memory to map fs_id -> download_urls for quick access
        self.fs_id_to_download_urls = {}
        # For generic/video links from VKR, can use message_id or similar to keep state if needed



    def get_extension_from_url(self, url):
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1]
        return ext if ext else None





    def is_video_url(self, url):
        extension = self.get_extension_from_url(url)
        return extension in self.SUPPORTED_VIDEO_EXTENSIONS

    def is_video_file(self, filename: str) -> bool:
        if not filename:
            return False
        file_extension = filename.split('.')[-1].lower() if '.' in filename else ''
        return f'.{file_extension}' in self.SUPPORTED_VIDEO_EXTENSIONS

    def format_file_size(self, size: int) -> str:
        suffixes = ["B", "KB", "MB", "GB", "TB"]
        suffix_index = 0
        size_float = float(size)
        while size_float >= 1024 and suffix_index < len(suffixes) - 1:
            size_float /= 1024
            suffix_index += 1
        return f"{size_float:.1f} {suffixes[suffix_index]}"

    # =================== COMMAND HANDLERS ===================
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_message = """
🚀 **Welcome to Angry Downloader Bot!**
I can help you download files from various platforms including:
• TeraBox (supports folder links too! 📁)
• YouTube, Facebook, Instagram, TikTok
• Google Drive, Dropbox, OneDrive
• And 1000+ more sites!
**Features:**
✅ Multiple download links for each file
✅ Support for folders and individual files
✅ Fast and reliable downloads
**Commands:**
/start - Show this welcome message
**How to use:**
Just send me any supported link and I'll provide download links for you!
        """
        keyboard = [
            [InlineKeyboardButton("📋 Supported Sites", callback_data="show_sites")],
            [InlineKeyboardButton("💬 Support Group", url="https://t.me/+7AV6zd_uvHhmYmVl")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            welcome_message, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
📖 **How to use Angry Downloader Bot:**
**For TeraBox:**
• Send TeraBox link (supports both files and folders)
• I'll extract all downloadable content
• Get multiple download links for maximum compatibility
**For Other Sites:**
• Send any supported link
• I'll fetch available download options
• Multiple download links provided for reliability
**Tips:**
• Make sure links are publicly accessible
• Some sites may have region restrictions
• Use VPN if downloads are blocked in your area
• Try different download links if one doesn't work
**Need more help?** Join our support group!
        """
        keyboard = [
            [InlineKeyboardButton("📋 Supported Sites", callback_data="show_sites")],
            [InlineKeyboardButton("💬 Support Group", url="https://t.me/+7AV6zd_uvHhmYmVl")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def sites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.show_supported_sites(update, context)

    async def show_supported_sites(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        sites_text = "🌐 **Supported Sites (1000+):**\n\n"
        for i, site in enumerate(self.supported_sites[:50]):
            sites_text += f"• {site}\n"
            if (i + 1) % 10 == 0:
                sites_text += "\n"
        sites_text += "\n*And many more...*\n"
        sites_text += "\nJust send me any link from these platforms!"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            await update.callback_query.edit_message_text(
                sites_text, 
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                sites_text, 
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
       
       
       
            
            






    
    async def download_and_send_video(self, message, context, video_url):
        try:
            file_ext = self.get_extension_from_url(video_url)
            file_name = "video"
    
            # 1. Send a progress message
            progress_msg = await message.reply_text("⬇️ Downloading... 0%")
    
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as resp:
                    if resp.status == 200:
                        total_size = int(resp.headers.get("Content-Length", 0))
                        if total_size and total_size > self.MAX_FILE_SIZE:
                            await progress_msg.edit_text(
                                f"😊 Sorry, this feature is only available for files < 100 MB.\n"
                                f"Detected file size: {self.format_file_size(total_size)}\n\n"
                                "Please use the direct download links instead!"
                            )
                            return
    
                        # Extension guessing as before
                        if not file_ext:
                            content_type = resp.headers.get("Content-Type", "")
                            ext_from_type = mimetypes.guess_extension(content_type.split(";")[0].strip())
                            file_ext = ext_from_type if ext_from_type else ".mp4"
    
                        disp = resp.headers.get("Content-Disposition", "")
                        if "filename=" in disp:
                            file_name = disp.split("filename=")[1].split(";")[0].strip('"\' ')
                        else:
                            file_name = f"video{file_ext}"
    
                        # Download in chunks and update progress
                        chunk_size = 1024 * 1024  # 1 MB
                        downloaded = 0
                        last_percent = 0
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                            async for chunk in resp.content.iter_chunked(chunk_size):
                                if not chunk:
                                    break
                                tmp_file.write(chunk)
                                downloaded += len(chunk)
                                if total_size:
                                    percent = int(downloaded * 100 / total_size)
                                    # Update progress message every 10%
                                    if percent // 10 > last_percent // 10:
                                        await progress_msg.edit_text(f"⬇️ Downloading... {percent}%")
                                        last_percent = percent
                            tmp_file_path = tmp_file.name
                    else:
                        await progress_msg.edit_text(
                            "😊 Failed to download the video.\n\n"
                            "👉 For large videos or better support, try our Android app!\n"
                            "[📲 Download Android App](https://play.google.com/store/apps/details?id=com.chandu.angry_downloader)",
                            parse_mode='Markdown'
                        )

                        return
    
            await progress_msg.edit_text("✅ Download complete! Sending...")
    
            # Send as video if extension is a known video, else as document
            if file_ext.lower() in [".mp4", ".mkv", ".webm"]:
                with open(tmp_file_path, "rb") as video_file:
                    await message.reply_video(video_file, filename=file_name, supports_streaming=True)
            else:
                with open(tmp_file_path, "rb") as video_file:
                    await message.reply_document(video_file, filename=file_name)
            os.remove(tmp_file_path)
            await progress_msg.delete()
    
        except Exception as e:
            logger.error(f"Error downloading/sending video: {e}")
            try:
                await progress_msg.edit_text("😊 Error sending video file.")
            except:
                await message.reply_text("😊 Error sending video file.")
    
    



    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        try:
            if query.data == "show_sites":
                await self.show_supported_sites(update, context)
            elif query.data == "help":
                await self.help_command(update, context)
            elif query.data == "back_to_main":
                await self.start_command(update, context)
            elif query.data.startswith("get_video|"):
                await self.handle_get_video_callback(update, context, query)
        except Exception as e:
            logger.error(f"Callback error: {e}")
            await query.message.reply_text("😊 Something went wrong. Please try again.")



    async def handle_get_video_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query):
        try:
            _, unique_id = query.data.split("|", 1)
            params = self.video_callback_params.get(unique_id)
            if not params:
                await query.message.reply_text("😊 Sorry, this button is expired. Please refresh links.")
                return

            logger.info(f"[DEBUG] Params from callback: {params}")

            # Regenerate fresh download links
            download_urls = await self.fetch_terabox_download_urls(
                mode=params.get("mode", 1),
                uk=params.get("uk", ""),
                shareid=params.get("shareid", ""),
                timestamp=params.get("timestamp", 0),
                sign=params.get("sign", ""),
                js_token=params.get("js_token", ""),
                cookie=params.get("cookie", ""),
                fs_id=params.get("fs_id", "")
            )

            logger.info(f"[DEBUG] Re-fetched download_urls: {download_urls}")

            if not download_urls or not any(download_urls):
                await query.message.reply_text("😊 Download link not found or expired.")
                return

            video_url = next((url for url in download_urls if url), None)
            if not video_url:
                await query.message.reply_text("😊 No valid video download link found.")
                return

            await self.download_and_send_video(query.message, context, video_url)

        except Exception as e:
            logger.error(f"Error in handle_get_video_callback: {e}")
            await query.message.reply_text("😊 Internal error, please try again later.")





    # =================== MESSAGE HANDLER ===================
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_text = update.message.text
        if not message_text:
            return
        if not any(keyword in message_text.lower() for keyword in ['http://', 'https://', 'www.']):
            await update.message.reply_text("Please send a valid link to download from!")
            return
        
        user = update.message.from_user
        user_id = user.id
        username = user.username or f"{user.first_name or ''} {user.last_name or ''}".strip()
        await self.save_user_link(user_id, username, message_text.strip())
        
        
        
        processing_msg = await update.message.reply_text("🔄 Processing your link... Please wait!")
        try:
            if 'terabox' in message_text.lower() or '1024terabox' in message_text.lower():
                await self.process_terabox_link(update, context, message_text, processing_msg)
            else:
                await self.process_general_link(update, context, message_text, processing_msg)
        except Exception as e:
            logger.error(f"Error processing link: {e}")
            await processing_msg.edit_text(
                "😊 Sorry, something went wrong while processing your link. Please try again later."
            )

    # =================== TeraBox LINK HANDLING ===================
    async def process_terabox_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, processing_msg):
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"url": url, "mode": 2}
                async with session.post(self.terabox_api_url, 
                                       json=payload,
                                       headers={"Content-Type": "application/json"}) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'success' and data.get('list'):
                            await self.generate_all_download_links(data)
                            await processing_msg.delete()
                            await self.send_terabox_results(update, context, data)
                        else:
                            await processing_msg.edit_text(
                                "😊 Failed to process TeraBox link. Please check the link and try again."
                            )
                    else:
                        await processing_msg.edit_text(
                            "😊 Error connecting . Please try again later."
                        )
        except Exception as e:
            logger.error(f"TeraBox processing error: {e}")
            await processing_msg.edit_text(
                "😊 Something went wrong processing the TeraBox link."
            )

    async def generate_all_download_links(self, data: Dict):
        items = data.get('list', [])
        for item in items:
            if item.get('is_dir') != '1':
                fs_id = item.get('fs_id', '')
                if fs_id:
                    download_urls = await self.fetch_terabox_download_urls(
                        mode=data.get('mode', 1),
                        uk=str(data.get('uk', '')),
                        shareid=str(data.get('shareid', '')),
                        timestamp=data.get('timestamp', 0),
                        sign=str(data.get('sign', '')),
                        js_token=str(data.get('js_token', '')),
                        cookie=str(data.get('cookie', '')),
                        fs_id=fs_id
                    )
                    item['download_urls'] = download_urls
                    # Store the parameters so you can retrieve later
                    item['mode'] = data.get('mode', 1)
                    item['uk'] = str(data.get('uk', ''))
                    item['shareid'] = str(data.get('shareid', ''))
                    item['timestamp'] = data.get('timestamp', 0)
                    item['sign'] = str(data.get('sign', ''))
                    item['js_token'] = str(data.get('js_token', ''))
                    item['cookie'] = str(data.get('cookie', ''))
                    # Save mapping for the "🎥 Get Video" callback
                    self.fs_id_to_download_urls[fs_id] = download_urls
            elif item.get('list'):
                folder_data = {**data, 'list': item['list']}
                await self.generate_all_download_links(folder_data)


    async def fetch_terabox_download_urls(self, mode: int, uk: str, shareid: str, 
                                          timestamp: int, sign: str, js_token: str, 
                                          cookie: str, fs_id: str) -> List[str]:
        try:
            payload = {
                'mode': mode,
                'uk': uk,
                'shareid': shareid,
                'timestamp': timestamp,
                'sign': sign,
                'js_token': js_token,
                'cookie': cookie,
                'fs_id': fs_id
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(self.terabox_link_api_url, 
                                       json=payload,
                                       headers={'Content-Type': 'application/json'}) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'success' and data.get('download_link'):
                            download_links = data['download_link']
                            return [
                                download_links.get('url_1', ''),
                                download_links.get('url_2', ''),
                                download_links.get('url_3', '')
                            ]
        except Exception as e:
            logger.error(f"Error fetching download URLs: {e}")
        return []




    

    # async def send_terabox_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: Dict):
    #     items = data.get('list', [])
    #     for item in items:
    #         is_dir = item.get('is_dir') == '1'
    #         if is_dir:
    #             if item.get('list'):
    #                 folder_items = await self.process_items_without_download_links(item['list'])
    #                 for folder_item in folder_items:
    #                     await self.send_terabox_item(update, context, folder_item)
    #         else:
    #             await self.send_terabox_item(update, context, item)


    async def send_terabox_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: Dict):
        items = data.get('list', [])
        for item in items:
            is_dir = item.get('is_dir') == '1'
            # If it's a folder, just show "Coming soon"
            if is_dir:
                await self.send_terabox_item(update, context, item)
            else:
                await self.send_terabox_item(update, context, item)





    
    async def process_items_without_download_links(self, items: List[Dict]) -> List[Dict]:
        processed_items = []
        for item in items:
            if item.get('is_dir') == '1' and item.get('list'):
                sub_items = await self.process_items_without_download_links(item['list'])
                processed_items.extend(sub_items)
            else:
                processed_items.append(item)
        return processed_items




    
    async def send_terabox_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item: Dict):
        name = item.get('name', 'Unknown')
        is_dir = item.get('is_dir') == '1'   # <---- Check if it's a folder
    
        if is_dir:
            # Tell user to use the app for folders, and add a button
            message_text = (
                "📁 *Folder support is not available in the Telegram bot yet.*\n"
                "👉 _You can use our Android app to download entire folders easily!_\n"
            )
            keyboard = [
                [InlineKeyboardButton("📲 Try in our App", url="https://play.google.com/store/apps/details?id=com.chandu.angry_downloader")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_chat.send_message(
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return


    
        # The rest of your code for single files (NO CHANGE)
        size = int(item.get('size', 0))
        size_formatted = self.format_file_size(size)
        is_video = self.is_video_file(name)
        file_type = "🎬" if is_video else "📄"
        message_text = f"{file_type} **{name}**\n"
        if size_formatted != "0 B":
            message_text += f"📊 Size: {size_formatted}\n\n"
        else:
            message_text += "\n"
        message_text += "📥 **Download Options:**"
        keyboard = []
        download_urls = item.get('download_urls', ['', '', ''])
        fs_id = str(item.get('fs_id', ''))
        params = {
            "mode": item.get("mode"),
            "uk": item.get("uk"),
            "shareid": item.get("shareid"),
            "timestamp": item.get("timestamp"),
            "sign": item.get("sign"),
            "js_token": item.get("js_token"),
            "cookie": item.get("cookie"),
            "fs_id": fs_id,
        }
        unique_id = str(uuid.uuid4())[:8]
        self.video_callback_params[unique_id] = params
        callback_data = f"get_video|{unique_id}"
    
        if fs_id:
            self.fs_id_to_download_urls[fs_id] = download_urls
    
        if download_urls[0]:
            keyboard.append([InlineKeyboardButton("🔗 Download Link 1", url=download_urls[0])])
        if download_urls[1]:
            keyboard.append([InlineKeyboardButton("⚡ Download Link 2", url=download_urls[1])])
        if download_urls[2]:
            keyboard.append([InlineKeyboardButton("🔄 Download Link 3", url=download_urls[2])])
    
        if is_video:
            keyboard.append([
                InlineKeyboardButton("🎥 Get Video", callback_data=callback_data)
            ])

        if not any(download_urls):
            message_text += (
                "\n😊 No download links available for this file.\n"
                "Sometimes, our bot can’t fetch links due to site restrictions.\n\n"
                "👉 *Try in our Android app for more features!*"
            )
            keyboard = [
                [InlineKeyboardButton("📲 Try in our App", url="https://play.google.com/store/apps/details?id=com.chandu.angry_downloader")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.effective_chat.send_message(
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        if item.get('image'):
            try:
                await update.effective_chat.send_photo(
                    photo=item['image'],
                    caption=message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except:
                await update.effective_chat.send_message(
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        else:
            await update.effective_chat.send_message(
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            
            
            
            
            
            

    # =================== VKR LINK HANDLING (Not wired to Get Video) ===================
    async def process_general_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, processing_msg):
        try:
            async with aiohttp.ClientSession() as session:
                api_url = f"{self.vkr_api_url}?api_key={self.vkr_api_key}&vkr={url}"
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('data'):
                            await processing_msg.delete()
                            await self.send_vkr_results(update, context, data['data'])
                        else:
                            await processing_msg.edit_text(
                                "😊 No downloadable content found for this link."
                            )
                    else:
                        await processing_msg.edit_text(
                            "😊 Error processing link. Please try again later."
                        )
        except Exception as e:
            logger.error(f"VKR processing error: {e}")
            await processing_msg.edit_text(
                "😊 Connection issue. Please try later 😊"
            )

    async def send_vkr_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: Dict):
        title = data.get('title', 'Unknown Title')
        description = data.get('description', 'No description available')
        thumbnails = data.get('thumbnail', [])
        downloads = data.get('downloads', [])
        message_text = f"🎬 **{title}**\n\n"
        if description and description != 'No description available':
            if len(description) > 200:
                message_text += f"📝 {description[:200]}...\n\n"
            else:
                message_text += f"📝 {description}\n\n"
        message_text += "📥 **Available Downloads:**"
        keyboard = []
        for i, download in enumerate(downloads[:8]):  # Show up to 8 options
            format_info = download.get('ext', 'unknown').upper()
            size_info = download.get('size', 'Unknown Size')
            download_url = download.get('url', '')
            if download_url:
                button_text = f"🔗 {format_info}"
                if size_info != 'Unknown Size':
                    button_text += f" ({size_info})"
                keyboard.append([InlineKeyboardButton(button_text, url=download_url)])
        # Optionally, for non-TeraBox you can also add a Get Video button with callback data
        # but you'd have to manage state differently (e.g. by message_id)
        # If no download links available
        if not keyboard:
            message_text += "\n😊 No download links available for this content."
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        if thumbnails and isinstance(thumbnails, list) and len(thumbnails) > 0:
            thumbnail_url = thumbnails[0].get('url') if isinstance(thumbnails[0], dict) else thumbnails[0]
            try:
                await update.effective_chat.send_photo(
                    photo=thumbnail_url,
                    caption=message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except:
                await update.effective_chat.send_message(
                    text=message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        else:
            await update.effective_chat.send_message(
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    # =================== MAIN ===================
    def run(self):
        application = Application.builder().token(self.bot_token).build()
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("sites", self.sites_command))
        application.add_handler(CommandHandler("history", self.history_command))   # <--- ADD THIS LINE
        application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        print("🚀 Angry Downloader Bot is starting...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    BOT_TOKEN = "8070311190:AAEeOBY31OB8DKacEvWDJg0QJeg7UV4bkBI"
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("😊 Please set your bot token in the BOT_TOKEN variable!")
        print("Get your token from @BotFather on Telegram")
        return
    bot = TelegramDownloaderBot(BOT_TOKEN)
    bot.run()

if __name__ == "__main__":
    main()

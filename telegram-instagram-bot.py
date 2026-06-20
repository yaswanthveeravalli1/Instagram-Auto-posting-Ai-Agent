#!/usr/bin/env python3
"""
Standalone Telegram Bot for Instagram Carousel Posting
This script runs locally and listens for Telegram messages containing CDN image links.
When it receives 1-4 image URLs, it posts them as an Instagram carousel
using the Instagram Graph API directly.
"""

import os
import re
import sys
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import httpx
from dotenv import load_dotenv

# Fix Windows console encoding for emoji output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from telegram.constants import ChatAction
from telegram.error import NetworkError, TimedOut

# Configure logging to reduce noise
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

# Instagram Graph API Configuration
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
GRAPH_API_BASE = "https://graph.instagram.com/v25.0"

# URL pattern to match CDN links
URL_PATTERN = r'https?://[^\s]+'


async def extract_urls(text: str) -> list:
    """Extract all URLs from text."""
    urls = re.findall(URL_PATTERN, text)
    return urls[:10]  # Maximum 10 images for carousel


def create_child_container(image_url: str) -> str:
    """
    Create a child media container for a single image (carousel item).

    Args:
        image_url: Publicly accessible URL of the image

    Returns:
        Container ID string

    Raises:
        Exception if the API call fails
    """
    url = f"{GRAPH_API_BASE}/{INSTAGRAM_USER_ID}/media"
    payload = {
        "image_url": image_url,
        "is_carousel_item": "true",
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }
    response = requests.post(url, data=payload, timeout=30)
    data = response.json()

    if "id" in data:
        return data["id"]
    else:
        error_msg = data.get("error", {}).get("message", str(data))
        raise Exception(f"Failed to create child container: {error_msg}")


def create_carousel_container(child_ids: list, caption: str = "") -> str:
    """
    Create a parent carousel container from child container IDs.

    Args:
        child_ids: List of child container ID strings
        caption: Caption for the Instagram post

    Returns:
        Carousel container ID string

    Raises:
        Exception if the API call fails
    """
    url = f"{GRAPH_API_BASE}/{INSTAGRAM_USER_ID}/media"
    payload = {
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
        "caption": caption or "Posted via Instagram Carousel Bot 📸",
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }
    response = requests.post(url, data=payload, timeout=30)
    data = response.json()

    if "id" in data:
        return data["id"]
    else:
        error_msg = data.get("error", {}).get("message", str(data))
        raise Exception(f"Failed to create carousel container: {error_msg}")


def publish_media(creation_id: str) -> str:
    """
    Publish a media container to Instagram.

    Args:
        creation_id: The container ID to publish

    Returns:
        Published media ID string

    Raises:
        Exception if the API call fails
    """
    url = f"{GRAPH_API_BASE}/{INSTAGRAM_USER_ID}/media_publish"
    payload = {
        "creation_id": creation_id,
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }
    response = requests.post(url, data=payload, timeout=60)
    data = response.json()

    if "id" in data:
        return data["id"]
    else:
        error_msg = data.get("error", {}).get("message", str(data))
        raise Exception(f"Failed to publish media: {error_msg}")


def get_permalink(media_id: str) -> str:
    """
    Get the permalink for a published Instagram post.

    Args:
        media_id: The published media ID

    Returns:
        Permalink URL string, or empty string if unavailable
    """
    url = f"{GRAPH_API_BASE}/{media_id}"
    params = {
        "fields": "permalink",
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        return data.get("permalink", "")
    except Exception:
        return ""


async def post_to_instagram(image_urls: list, caption: str = "") -> dict:
    """
    Post images to Instagram as a carousel using the Graph API.

    Flow:
    1. Create child containers for each image
    2. Create a parent carousel container
    3. Publish the carousel
    4. Retrieve the permalink

    Args:
        image_urls: List of CDN image URLs (1-4 items)
        caption: Optional caption for the post

    Returns:
        Dictionary with 'success', 'permalink', and 'error' keys
    """
    if not INSTAGRAM_USER_ID or not INSTAGRAM_ACCESS_TOKEN:
        return {
            "success": False,
            "error": "Instagram credentials not configured. "
                     "Please set INSTAGRAM_USER_ID and INSTAGRAM_ACCESS_TOKEN in .env file."
        }

    if not image_urls or len(image_urls) == 0:
        return {
            "success": False,
            "error": "No valid image URLs provided"
        }

    if len(image_urls) > 10:
        image_urls = image_urls[:10]

    try:
        # Step 1: Create child containers for each image
        print(f"  📦 Creating {len(image_urls)} child container(s)...")
        child_ids = []
        for i, img_url in enumerate(image_urls):
            print(f"    → Image {i+1}: {img_url[:60]}...")
            child_id = create_child_container(img_url)
            child_ids.append(child_id)
            print(f"    ✓ Container ID: {child_id}")

        # Step 2: Brief pause to let containers process
        time.sleep(2)

        # Step 3: Create the carousel container
        print(f"  📸 Creating carousel container with {len(child_ids)} items...")
        if len(child_ids) == 1:
            # Single image — publish directly (no carousel needed)
            carousel_id = child_ids[0]
            # For single image, we need to re-create without is_carousel_item
            url = f"{GRAPH_API_BASE}/{INSTAGRAM_USER_ID}/media"
            payload = {
                "image_url": image_urls[0],
                "caption": caption or "Posted via Instagram Carousel Bot 📸",
                "access_token": INSTAGRAM_ACCESS_TOKEN,
            }
            response = requests.post(url, data=payload, timeout=30)
            data = response.json()
            if "id" not in data:
                error_msg = data.get("error", {}).get("message", str(data))
                raise Exception(f"Failed to create single image container: {error_msg}")
            carousel_id = data["id"]
        else:
            carousel_id = create_carousel_container(child_ids, caption)
        print(f"  ✓ Carousel container ID: {carousel_id}")

        # Step 4: Brief pause before publishing
        time.sleep(2)

        # Step 5: Publish the carousel
        print(f"  🚀 Publishing to Instagram...")
        media_id = publish_media(carousel_id)
        print(f"  ✓ Published! Media ID: {media_id}")

        # Step 6: Get the permalink
        permalink = get_permalink(media_id)
        if permalink:
            print(f"  🔗 Permalink: {permalink}")

        return {
            "success": True,
            "permalink": permalink,
            "message": "✅ Carousel posted successfully!"
        }

    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return {
            "success": False,
            "error": f"Instagram posting failed: {str(e)}"
        }


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming Telegram messages."""

    if not update.message or not update.message.text:
        return

    user_id = update.message.from_user.id
    message_text = update.message.text

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # Extract URLs from message
    image_urls = await extract_urls(message_text)

    if not image_urls:
        await update.message.reply_text(
            "❌ No image URLs found in your message.\n\n"
            "Please send a message with 1-10 CDN image links, for example:\n"
            "https://example.com/image1.jpg\n"
            "https://example.com/image2.jpg"
        )
        return

    # Validate URLs are accessible
    valid_urls = []
    for url in image_urls:
        # Basic URL validation
        if url.startswith(('http://', 'https://')) and ('.' in url):
            valid_urls.append(url)

    if not valid_urls:
        await update.message.reply_text(
            "❌ Invalid image URLs detected.\n"
            "Please provide valid CDN links (starting with http:// or https://)"
        )
        return

    # Post to Instagram
    await update.message.reply_text(
        f"🚀 Posting {len(valid_urls)} image(s) to Instagram as a carousel...\n"
        "Please wait..."
    )

    print(f"\n📨 Received {len(valid_urls)} image URL(s) from user {user_id}")
    result = await post_to_instagram(valid_urls)

    if result["success"]:
        response = result.get("message", "✅ Carousel posted successfully!")
        if result.get("permalink"):
            response += f"\n\n📱 View on Instagram:\n{result['permalink']}"
        await update.message.reply_text(response)
    else:
        error_msg = result.get("error", "Unknown error occurred")
        await update.message.reply_text(
            f"❌ Failed to post carousel:\n{error_msg}\n\n"
            "Please check your image URLs and try again."
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "👋 Welcome to Instagram Carousel Bot!\n\n"
        "📸 How to use:\n"
        "1. Send me 1-10 CDN image links in a single message\n"
        "2. I'll post them as an Instagram carousel\n"
        "3. You'll receive the Instagram post link\n\n"
        "Example:\n"
        "https://res.cloudinary.com/example/image1.jpg\n"
        "https://res.cloudinary.com/example/image2.jpg\n"
        "https://res.cloudinary.com/example/image3.jpg\n"
        "https://res.cloudinary.com/example/image4.jpg\n\n"
        "✨ That's it! The carousel will be posted instantly."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(
        "📖 Help & Information\n\n"
        "Commands:\n"
        "/start - Show welcome message\n"
        "/help - Show this help message\n\n"
        "Features:\n"
        "✅ Post up to 10 images as Instagram carousel\n"
        "✅ Instant posting via Instagram Graph API\n"
        "✅ Automatic error handling\n"
        "✅ Instant confirmation with post link\n\n"
        "Supported image formats:\n"
        "• JPG, JPEG, PNG, GIF, WEBP\n"
        "• File size: up to 8 MB per image\n\n"
        "Need help? Send /start to see examples."
    )


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple health check handler for Render.com port binding."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self, format, *args):
        pass  # Suppress noisy HTTP logs


def start_health_server():
    """Start a background HTTP server for Render.com health checks."""
    port = int(os.getenv("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"🌐 Health check server running on port {port}")
    server.serve_forever()


def main():
    """Start the bot."""
    # Start health check server in background thread (for Render.com)
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()

    print("🤖 Starting Instagram Carousel Telegram Bot...")
    print(f"Bot Token: {TELEGRAM_BOT_TOKEN[:20]}...")
    print(f"Chat ID: {TELEGRAM_CHAT_ID}")

    # Validate Instagram credentials
    if not INSTAGRAM_USER_ID or INSTAGRAM_USER_ID == "your_ig_user_id_here":
        print("⚠️  WARNING: INSTAGRAM_USER_ID not set in .env file!")
        print("   The bot will start but Instagram posting will fail.")
    if not INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_ACCESS_TOKEN == "your_access_token_here":
        print("⚠️  WARNING: INSTAGRAM_ACCESS_TOKEN not set in .env file!")
        print("   The bot will start but Instagram posting will fail.")

    if INSTAGRAM_USER_ID and INSTAGRAM_USER_ID != "your_ig_user_id_here":
        print(f"Instagram User ID: {INSTAGRAM_USER_ID}")
        print(f"Instagram Token: {INSTAGRAM_ACCESS_TOKEN[:20]}...")

    # Force IPv4 to avoid "All connection attempts failed" on networks
    # where IPv6 DNS resolution succeeds but IPv6 connectivity is broken.
    # local_address="0.0.0.0" binds to IPv4 only.
    custom_request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
        httpx_kwargs={"transport": httpx.AsyncHTTPTransport(
            retries=3,
            local_address="0.0.0.0",
        )},
    )

    polling_request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=60.0,
        write_timeout=30.0,
        pool_timeout=30.0,
        httpx_kwargs={"transport": httpx.AsyncHTTPTransport(
            retries=3,
            local_address="0.0.0.0",
        )},
    )

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(custom_request)
        .get_updates_request(polling_request)
        .build()
    )

    # Add error handler to gracefully handle network issues
    async def error_handler(update, context):
        """Handle errors without crashing the bot."""
        if isinstance(context.error, (NetworkError, TimedOut)):
            print(f"⚠️  Network error (will retry automatically): {context.error}")
        else:
            print(f"❌ Unhandled error: {context.error}")
            logger.error("Exception:", exc_info=context.error)

    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    # Start polling with retries for bootstrap
    print("\n✅ Bot is running and listening for messages...")
    print("Press Ctrl+C to stop.\n")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        bootstrap_retries=5,
    )


if __name__ == "__main__":
    main()

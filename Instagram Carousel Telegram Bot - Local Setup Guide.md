# Instagram Carousel Telegram Bot - Local Setup Guide

This is a standalone Telegram bot that you can run on your local machine to post Instagram carousels directly from Telegram messages.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Access to Telegram bot token: `8980560338:AAH-jL3O25LwINPvYaBcFaCc2m-fA38HHcM`
- Manus CLI installed (for Instagram posting)

## Installation Steps

### 1. Install Python Dependencies

```bash
pip install python-telegram-bot
```

### 2. Download the Bot Script

The bot script is located at: `/home/ubuntu/telegram-instagram-bot.py`

### 3. Run the Bot

```bash
python3 /home/ubuntu/telegram-instagram-bot.py
```

You should see:
```
🤖 Starting Instagram Carousel Telegram Bot...
Bot Token: 8980560338:AAH-jL3O25LwINPvYaBcFaCc2m-fA38HHcM...
Chat ID: 1429186093
✅ Bot is running and listening for messages...
Press Ctrl+C to stop.
```

## How to Use

### Send Images to the Bot

1. Open Telegram and search for: **@yaswanth_carousel_bot**
2. Send a message with 1-4 CDN image links, for example:

```
https://res.cloudinary.com/dvtrsojsa/image/upload/v1781189386/kylafkywt4owbbc68o94.jpg
https://res.cloudinary.com/dvtrsojsa/image/upload/v1781187234/kespvshrgpuhbv9ubgnp.jpg
https://res.cloudinary.com/dvtrsojsa/image/upload/v1781189386/kylafkywt4owbbc68o94.jpg
https://res.cloudinary.com/dvtrsojsa/image/upload/v1781187234/kespvshrgpuhbv9ubgnp.jpg
```

3. The bot will:
   - ✅ Extract the image URLs
   - ✅ Validate them
   - ✅ Post them as an Instagram carousel
   - ✅ Send you the Instagram post link

### Example Response

```
🚀 Posting 4 image(s) to Instagram as a carousel...
Please wait...

✅ Carousel posted successfully!

📱 View on Instagram:
https://www.instagram.com/p/DZmp3sgESbs/
```

## Supported Image Formats

- JPG, JPEG, PNG, GIF, WEBP
- File size: up to 8 MB per image
- Maximum 4 images per carousel

## Bot Commands

- `/start` - Show welcome message with usage examples
- `/help` - Show help and information
- Send image URLs - Post carousel to Instagram

## Troubleshooting

### Bot doesn't respond
1. Make sure the bot script is running: `python3 /home/ubuntu/telegram-instagram-bot.py`
2. Check that your Telegram bot token is correct
3. Verify you're sending messages to the correct bot: **@yaswanth_carousel_bot**

### Images not posting to Instagram
1. Verify the image URLs are valid and accessible
2. Check that Manus CLI is installed: `which manus-mcp-cli`
3. Ensure you have Instagram credentials configured
4. Check the bot console for error messages

### "No valid image URLs found"
- Make sure URLs start with `http://` or `https://`
- URLs must be on separate lines or separated by spaces
- Maximum 4 URLs per message

## Running as a Background Service (Optional)

### Using nohup (Linux/Mac)
```bash
nohup python3 /home/ubuntu/telegram-instagram-bot.py > bot.log 2>&1 &
```

### Using screen (Linux/Mac)
```bash
screen -S instagram-bot
python3 /home/ubuntu/telegram-instagram-bot.py
# Press Ctrl+A then D to detach
```

### Using systemd (Linux)

Create `/etc/systemd/system/instagram-bot.service`:
```ini
[Unit]
Description=Instagram Carousel Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/usr/bin/python3 /home/ubuntu/telegram-instagram-bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then run:
```bash
sudo systemctl daemon-reload
sudo systemctl enable instagram-bot
sudo systemctl start instagram-bot
```

## Configuration

To modify the bot behavior, edit `/home/ubuntu/telegram-instagram-bot.py`:

- **TELEGRAM_BOT_TOKEN**: Your bot's token (line 12)
- **TELEGRAM_CHAT_ID**: Your chat ID (line 13)
- **URL_PATTERN**: Regex for URL matching (line 16)
- **Maximum images**: Change `[:4]` to a different number (line 21)

## Security Notes

- Keep your bot token private - never share it publicly
- The bot only responds to messages from your configured chat ID
- All image URLs must be publicly accessible
- Instagram credentials are handled securely through Manus CLI

## Support

If you encounter issues:
1. Check the console output for error messages
2. Verify all prerequisites are installed
3. Ensure your Telegram bot token is correct
4. Check that Manus CLI is properly configured

---

**Bot Status:** Ready to use locally ✅
**Last Updated:** June 15, 2026

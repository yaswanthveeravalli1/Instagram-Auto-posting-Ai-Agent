/**
 * Instagram Carousel Telegram Bot — Google Apps Script version
 * =============================================================
 *
 * SETUP INSTRUCTIONS:
 *
 * 1. Go to https://script.google.com → New project.
 *    Replace the default Code.gs contents with this file.
 *
 * 2. Set up Script Properties (Project Settings ⚙️ → Script Properties → Add):
 *      TELEGRAM_BOT_TOKEN       = your Telegram bot token
 *      INSTAGRAM_USER_ID        = your Instagram business account ID
 *      INSTAGRAM_ACCESS_TOKEN   = your Instagram Graph API access token
 *
 *    (Do NOT hardcode these in the script — Script Properties keeps them
 *    out of the source code.)
 *
 * 3. Deploy → New deployment → type: "Web app"
 *      - Execute as: Me
 *      - Who has access: Anyone
 *    Click Deploy, authorize the script, and copy the Web App URL.
 *
 * 4. Run the setWebhook() function once (select it in the dropdown next to
 *    "Run" and click Run). This tells Telegram to send updates to your
 *    Web App URL. Check the execution log to confirm it returned "ok": true.
 *
 * 5. Message your bot on Telegram — it should reply.
 *
 * NOTE: Apps Script can't run an infinite polling loop like
 * app.run_polling() did. This version uses Telegram webhooks instead —
 * Telegram pushes each message to doPost(), which runs briefly and exits.
 */

const GRAPH_API_BASE = "https://graph.instagram.com/v25.0";
const TELEGRAM_API_BASE = "https://api.telegram.org/bot";

const START_MESSAGE =
  "👋 Welcome to Instagram Carousel Bot!\n\n" +
  "📸 How to use:\n" +
  "1. Send me 1-4 CDN image links in a single message\n" +
  "2. I'll post them as an Instagram carousel\n" +
  "3. You'll receive the Instagram post link\n\n" +
  "Example:\n" +
  "https://res.cloudinary.com/example/image1.jpg\n" +
  "https://res.cloudinary.com/example/image2.jpg\n" +
  "https://res.cloudinary.com/example/image3.jpg\n" +
  "https://res.cloudinary.com/example/image4.jpg\n\n" +
  "✨ That's it! The carousel will be posted instantly.";

const HELP_MESSAGE =
  "📖 Help & Information\n\n" +
  "Commands:\n" +
  "/start - Show welcome message\n" +
  "/help - Show this help message\n\n" +
  "Features:\n" +
  "✅ Post up to 4 images as Instagram carousel\n" +
  "✅ Instant posting via Instagram Graph API\n" +
  "✅ Automatic error handling\n" +
  "✅ Instant confirmation with post link\n\n" +
  "Supported image formats:\n" +
  "• JPG, JPEG, PNG, GIF, WEBP\n" +
  "• File size: up to 8 MB per image\n\n" +
  "Need help? Send /start to see examples.";

/**
 * Reads credentials from Script Properties.
 */
function getConfig_() {
  const props = PropertiesService.getScriptProperties();
  return {
    TELEGRAM_BOT_TOKEN: props.getProperty("TELEGRAM_BOT_TOKEN"),
    INSTAGRAM_USER_ID: props.getProperty("INSTAGRAM_USER_ID"),
    INSTAGRAM_ACCESS_TOKEN: props.getProperty("INSTAGRAM_ACCESS_TOKEN"),
  };
}

/**
 * Web app entry point — Telegram calls this for every update.
 */
function doPost(e) {
  try {
    const update = JSON.parse(e.postData.contents);
    handleUpdate_(update);
  } catch (err) {
    console.error("Error processing update: " + err);
  }
  // Telegram just needs a 200 OK; content doesn't matter.
  return ContentService
    .createTextOutput(JSON.stringify({ status: "ok" }))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Routes an incoming Telegram update to the right handler.
 */
function handleUpdate_(update) {
  if (!update.message || !update.message.text) return;

  const chatId = update.message.chat.id;
  const text = update.message.text;

  if (text === "/start") {
    sendTelegramMessage_(chatId, START_MESSAGE);
    return;
  }

  if (text === "/help") {
    sendTelegramMessage_(chatId, HELP_MESSAGE);
    return;
  }

  const imageUrls = extractUrls_(text);

  if (imageUrls.length === 0) {
    sendTelegramMessage_(
      chatId,
      "❌ No image URLs found in your message.\n\n" +
      "Please send a message with 1-4 CDN image links, for example:\n" +
      "https://example.com/image1.jpg\n" +
      "https://example.com/image2.jpg"
    );
    return;
  }

  sendTelegramMessage_(
    chatId,
    `🚀 Posting ${imageUrls.length} image(s) to Instagram as a carousel...\nPlease wait...`
  );

  const result = postToInstagram_(imageUrls);

  if (result.success) {
    let response = result.message || "✅ Carousel posted successfully!";
    if (result.permalink) {
      response += `\n\n📱 View on Instagram:\n${result.permalink}`;
    }
    sendTelegramMessage_(chatId, response);
  } else {
    sendTelegramMessage_(
      chatId,
      `❌ Failed to post carousel:\n${result.error}\n\nPlease check your image URLs and try again.`
    );
  }
}

/**
 * Extracts up to 4 URLs from a message's text.
 */
function extractUrls_(text) {
  const matches = text.match(/https?:\/\/[^\s]+/g) || [];
  return matches.slice(0, 4);
}

/**
 * Sends a plain text message back to a Telegram chat.
 */
function sendTelegramMessage_(chatId, text) {
  const config = getConfig_();
  const url = `${TELEGRAM_API_BASE}${config.TELEGRAM_BOT_TOKEN}/sendMessage`;
  UrlFetchApp.fetch(url, {
    method: "post",
    payload: {
      chat_id: String(chatId),
      text: text,
    },
    muteHttpExceptions: true,
  });
}

/**
 * Creates a child media container for one carousel image.
 */
function createChildContainer_(imageUrl, config) {
  const url = `${GRAPH_API_BASE}/${config.INSTAGRAM_USER_ID}/media`;
  const response = UrlFetchApp.fetch(url, {
    method: "post",
    payload: {
      image_url: imageUrl,
      is_carousel_item: "true",
      access_token: config.INSTAGRAM_ACCESS_TOKEN,
    },
    muteHttpExceptions: true,
  });
  const data = JSON.parse(response.getContentText());
  if (data.id) return data.id;
  const errorMsg = (data.error && data.error.message) || JSON.stringify(data);
  throw new Error(`Failed to create child container: ${errorMsg}`);
}

/**
 * Creates the parent carousel container from child container IDs.
 */
function createCarouselContainer_(childIds, caption, config) {
  const url = `${GRAPH_API_BASE}/${config.INSTAGRAM_USER_ID}/media`;
  const response = UrlFetchApp.fetch(url, {
    method: "post",
    payload: {
      media_type: "CAROUSEL",
      children: childIds.join(","),
      caption: caption || "Posted via Instagram Carousel Bot 📸",
      access_token: config.INSTAGRAM_ACCESS_TOKEN,
    },
    muteHttpExceptions: true,
  });
  const data = JSON.parse(response.getContentText());
  if (data.id) return data.id;
  const errorMsg = (data.error && data.error.message) || JSON.stringify(data);
  throw new Error(`Failed to create carousel container: ${errorMsg}`);
}

/**
 * Publishes a media container to Instagram.
 */
function publishMedia_(creationId, config) {
  const url = `${GRAPH_API_BASE}/${config.INSTAGRAM_USER_ID}/media_publish`;
  const response = UrlFetchApp.fetch(url, {
    method: "post",
    payload: {
      creation_id: creationId,
      access_token: config.INSTAGRAM_ACCESS_TOKEN,
    },
    muteHttpExceptions: true,
  });
  const data = JSON.parse(response.getContentText());
  if (data.id) return data.id;
  const errorMsg = (data.error && data.error.message) || JSON.stringify(data);
  throw new Error(`Failed to publish media: ${errorMsg}`);
}

/**
 * Gets the permalink for a published media item.
 */
function getPermalink_(mediaId, config) {
  const url = `${GRAPH_API_BASE}/${mediaId}?fields=permalink&access_token=${config.INSTAGRAM_ACCESS_TOKEN}`;
  try {
    const response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    const data = JSON.parse(response.getContentText());
    return data.permalink || "";
  } catch (err) {
    return "";
  }
}

/**
 * Posts 1-4 images to Instagram as a carousel (or single post if only 1).
 */
function postToInstagram_(imageUrls, caption) {
  const config = getConfig_();

  if (!config.INSTAGRAM_USER_ID || !config.INSTAGRAM_ACCESS_TOKEN) {
    return {
      success: false,
      error: "Instagram credentials not configured. Set INSTAGRAM_USER_ID and " +
             "INSTAGRAM_ACCESS_TOKEN in Script Properties.",
    };
  }

  if (!imageUrls || imageUrls.length === 0) {
    return { success: false, error: "No valid image URLs provided" };
  }

  if (imageUrls.length > 4) {
    imageUrls = imageUrls.slice(0, 4);
  }

  try {
    // Step 1: Create child containers for each image
    const childIds = [];
    for (const imgUrl of imageUrls) {
      childIds.push(createChildContainer_(imgUrl, config));
    }

    // Step 2: Brief pause to let containers process
    Utilities.sleep(2000);

    // Step 3: Create the carousel container (or single-image container)
    let carouselId;
    if (childIds.length === 1) {
      const url = `${GRAPH_API_BASE}/${config.INSTAGRAM_USER_ID}/media`;
      const response = UrlFetchApp.fetch(url, {
        method: "post",
        payload: {
          image_url: imageUrls[0],
          caption: caption || "Posted via Instagram Carousel Bot 📸",
          access_token: config.INSTAGRAM_ACCESS_TOKEN,
        },
        muteHttpExceptions: true,
      });
      const data = JSON.parse(response.getContentText());
      if (!data.id) {
        const errorMsg = (data.error && data.error.message) || JSON.stringify(data);
        throw new Error(`Failed to create single image container: ${errorMsg}`);
      }
      carouselId = data.id;
    } else {
      carouselId = createCarouselContainer_(childIds, caption, config);
    }

    // Step 4: Brief pause before publishing
    Utilities.sleep(2000);

    // Step 5: Publish
    const mediaId = publishMedia_(carouselId, config);

    // Step 6: Get permalink
    const permalink = getPermalink_(mediaId, config);

    return {
      success: true,
      permalink: permalink,
      message: "✅ Carousel posted successfully!",
    };
  } catch (err) {
    return { success: false, error: err.toString() };
  }
}

/**
 * Run this ONCE after deploying the Web App, to register the webhook
 * with Telegram. Re-run it if you redeploy and get a new URL.
 */
function setWebhook() {
  const config = getConfig_();
  const webAppUrl = ScriptApp.getService().getUrl();
  const url = `${TELEGRAM_API_BASE}${config.TELEGRAM_BOT_TOKEN}/setWebhook?url=${encodeURIComponent(webAppUrl)}`;
  const response = UrlFetchApp.fetch(url);
  console.log(response.getContentText());
}

/**
 * Optional: check current webhook status / undo it if needed.
 */
function getWebhookInfo() {
  const config = getConfig_();
  const url = `${TELEGRAM_API_BASE}${config.TELEGRAM_BOT_TOKEN}/getWebhookInfo`;
  console.log(UrlFetchApp.fetch(url).getContentText());
}

function deleteWebhook() {
  const config = getConfig_();
  const url = `${TELEGRAM_API_BASE}${config.TELEGRAM_BOT_TOKEN}/deleteWebhook`;
  console.log(UrlFetchApp.fetch(url).getContentText());
}

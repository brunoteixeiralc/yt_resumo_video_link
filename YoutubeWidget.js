// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: red; icon-glyph: play;

// Youtube Summarizer Widget & Reader
// v2.0 - WebView UI + Safe Mode

const SERVER_URL = "https://roseline-smelly-bloodlessly.ngrok-free.dev/summarize";

// --- MAIN LOGIC ---

// 1. Detect Input Source (Share Sheet vs Clipboard)
let inputUrl = null;

if (args.urls && args.urls.length > 0) {
    inputUrl = args.urls[0];
} else if (args.plainTexts && args.plainTexts.length > 0) {
    // YouTube often shares "Title https://youtu.be/..."
    const text = args.plainTexts[0];
    const match = text.match(/(https?:\/\/[^\s]+)/);
    if (match) inputUrl = match[0];
}

if (config.runsInWidget) {
    // Homescreen Widget: Passive Mode
    const widget = createDashboardWidget();
    Script.setWidget(widget);
} else {
    // Interactive Mode (App or Share Sheet)
    if (inputUrl) {
        // Came from Share Sheet -> Go straight to summary
        await showSummaryWebView(inputUrl);
    } else {
        // Opened App manually -> Check clipboard
        await handleAppInteraction();
    }
}

Script.complete();

// --- FUNCTIONS ---

function createDashboardWidget() {
    const w = new ListWidget();
    w.backgroundColor = new Color("#1c1c1e");

    // Header
    const title = w.addText("📺 YouTube Resumo");
    title.font = Font.boldSystemFont(14);
    title.textColor = new Color("#ff3b30");
    w.addSpacer(8);

    // Check Clipboard (May be restricted in Widget mode)
    // We try/catch just in case
    let url = "";
    try {
        url = Pasteboard.paste() || "";
    } catch (e) { }

    const isYoutube = url && (url.includes("youtube.com") || url.includes("youtu.be"));

    if (isYoutube) {
        const t1 = w.addText("🔗 Link detectado!");
        t1.font = Font.boldSystemFont(12);
        t1.textColor = Color.white();
        w.addSpacer(4);
        const t2 = w.addText(url.substring(0, 30) + "...");
        t2.font = Font.systemFont(10);
        t2.textColor = Color.gray();
        w.addSpacer(8);
        const btn = w.addText("Toque para resumir ▶️");
        btn.font = Font.mediumSystemFont(12);
        btn.textColor = new Color("#34c759");
    } else {
        const t = w.addText("Toque para abrir");
        t.font = Font.boldSystemFont(12);
        t.textColor = Color.white();
        w.addSpacer(4);
        const sub = w.addText("ou use o Compartilhar do YouTube");
        sub.font = Font.italicSystemFont(10);
        sub.textColor = Color.gray();
    }

    return w;
}

async function handleAppInteraction() {
    // 1. Get URL Input
    const alert = new Alert();
    alert.title = "Novo Resumo";
    alert.message = "Confirme ou edite o link do vídeo:";
    alert.addTextField(Pasteboard.paste() || "https://");
    alert.addAction("Gerar Resumo");
    alert.addCancelAction("Cancelar");

    const idx = await alert.present();
    if (idx === -1) return; // Cancelled

    const url = alert.textFieldValue(0);

    // 2. Loading UI (Quick Alert)
    // Scriptable doesn't have a persistent loading spinner, so we show a notification or just proceed.
    // We'll jump straight to the WebView with a "Loading" state.
    await showSummaryWebView(url);
}

async function showSummaryWebView(url) {
    // Encode the URL to prevent XSS via string interpolation into the HTML template
    const encodedUrl = encodeURIComponent(url);

    // Create HTML for the WebView
    // We inject a script to fetch the summary cleanly
    const html = `
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: -apple-system, sans-serif; padding: 20px; background: #f2f2f7; color: #000; }
            .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
            h1 { color: #ff3b30; font-size: 22px; margin-top: 0; }
            .loading { color: #666; text-align: center; margin-top: 50px; font-weight: 500; }
            #content { line-height: 1.6; font-size: 16px; }
            pre { background: #eee; padding: 10px; overflow-x: scroll; }
        </style>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js"></script>
    </head>
    <body>
        <div class="card">
            <div id="status" class="loading">🔄 Conectando ao servidor...</div>
            <div id="result" style="display:none;">
                <h1>📝 Resumo do Vídeo</h1>
                <div id="content"></div>
            </div>
        </div>

        <script>
            async function fetchSummary() {
                // Decode the URL that was safely encoded before injection into this template
                const videoUrl = decodeURIComponent("${encodedUrl}");
                try {
                    const response = await fetch("${SERVER_URL}", {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: videoUrl })
                    });

                    const data = await response.json();

                    if (data.error) {
                         document.getElementById('status').textContent = "❌ Erro: " + data.error;
                         document.getElementById('status').style.color = "red";
                    } else {
                        document.getElementById('status').style.display = 'none';
                        document.getElementById('result').style.display = 'block';
                        document.getElementById('content').innerHTML = DOMPurify.sanitize(marked.parse(data.summary));
                    }
                } catch (e) {
                    document.getElementById('status').innerHTML = "❌ Falha na conexão. <br><br>Verifique se o servidor Python e o Ngrok estão rodando.";
                    document.getElementById('status').style.color = "red";
                }
            }
            
            // Start immediately
            fetchSummary();
        </script>
    </body>
    </html>
    `;

    const webView = new WebView();
    await webView.loadHTML(html);
    await webView.present();
}

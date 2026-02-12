// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: red; icon-glyph: play;

// Youtube Summarizer Widget
// This script interacts with the local python server running on localhost:5000

const SERVER_URL = "http://localhost:5001/summarize";

async function createWidget() {
    const widget = new ListWidget();
    widget.backgroundColor = new Color("#1c1c1e");

    // Title
    const titleTxt = widget.addText("📺 YouTube Resumo");
    titleTxt.font = Font.boldSystemFont(16);
    titleTxt.textColor = new Color("#ff0000");
    widget.addSpacer(8);

    // Get URL from Clipboard
    const url = Pasteboard.paste();

    if (!url || !url.includes("youtube.com") && !url.includes("youtu.be")) {
        const errorTxt = widget.addText("⚠️ Copie um link do YouTube primeiro.");
        errorTxt.font = Font.systemFont(12);
        errorTxt.textColor = Color.gray();
    } else {
        // Show Loading state if necessary, but widgets are static snapshot mostly.
        // We will try to fetch the summary.
        const statusTxt = widget.addText("🔄 Processando: " + url.substring(0, 25) + "...");
        statusTxt.font = Font.systemFont(10);
        statusTxt.textColor = Color.gray();

        try {
            const req = new Request(SERVER_URL);
            req.method = "POST";
            req.headers = { "Content-Type": "application/json" };
            req.body = JSON.stringify({ url: url });

            // Timeout to avoid widget crash
            req.timeoutInterval = 60;

            const res = await req.loadJSON();

            if (res.error) {
                const errRes = widget.addText("❌ Erro: " + res.error);
                errRes.textColor = Color.red();
            } else {
                widget.addSpacer(8);
                const summaryTxt = widget.addText(res.summary);
                summaryTxt.font = Font.systemFont(12);
                summaryTxt.textColor = Color.white();
                summaryTxt.minimumScaleFactor = 0.5;
            }

        } catch (e) {
            widget.addSpacer(8);
            const failTxt = widget.addText("❌ Falha na conexão. O servidor Python está rodando?");
            failTxt.font = Font.systemFont(10);
            failTxt.textColor = Color.red();
            console.error(e);
        }
    }

    return widget;
}

if (config.runsInWidget) {
    const widget = await createWidget();
    Script.setWidget(widget);
} else {
    const widget = await createWidget();
    widget.presentLarge();
}

Script.complete();

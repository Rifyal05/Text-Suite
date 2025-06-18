self.importScripts('https://cdn.jsdelivr.net/npm/marked/marked.min.js');
let marked;

function cleanUpAiOutput(text) {
    if (!text) return "";
    let cleanedText = text;
    cleanedText = cleanedText.replace(/^\s*[-•]\s*/gm, '- ');
    cleanedText = cleanedText.replace(/([.?!,")-])([a-zA-Z0-9À-ÖØ-öø-ÿ])/g, '$1 $2');
    cleanedText = cleanedText.replace(/ \n/g, '\n');
    cleanedText = cleanedText.replace(/\n{3,}/g, '\n\n');
    cleanedText = cleanedText.replace(/([a-z])([A-Z])/g, '$1 $2');
    return cleanedText.trim();
}

self.onmessage = async (event) => {
    if (!marked) {
        marked = self.marked;
        marked.setOptions({ gfm: true, breaks: true, sanitize: false, silent: true });
    }
    const { type, data } = event.data;
    let accumulatedText = "";
    let textBuffer = "";
    const TYPING_SPEED = 5;
    const typingIntervalId = setInterval(() => {
        if (textBuffer.length > 0) {
            const char = textBuffer.substring(0, 1);
            accumulatedText += char;
            textBuffer = textBuffer.substring(1);
            self.postMessage({ type: 'update', content: marked.parse(accumulatedText) });
        }
    }, TYPING_SPEED);
    try {
        if (type === 'stream') {
            const response = await fetch(data.url, data.options);
            if (!response.ok || !response.body) {
                throw new Error('Gagal melakukan streaming dari server.');
            }
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                for (const line of lines) {
                    if (line.startsWith('event: error')) {
                        const errorMessage = line.substring(line.indexOf('data:') + 5).trim();
                        throw new Error(errorMessage || 'Kesalahan dari server saat streaming.');
                    }
                    if (line.startsWith('data: ')) {
                        textBuffer += line.substring(6).trim().replace(/\\n/g, '\n');
                    }
                }
            }
        } else if (type === 'static') {
            textBuffer = data.text;
        }
        const finalizationCheck = setInterval(() => {
            if (textBuffer.length === 0) {
                clearInterval(finalizationCheck);
                clearInterval(typingIntervalId);
                const cleanedFinalText = cleanUpAiOutput(accumulatedText);
                self.postMessage({ type: 'done', finalContent: cleanedFinalText });
                self.close();
            }
        }, 50);
    } catch (e) {
        clearInterval(typingIntervalId);
        self.postMessage({ type: 'error', message: e.message });
        self.close();
    }
};
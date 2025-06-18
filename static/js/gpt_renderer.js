// JS KHUSUS UNTUK RENDERING GPT RESPON

const GPT_TYPING_SPEED = 3;

async function renderJsonResponseWithTyping(targetDiv, textToRender, onProcessEndCallback) {
    const marked = await getMarked(); 
    let accumulatedText = "";
    let textBuffer = textToRender || "";
    let typingIntervalId = null;
    let renderFinalized = false;
    const scrollContainer = document.querySelector('.page-container') || document.documentElement;

    function typeCharacter() {
        if (renderFinalized || textBuffer.length === 0) return;
        const char = textBuffer.substring(0, 1);
        accumulatedText += char;
        textBuffer = textBuffer.substring(1);
        targetDiv.innerHTML = marked.parse(accumulatedText);
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
    }

    function finalizeRender(hadError = false) {
        if (renderFinalized) return;
        renderFinalized = true;
        clearInterval(typingIntervalId);
        if (!hadError && textBuffer.length > 0) {
            accumulatedText += textBuffer;
            targetDiv.innerHTML = marked.parse(accumulatedText);
        }
        if (onProcessEndCallback) onProcessEndCallback(hadError, accumulatedText);
    }

    targetDiv.innerHTML = '';
    typingIntervalId = setInterval(typeCharacter, GPT_TYPING_SPEED);

    const finalizationCheck = setInterval(() => {
        if (textBuffer.length === 0) {
            clearInterval(finalizationCheck);
            finalizeRender(false);
        }
    }, 100);
}
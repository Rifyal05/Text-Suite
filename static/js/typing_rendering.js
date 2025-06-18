// JS UNTUK EFEK KETIK GLOBAL

const TYPING_SPEED = 3;

async function renderWithTypingEffect(targetDiv, textToRender, onProcessEndCallback) {
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

    const handleVisibilityChange = () => {
        if (document.visibilityState === 'hidden' && !renderFinalized) {
            clearInterval(typingIntervalId);
            accumulatedText += textBuffer;
            textBuffer = "";
            targetDiv.innerHTML = marked.parse(accumulatedText);
            finalizeRender(false);
        }
    };

    function finalizeRender(hadError = false) {
        if (renderFinalized) return;
        renderFinalized = true;
        document.removeEventListener('visibilitychange', handleVisibilityChange);
        clearInterval(typingIntervalId);
        if (!hadError && textBuffer.length > 0) {
            accumulatedText += textBuffer;
            targetDiv.innerHTML = marked.parse(accumulatedText);
        }
        if (onProcessEndCallback) onProcessEndCallback(hadError, accumulatedText);
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange);

    targetDiv.innerHTML = '';
    typingIntervalId = setInterval(typeCharacter, TYPING_SPEED);

    const finalizationCheck = setInterval(() => {
        if (textBuffer.length === 0) {
            clearInterval(finalizationCheck);
            if (!renderFinalized) {
                finalizeRender(false);
            }
        }
    }, 100);
}
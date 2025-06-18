// JS UNTUK BLOK RENDERING METODE KLASIK

async function renderClassicModelResponse(targetDiv, markdownText, onProcessEndCallback) {
    const marked = await getMarked();
    const cleanedText = cleanUpAiOutput(markdownText);
    targetDiv.innerHTML = marked.parse(cleanedText);
    if (onProcessEndCallback) {
        onProcessEndCallback(false, cleanedText);
    }
}
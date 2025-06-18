window.currentEvalController = null;
let currentWorker = null;

const SVG_SPINNER_ICON = '<svg class="spinner" viewBox="0 0 50 50"><circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle></svg>';
const ORIGINAL_SUBMIT_ICON = '<i class="fa-solid fa-arrow-up"></i>';

function showErrorMessage(container, message) {
    container.innerHTML = `<div class="error-text"><strong>Oops! Terjadi kesalahan:</strong><br>${message}</div>`;
}

function createResultPlaceholder() {
    const placeholder = document.createElement('div');
    placeholder.className = 'markdown-content result-placeholder';
    placeholder.innerHTML = `
        <div class="placeholder-line"></div>
        <div class="placeholder-line"></div>
        <div class="placeholder-line short"></div>
        <br>
        <div class="placeholder-line title"></div>
        <div class="placeholder-line short"></div>
        <div class="placeholder-line short"></div>
    `;
    return placeholder;
}

document.addEventListener('DOMContentLoaded', async function() {
    const form = document.getElementById('mainFeatureForm');
    const resultsContainer = document.getElementById('resultsContainer');
    const submitButton = document.getElementById('submitBtn');
    const mainTextarea = document.getElementById('mainTextarea');
    const algoSelect = document.getElementById('summarizer_algo');
    const comparisonAlgoSelect = document.getElementById('comparison_algo');
    const langSelect = document.getElementById('lang_summarizer');

    if (!form || !resultsContainer || !submitButton || !mainTextarea || !algoSelect || !langSelect) return;

    function updateUIState(isProcessing) {
        submitButton.disabled = isProcessing;
        mainTextarea.disabled = isProcessing;
        submitButton.innerHTML = isProcessing ? SVG_SPINNER_ICON : ORIGINAL_SUBMIT_ICON;
    }

    function createActionBar(originalText, textToCopy, isOutputBlock) {
        const actionBar = document.createElement('div');
        actionBar.className = 'action-bar';
        const copyBtn = document.createElement('button');
        copyBtn.className = 'action-btn';
        copyBtn.innerHTML = '<i class="fa-solid fa-copy"></i> Salin';
        copyBtn.addEventListener('click', () => { navigator.clipboard.writeText(textToCopy).then(() => { const originalContent = copyBtn.innerHTML; copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Tersalin'; setTimeout(() => { copyBtn.innerHTML = originalContent; }, 2000); }); });
        actionBar.appendChild(copyBtn);
        const actionBtn = document.createElement('button');
        actionBtn.className = 'action-btn';
        if (isOutputBlock) {
            actionBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Coba Lagi';
            actionBtn.addEventListener('click', () => { if (submitButton.disabled) return; mainTextarea.value = originalText; form.requestSubmit(); });
        } else {
            actionBtn.innerHTML = '<i class="fa-solid fa-pen-to-square"></i> Ubah';
            actionBtn.addEventListener('click', () => { mainTextarea.value = originalText; mainTextarea.focus(); });
        }
        actionBar.appendChild(actionBtn);
        return actionBar;
    }
    
    function processSingleModel(modelAlgo, originalText, commonPayload) {
        return new Promise(async (resolve, reject) => {
            const selectElement = document.getElementById('summarizer_algo');
            const selectedOption = Array.from(selectElement.options).find(opt => opt.value === modelAlgo);
            const modelNameText = selectedOption ? selectedOption.text.trim() : modelAlgo;
            
            const modelPayload = { ...commonPayload, summarizer_algo: modelAlgo };
            
            const outputContainer = document.createElement('div');
            outputContainer.className = 'results-output ai-output-display';
            outputContainer.innerHTML = `<h2><span class="res-icon">✨</span> Hasil (${modelNameText})</h2>`;
            const resultPlaceholder = createResultPlaceholder();
            outputContainer.appendChild(resultPlaceholder);
            resultsContainer.appendChild(outputContainer);
            
            setTimeout(() => { outputContainer.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 100);

            const worker = new Worker(URL_TO_WORKER_JS);
            
            worker.onmessage = (e) => {
                const { type, content, finalContent, message } = e.data;
                if (type === 'update') {
                    if (resultPlaceholder.classList.contains('result-placeholder')) {
                        resultPlaceholder.classList.remove('result-placeholder');
                    }
                    resultPlaceholder.innerHTML = content;
                    outputContainer.scrollIntoView({ behavior: 'auto', block: 'end' });
                } else if (type === 'done') {
                    resultPlaceholder.innerHTML = marked.parse(finalContent);
                    outputContainer.appendChild(createActionBar(originalText, finalContent, true));
                    worker.terminate();
                    resolve({ result: finalContent, name: modelNameText });
                } else if (type === 'error') {
                    showErrorMessage(resultPlaceholder, message);
                    worker.terminate();
                    reject(new Error(message));
                }
            };
            
            const aiStreamModels = ['gemini', 'learnlm'];
            if (aiStreamModels.includes(modelAlgo)) {
                worker.postMessage({ type: 'stream', data: { url: form.action, options: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(modelPayload) } } });
            } else {
                try {
                    const response = await fetch(form.action, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(modelPayload) });
                    if (!response.ok) {
                        const errData = await response.json().catch(() => ({}));
                        throw new Error(errData.error || `Server merespons dengan status ${response.status}`);
                    }
                    const data = await response.json();
                    if (data.error) throw new Error(data.error);
                    worker.postMessage({ type: 'static', data: { text: data.result } });
                } catch (error) {
                    worker.onmessage({ data: { type: 'error', message: error.message } });
                }
            }
        });
    }

    form.addEventListener('submit', async function(event) {
        event.preventDefault();
        
        if (submitButton.disabled) return;
        if (window.currentEvalController) window.currentEvalController.abort();
        
        const originalText = mainTextarea.value.trim();
        if (!originalText) {
            alert('Teks tidak boleh kosong!');
            return;
        }
        
        updateUIState(true);

        const mainModelAlgo = algoSelect.value;
        const comparisonModelAlgo = comparisonAlgoSelect.value;
        
        const commonPayload = {
            original_text: originalText,
            num_sentences_summary: document.getElementById('num_sentences_summary').value,
            max_keywords_summary: document.getElementById('max_keywords_summary').value,
            lang_summarizer: langSelect.value
        };
        
        mainTextarea.value = '';
        mainTextarea.style.height = 'auto';
        resultsContainer.innerHTML = '';

        const userInputDiv = document.createElement('div');
        userInputDiv.className = 'results-output user-input-display';
        userInputDiv.innerHTML = `<h2><span class="res-icon">👤</span> Teks Anda:</h2><pre></pre>`;
        userInputDiv.querySelector('pre').textContent = originalText;
        userInputDiv.appendChild(createActionBar(originalText, originalText, false));
        resultsContainer.appendChild(userInputDiv);
        
        let mainModelData = null;
        let comparisonModelData = null;

        try {
            mainModelData = await processSingleModel(mainModelAlgo, originalText, commonPayload);
            if (comparisonModelAlgo !== 'none') {
                comparisonModelData = await processSingleModel(comparisonModelAlgo, originalText, commonPayload);
            }
        } catch (error) {
            console.error("Terjadi kesalahan pada salah satu proses model:", error.message);
        }

        const useGrid = !!comparisonModelData;

        if (mainModelData && typeof getAndRenderEvaluations === 'function') {
            getAndRenderEvaluations(originalText, mainModelData.result, langSelect.value, resultsContainer, useGrid, mainModelData.name);
        }

        if (comparisonModelData && typeof getAndRenderEvaluations === 'function') {
            getAndRenderEvaluations(originalText, comparisonModelData.result, langSelect.value, resultsContainer, useGrid, comparisonModelData.name);
        }
        
        if (mainModelData || comparisonModelData) {
            const firstEvalWrapper = resultsContainer.querySelector('.evaluation-wrapper');
            if (firstEvalWrapper) {
                setTimeout(() => { firstEvalWrapper.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 200);
            }
        }
        
        updateUIState(false);
    });

    const languageOptions = { gemini: [{ value: 'auto', text: 'Auto-Deteksi Bahasa ✨' }, { value: 'indonesian', text: 'Bahasa Indonesia' }, { value: 'english', text: 'English' }], learnlm: [{ value: 'auto', text: 'Auto-Deteksi Bahasa ✨' }, { value: 'indonesian', text: 'Bahasa Indonesia' }, { value: 'english', 'text': 'English' }], gpt: [{ value: 'auto', text: 'Auto-Deteksi Bahasa ✨' }, { value: 'indonesian', text: 'Bahasa Indonesia' }, { value: 'english', text: 'English' }], textrank: [{ value: 'indonesian', text: 'Bahasa Indonesia' }, { value: 'english', text: 'English' }], tfidf: [{ value: 'indonesian', text: 'Bahasa Indonesia' }, { value: 'english', 'text': 'English' }],  'gpt-4o-nano': [{ value: 'auto', text: 'Auto-Deteksi Bahasa ✨' }, { value: 'indonesian', text: 'Bahasa Indonesia' }, { value: 'english', text: 'English' }] };
    function updateLanguageOptions() { const selectedAlgo = algoSelect.value; const last = sessionStorage.getItem(`lastLangFor_${selectedAlgo}`); const options = languageOptions[selectedAlgo] || languageOptions.textrank; langSelect.innerHTML = ''; options.forEach(o => { const opt = document.createElement('option'); opt.value = o.value; opt.textContent = o.text; langSelect.appendChild(opt); }); langSelect.value = options.some(o => o.value === last) ? last : options[0].value; }
    algoSelect.addEventListener('change', updateLanguageOptions); langSelect.addEventListener('change', () => sessionStorage.setItem(`lastLangFor_${algoSelect.value}`, langSelect.value)); updateLanguageOptions();
    mainTextarea.addEventListener('keydown', function(event) { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); form.requestSubmit(); } });
});
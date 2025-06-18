document.addEventListener('DOMContentLoaded', async function() {
    const marked = await getMarked();

    const form = document.getElementById('mainFeatureForm');
    if (!form) return;

    const resultsContainer = document.getElementById('translatorResultsContainer');
    const submitButton = document.getElementById('submitBtn');
    const mainTextarea = document.getElementById('mainTextarea');
    const modelSelect = document.getElementById('translation_model');
    const comparisonModelSelect = document.getElementById('comparison_model_translate'); 
    const sourceLangSelect = document.getElementById('source_language_translate');
    const targetLangSelect = document.getElementById('target_language_translate');

    if (!resultsContainer || !submitButton || !mainTextarea || !modelSelect || !comparisonModelSelect || !sourceLangSelect || !targetLangSelect) {
        console.error("TRANSLATOR.JS: Satu atau lebih elemen DOM penting tidak ditemukan. Pastikan ID HTML sudah benar.");
        return;
    }

    const SVG_SPINNER_ICON = '<svg class="spinner" viewBox="0 0 50 50"><circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle></svg>';
    const ORIGINAL_SUBMIT_ICON = '<i class="fa-solid fa-arrow-up"></i>';

    function showErrorMessage(container, message) {
        container.innerHTML = `<div class="error-text"><strong>Oops! Terjadi kesalahan:</strong><br>${message.replace('STATUS_ERROR:', '').trim()}</div>`;
    }

    function createResultPlaceholder() {
        const placeholder = document.createElement('div');
        placeholder.className = 'markdown-content result-placeholder';
        placeholder.innerHTML = `
            <div class="placeholder-line"></div>
            <div class="placeholder-line short"></div>
            <div class="placeholder-line"></div>
        `;
        return placeholder;
    }

    function updateUIState(isProcessing) {
        submitButton.disabled = isProcessing;
        mainTextarea.disabled = isProcessing;
        submitButton.innerHTML = isProcessing ? SVG_SPINNER_ICON : ORIGINAL_SUBMIT_ICON;
    }

    function createActionBar(originalText, textToCopy) {
        const actionBar = document.createElement('div');
        actionBar.className = 'action-bar';
        const copyBtn = document.createElement('button');
        copyBtn.className = 'action-btn';
        copyBtn.innerHTML = '<i class="fa-solid fa-copy"></i> Salin';
        copyBtn.addEventListener('click', () => { navigator.clipboard.writeText(textToCopy).then(() => { const originalContent = copyBtn.innerHTML; copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Tersalin'; setTimeout(() => { copyBtn.innerHTML = originalContent; }, 2000); }); });
        actionBar.appendChild(copyBtn);
        const actionBtn = document.createElement('button');
        actionBtn.className = 'action-btn';
        actionBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Coba Lagi';
        actionBtn.addEventListener('click', () => { if (submitButton.disabled) return; mainTextarea.value = originalText; form.requestSubmit(); });
        actionBar.appendChild(actionBtn);
        return actionBar;
    }
    
    function processSingleModel(modelAlgo, originalText, commonPayload) {
        return new Promise(async (resolve, reject) => {
            const selectElement = Array.from(document.querySelectorAll('#translation_model option, #comparison_model_translate option'))
                                     .find(opt => opt.value === modelAlgo);
            const modelNameText = selectElement ? selectElement.text.trim() : modelAlgo;
            
            const modelPayload = { ...commonPayload, translation_model: modelAlgo };
            
            const outputContainer = document.createElement('div');
            outputContainer.className = 'results-output ai-output-display';

            const contentWrapper = document.createElement('div');
            contentWrapper.className = 'card-content-wrapper';
            
            contentWrapper.innerHTML = `<h2><span class="res-icon">✨</span> Hasil Terjemahan (${modelNameText})</h2>`;
            const resultPlaceholder = createResultPlaceholder();
            contentWrapper.appendChild(resultPlaceholder);
            outputContainer.appendChild(contentWrapper);

            const grid = resultsContainer.querySelector('.translation-grid-container');
            if (grid) {
                grid.appendChild(outputContainer);
            } else {
                resultsContainer.appendChild(outputContainer);
            }
            
            try {
                const actionURL = form.action;
                const response = await fetch(actionURL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                    body: JSON.stringify(modelPayload)
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.error_message || `Server merespons dengan status ${response.status}`);
                }

                const data = await response.json();
                if(data.error_message) throw new Error(data.error_message);

                const translationResult = data.translation_result || '[Terjemahan tidak diterima]';
                
                resultPlaceholder.remove(); // Hapus placeholder
                
                const translationDiv = document.createElement('div');
                translationDiv.innerHTML = `<pre>${translationResult}</pre>`;
                contentWrapper.appendChild(translationDiv); // Tambahkan hasil terjemahan

                addShineEffect(outputContainer);

                if (data.context_explanation) {
                    const contextDiv = document.createElement('div');
                    contextDiv.className = 'context-explanation';
                    contextDiv.innerHTML = `<h4>Penjelasan Konteks:</h4>${marked.parse(data.context_explanation)}`;
                    contentWrapper.appendChild(contextDiv); // Tambahkan konteks
                }
                
                contentWrapper.appendChild(createActionBar(originalText, translationResult)); // Tambahkan action bar
                
                resolve({ result: translationResult, name: modelNameText });

            } catch (error) {
                resultPlaceholder.remove();
                showErrorMessage(contentWrapper, error.message);
                reject(error);
            }
        });
    }

    form.addEventListener('submit', async function(event) {
        event.preventDefault();
        
        if (submitButton.disabled) return;
        if (window.currentEvalController) {
            window.currentEvalController.abort();
            window.currentEvalController = null;
        }
        
        const originalText = mainTextarea.value.trim();
        if (!originalText) {
            alert('Teks tidak boleh kosong!');
            return;
        }
        
        updateUIState(true);

        const mainModelAlgo = modelSelect.value;
        const comparisonModelAlgo = comparisonModelSelect.value;
        const isComparing = comparisonModelAlgo !== 'none' && mainModelAlgo !== comparisonModelAlgo;
        
        const commonPayload = {
            text_to_translate: originalText, 
            source_language_translate: sourceLangSelect.value,
            target_language_translate: targetLangSelect.value,
            comparison_model_translate: comparisonModelAlgo
        };
        
        mainTextarea.value = '';
        mainTextarea.style.height = 'auto';
        resultsContainer.innerHTML = '';

        const userInputDiv = document.createElement('div');
        userInputDiv.className = 'results-output user-input-display';
        const userActionBar = createActionBar(originalText, originalText);
        userActionBar.querySelector('.fa-bolt').parentElement.innerHTML = '<i class="fa-solid fa-pen-to-square"></i> Ubah';
        userActionBar.querySelector('.fa-pen-to-square').parentElement.addEventListener('click', () => { mainTextarea.value = originalText; mainTextarea.focus(); });
        
        userInputDiv.innerHTML = `<h2><span class="res-icon">👤</span> Teks Anda:</h2><pre>${originalText}</pre>`;
        userInputDiv.appendChild(userActionBar);
        resultsContainer.appendChild(userInputDiv);
        
        if(isComparing) {
            const gridDiv = document.createElement('div');
            gridDiv.className = 'translation-grid-container';
            resultsContainer.appendChild(gridDiv);
        }
        
        const modelPromises = [processSingleModel(mainModelAlgo, originalText, commonPayload)];
        if (isComparing) {
            modelPromises.push(processSingleModel(comparisonModelAlgo, originalText, commonPayload));
        }

        try {
            const modelResults = await Promise.allSettled(modelPromises);

            const successfulResults = modelResults.filter(r => r.status === 'fulfilled').map(r => r.value);
            const useEvalGrid = successfulResults.length > 1;

            if (successfulResults.length > 0 && typeof getAndRenderEvaluations === 'function') {
                const evalPromises = successfulResults.map(result => {
                    const { result: translatedText, name: modelName } = result;
                    const evalPayload = {
                        original_text: originalText,
                        translated_text: translatedText,
                        source_lang: sourceLangSelect.value,
                        target_lang: targetLangSelect.value,
                    };
                    return getAndRenderEvaluations(evalPayload, '/translator/evaluate', resultsContainer, modelName, useEvalGrid);
                });
                
                await Promise.all(evalPromises);
            }
        } catch(e) {
            console.error("Terjadi kesalahan saat memproses model atau evaluasi:", e);
        } finally {
            updateUIState(false);
        }
    });

    const LANGUAGES = [
        { code: 'Indonesian', name: 'Indonesia' }, { code: 'English', name: 'English' },
        { code: 'Japanese', name: 'Japanese' }, { code: 'Korean', name: 'Korean' },
        { code: 'Chinese', name: 'Chinese' }, { code: 'Arabic', name: 'Arabic' },
        { code: 'German', name: 'German' }
    ];

    function populateLanguages() {
        const currentSource = sourceLangSelect.value;
        const currentTarget = targetLangSelect.value;
        sourceLangSelect.innerHTML = '<option value="auto">Deteksi Otomatis</option>';
        targetLangSelect.innerHTML = '';
        LANGUAGES.forEach(lang => {
            sourceLangSelect.innerHTML += `<option value="${lang.code}">${lang.name}</option>`;
            targetLangSelect.innerHTML += `<option value="${lang.code}">${lang.name}</option>`;
        });
        sourceLangSelect.value = Array.from(sourceLangSelect.options).some(o => o.value === currentSource) ? currentSource : 'auto';
        targetLangSelect.value = Array.from(targetLangSelect.options).some(o => o.value === currentTarget) ? currentTarget : 'English';
    }
    
    populateLanguages();
    mainTextarea.addEventListener('keydown', function(event) { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); form.requestSubmit(); } });
});

function getMarked() {
    return new Promise((resolve) => {
        const setupMarked = () => { if (!marked.isConfigured) { marked.setOptions({ gfm: true, breaks: true, sanitize: false }); marked.isConfigured = true; } resolve(marked); };
        if (typeof marked !== 'undefined') { setupMarked(); } else { const i = setInterval(() => { if (typeof marked !== 'undefined') { clearInterval(i); setupMarked(); } }, 50); }
    });
}
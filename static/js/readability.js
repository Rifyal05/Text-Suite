document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('mainFeatureForm');
    if (!form) return; 

    const resultsContainer = document.getElementById('readabilityResultsContainer');
    const submitButton = document.getElementById('submitBtn');
    const mainTextarea = document.getElementById('mainTextarea');
    const modelSelect = document.getElementById('analysis_method');

    const SVG_SPINNER_ICON = `<svg class="spinner" viewBox="0 0 50 50"><circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle></svg>`;
    const ORIGINAL_SUBMIT_ICON = '<i class="fa-solid fa-arrow-up"></i>';

    function updateUIState(isLoading) {
        submitButton.disabled = isLoading;
        submitButton.innerHTML = isLoading ? SVG_SPINNER_ICON : ORIGINAL_SUBMIT_ICON;
    }

    function createActionBar(originalText, textToCopy, isAiBlock) {
        const actionBar = document.createElement('div');
        actionBar.className = 'action-bar';
        const copyBtn = document.createElement('button');
        copyBtn.className = 'action-btn';
        copyBtn.innerHTML = '<i class="fa-solid fa-copy"></i> Salin';
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalContent = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Tersalin';
                setTimeout(() => { copyBtn.innerHTML = originalContent; }, 2000);
            });
        });
        actionBar.appendChild(copyBtn);
        
        const retryOrEditBtn = document.createElement('button');
        retryOrEditBtn.className = 'action-btn';
        if (isAiBlock) {
            retryOrEditBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Coba Lagi';
            retryOrEditBtn.addEventListener('click', () => {
                if (submitButton.disabled) return;
                mainTextarea.value = originalText;
                submitButton.click();
            });
        } else {
            retryOrEditBtn.innerHTML = '<i class="fa-solid fa-pen-to-square"></i> Ubah';
            retryOrEditBtn.addEventListener('click', () => {
                mainTextarea.value = originalText;
                mainTextarea.focus();
                mainTextarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
            });
        }
        actionBar.appendChild(retryOrEditBtn);
        return actionBar;
    }

    mainTextarea.addEventListener('keydown', function (event) {
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
            event.preventDefault();
            form.requestSubmit();
        }
    });

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        const text = mainTextarea.value.trim();
        if (!text) {
            alert('Teks tidak boleh kosong!');
            return;
        }
        if (submitButton.disabled) return;
        updateUIState(true);

        const actionURL = resultsContainer.dataset.action;
        const payload = {
            text_to_analyze: text,
            analysis_method: modelSelect.value
        };

        resultsContainer.innerHTML = '';
        mainTextarea.value = '';
        mainTextarea.style.height = 'auto';

        const inputDiv = document.createElement('div');
        inputDiv.className = 'results-output user-input-display';
        inputDiv.innerHTML = `<h2><span class="res-icon">👤</span> Teks Anda:</h2><pre></pre>`;
        inputDiv.querySelector('pre').textContent = text;
        inputDiv.appendChild(createActionBar(text, text, false));
        resultsContainer.appendChild(inputDiv);

        const outputDiv = document.createElement('div');
        outputDiv.className = 'results-output ai-output-display';
        outputDiv.innerHTML = `<h2><span class="res-icon">✨</span> Hasil Analisis:</h2><div class="markdown-content"><p><em>Menganalisis...</em></p></div>`;
        resultsContainer.appendChild(outputDiv);

        try {
            const res = await fetch(actionURL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Gagal memproses analisis.');

            outputDiv.innerHTML = ''; 
            let fullTextToCopy = "";

            if (data.results.classic_analysis) {
                const classic = data.results.classic_analysis;
                fullTextToCopy = `Flesch Reading Ease: ${classic.flesch_reading_ease}\nInterpretasi: ${classic.flesch_reading_ease_interpretation}`;
                outputDiv.innerHTML = `
                    <h2><span class="res-icon">📊</span> Hasil Analisis Klasik</h2>
                    <div class="stats-grid">
                        <div class="stat-item"><span class="stat-label">Flesch Reading Ease:</span><span class="stat-value">${classic.flesch_reading_ease}</span><small class="stat-interpretation">${classic.flesch_reading_ease_interpretation}</small></div>
                        <div class="stat-item"><span class="stat-label">Flesch-Kincaid Grade:</span><span class="stat-value">${classic.flesch_kincaid_grade}</span><small class="stat-interpretation">Perkiraan tingkat pendidikan (AS).</small></div>
                    </div>
                    <p class="info-text"><i class="fas fa-info-circle"></i> <strong>Catatan:</strong> Skor ini paling akurat untuk teks B. Inggris.</p>
                `;
            } else if (data.results.gemini_analysis) {
                const gemini = data.results.gemini_analysis;
                fullTextToCopy = `Skor: ${gemini.skor_keterbacaan}/100\nLevel: ${gemini.level_pembaca}\nAnalisis: ${gemini.analisis_singkat}\n\nSaran:\n${gemini.saran_perbaikan}`;
                outputDiv.innerHTML = `
                    <h2><span class="res-icon">✨</span> Hasil Analisis AI</h2>
                    <div class="stats-grid">
                        <div class="stat-item"><span class="stat-label">Skor Keterbacaan:</span><span class="stat-value">${gemini.skor_keterbacaan}<small>/100</small></span></div>
                        <div class="stat-item"><span class="stat-label">Level Pembaca:</span><span class="stat-value">${gemini.level_pembaca}</span></div>
                    </div>
                    <div class="analysis-summary"><p>${gemini.analisis_singkat}</p></div>
                `;
                if (gemini.saran_perbaikan) {
                    const saranDiv = document.createElement('div');
                    saranDiv.className = 'results-output';
                    saranDiv.style.marginTop = '2rem';
                    saranDiv.innerHTML = `<h2><span class="res-icon">💡</span> Saran Perbaikan:</h2><div class="markdown-content"></div>`;
                    saranDiv.querySelector('.markdown-content').innerHTML = typeof marked !== 'undefined' ? marked.parse(gemini.saran_perbaikan) : `<pre>${gemini.saran_perbaikan}</pre>`;
                    resultsContainer.appendChild(saranDiv);
                }
            }
            outputDiv.appendChild(createActionBar(text, fullTextToCopy, true));
        } catch (error) {
            outputDiv.innerHTML = `<div class="error-text"><strong>Error:</strong> ${error.message}</div>`;
        } finally {
            updateUIState(false);
        }
    });
});
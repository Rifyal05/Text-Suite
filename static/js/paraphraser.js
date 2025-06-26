document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('mainFeatureForm');
    if (!form) return;

    const resultsContainer = document.getElementById('resultsContainer');
    const submitButton = document.getElementById('submitBtn');
    const mainTextarea = document.getElementById('mainTextarea');
    const styleSelect = document.getElementById('paraphrase_style');

    const SVG_SPINNER_ICON = `<svg class="spinner" viewBox="0 0 50 50"><circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle></svg>`;
    const ORIGINAL_SUBMIT_ICON = '<i class="fa-solid fa-arrow-up"></i>';

    function updateUIState(isLoading) {
        submitButton.disabled = isLoading;
        submitButton.innerHTML = isLoading ? SVG_SPINNER_ICON : ORIGINAL_SUBMIT_ICON;
    }

    function createActionBar(textToCopy) {
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
        return actionBar;
    }

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        const text = mainTextarea.value.trim();
        if (!text) {
            alert('Teks untuk diparafrase tidak boleh kosong!');
            return;
        }
        if (submitButton.disabled) return;
        updateUIState(true);

        const payload = {
            text_to_paraphrase: text,
            paraphrase_style: styleSelect.value
        };

        mainTextarea.value = '';
        mainTextarea.style.height = 'auto';
        resultsContainer.innerHTML = '';

        const placeholderDiv = document.createElement('div');
        placeholderDiv.className = 'paraphrase-grid-container';
        placeholderDiv.innerHTML = `
            <div class="results-output placeholder"><div class="placeholder-line title"></div><div class="placeholder-line"></div><div class="placeholder-line short"></div></div>
            <div class="results-output placeholder"><div class="placeholder-line title"></div><div class="placeholder-line"></div><div class="placeholder-line short"></div></div>
            <div class="results-output placeholder"><div class="placeholder-line title"></div><div class="placeholder-line"></div><div class="placeholder-line short"></div></div>
        `;
        resultsContainer.appendChild(placeholderDiv);

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Gagal memproses permintaan.');

            resultsContainer.innerHTML = ''; 

            const inputDiv = document.createElement('div');
            inputDiv.className = 'results-output user-input-display';
            inputDiv.innerHTML = `<h2><span class="res-icon">👤</span> Teks Asli Anda:</h2><pre>${text}</pre>`;
            resultsContainer.appendChild(inputDiv);

            if (data.variations && data.variations.length > 0) {
                const gridContainer = document.createElement('div');
                gridContainer.className = 'paraphrase-grid-container';

                data.variations.forEach(variation => {
                    const variationDiv = document.createElement('div');
                    variationDiv.className = 'results-output ai-output-display';
                    variationDiv.innerHTML = `<h3>${variation.title || 'Variasi'}</h3><pre>${variation.text || 'Tidak ada teks.'}</pre>`;
                    variationDiv.appendChild(createActionBar(variation.text));
                    gridContainer.appendChild(variationDiv);
                });
                resultsContainer.appendChild(gridContainer);
            } else {
                throw new Error("AI tidak memberikan variasi hasil.");
            }

        } catch (error) {
            resultsContainer.innerHTML = `<div class="error-text"><strong>Error:</strong> ${error.message}</div>`;
        } finally {
            updateUIState(false);
        }
    });

    mainTextarea.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            form.requestSubmit();
        }
    });
});
document.addEventListener('DOMContentLoaded', () => {
    // --- Theme Toggle ---
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;
    
    // Initialize theme
    const savedTheme = localStorage.getItem('theme') || 
        (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    body.dataset.theme = savedTheme;
    updateThemeIcon(savedTheme);

    themeToggle.addEventListener('click', () => {
        const newTheme = body.dataset.theme === 'dark' ? 'light' : 'dark';
        body.dataset.theme = newTheme;
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);
    });

    function updateThemeIcon(theme) {
        themeToggle.textContent = theme === 'dark' ? '☀️' : '🌙';
    }

    // --- Tabs (Text vs File) ---
    const tabText = document.getElementById('tab-text');
    const tabFile = document.getElementById('tab-file');
    const panelText = document.getElementById('panel-text');
    const panelFile = document.getElementById('panel-file');
    let currentSource = 'text'; // 'text' or 'file'

    function switchTab(source) {
        currentSource = source;
        if (source === 'text') {
            tabText.classList.add('active');
            tabFile.classList.remove('active');
            panelText.style.display = 'flex';
            panelFile.style.display = 'none';
        } else {
            tabText.classList.remove('active');
            tabFile.classList.add('active');
            panelText.style.display = 'none';
            panelFile.style.display = 'flex';
        }
        updateCliPreview();
    }

    tabText.addEventListener('click', () => switchTab('text'));
    tabFile.addEventListener('click', () => switchTab('file'));

    // --- File Upload ---
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('file-info');

    dropzone.addEventListener('click', () => fileInput.click());
    
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('drag');
    });
    
    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('drag');
    });
    
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag');
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            updateFileInfo();
        }
    });

    fileInput.addEventListener('change', updateFileInfo);

    function updateFileInfo() {
        if (fileInput.files.length) {
            fileInfo.textContent = fileInput.files[0].name;
            fileInfo.style.display = 'block';
            updateCliPreview();
        } else {
            fileInfo.style.display = 'none';
        }
    }

    // --- Locale & Detectors Visibility ---
    const localeSelect = document.getElementById('locale-select');
    const enDetectors = document.getElementById('detectors-en');
    const nlDetectors = document.getElementById('detectors-nl');

    function updateDetectors() {
        const val = localeSelect.value;
        if (val === 'en_US') {
            enDetectors.style.display = 'block';
            nlDetectors.style.display = 'none';
        } else if (val === 'nl_NL') {
            enDetectors.style.display = 'none';
            nlDetectors.style.display = 'block';
        } else {
            enDetectors.style.display = 'block';
            nlDetectors.style.display = 'block';
        }
        updateCliPreview();
    }

    localeSelect.addEventListener('change', updateDetectors);
    // Initial call
    updateDetectors();

    // --- Form Inputs Monitoring for CLI Preview ---
    const inputs = [
        'input-text', 'custom-text', 'cleanup-check', 'verbose-check',
        'output-format', 'pdf-mode', 'font-size'
    ];
    inputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', updateCliPreview);
    });

    document.querySelectorAll('input[name="detector"]').forEach(el => {
        el.addEventListener('change', updateCliPreview);
    });

    // --- Core Actions ---
    const scrubBtn = document.getElementById('scrub-btn');
    const downloadBtn = document.getElementById('download-btn');
    const copyBtn = document.getElementById('copy-btn');
    const outputText = document.getElementById('output-text');
    const resultMeta = document.getElementById('result-meta');

    scrubBtn.addEventListener('click', async () => {
        const state = getFormState();
        if (currentSource === 'text' && !state.text) {
            alert('Please enter some text to scrub.');
            return;
        }
        if (currentSource === 'file' && !fileInput.files.length) {
            alert('Please select a file to scrub.');
            return;
        }

        setLoading(true);
        try {
            let data;
            if (currentSource === 'text') {
                const res = await fetch('/process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: state.text,
                        locale: state.locale,
                        detectors: state.detectors,
                        custom: state.custom,
                        cleanup: state.cleanup,
                        verbose: state.verbose
                    })
                });
                data = await res.json();
            } else {
                const form = new FormData();
                form.append('file', fileInput.files[0]);
                if (state.locale) form.append('locale', state.locale);
                state.detectors.forEach(d => form.append('detectors', d));
                if (state.custom) form.append('custom', state.custom);
                form.append('cleanup', state.cleanup);
                form.append('verbose', state.verbose);
                
                const res = await fetch('/process-file', { method: 'POST', body: form });
                data = await res.json();
            }

            if (data.error) {
                alert(data.error);
            } else {
                renderResults(data);
            }
        } catch (err) {
            console.error(err);
            alert('An error occurred during processing.');
        } finally {
            setLoading(false);
        }
    });

    downloadBtn.addEventListener('click', async () => {
        const state = getFormState();
        // Logic similar to scrub but hitting /export or /download-file
        // Note: Browser handles download via blob/anchor trick
        const btnOriginal = downloadBtn.textContent;
        downloadBtn.textContent = 'Preparing...';
        downloadBtn.disabled = true;
        
        try {
            let res;
            if (currentSource === 'text') {
                res = await fetch('/export', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: state.text,
                        locale: state.locale,
                        detectors: state.detectors,
                        custom: state.custom,
                        cleanup: state.cleanup,
                        output_format: state.format,
                        pdf_mode: state.pdfMode,
                        font_size: state.fontSize
                    })
                });
            } else {
                 const form = new FormData();
                form.append('file', fileInput.files[0]);
                if (state.locale) form.append('locale', state.locale);
                state.detectors.forEach(d => form.append('detectors', d));
                if (state.custom) form.append('custom', state.custom);
                form.append('cleanup', state.cleanup);
                form.append('output_format', state.format);
                form.append('pdf_mode', state.pdfMode);
                form.append('font_size', state.fontSize);
                
                res = await fetch('/download-file', { method: 'POST', body: form });
            }
            
            if (res.ok) {
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                // extract filename from header if possible, else default
                a.download = `scrubbed.${state.format}`; 
                document.body.appendChild(a);
                a.click();
                a.remove();
            } else {
                const j = await res.json();
                alert(j.error || 'Download failed');
            }
        } catch (e) {
            alert('Download failed');
        } finally {
            downloadBtn.textContent = btnOriginal;
            downloadBtn.disabled = false;
        }
    });

    copyBtn.addEventListener('click', () => {
        outputText.select();
        navigator.clipboard.writeText(outputText.value);
        const orig = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        setTimeout(() => copyBtn.textContent = orig, 2000);
    });
    
    const cliCopy = document.getElementById('cli-copy');
    cliCopy.addEventListener('click', () => {
       const code = document.getElementById('cli-code').textContent;
       navigator.clipboard.writeText(code);
       const orig = cliCopy.textContent;
       cliCopy.textContent = 'Copied!';
       setTimeout(() => cliCopy.textContent = orig, 2000);
    });

    // --- Helpers ---
    function getFormState() {
        return {
            text: document.getElementById('input-text').value,
            locale: localeSelect.value || null,
            detectors: Array.from(document.querySelectorAll('input[name="detector"]:checked')).map(cb => cb.value),
            custom: document.getElementById('custom-text').value,
            cleanup: document.getElementById('cleanup-check').checked,
            verbose: document.getElementById('verbose-check').checked,
            format: document.getElementById('output-format').value,
            pdfMode: document.getElementById('pdf-mode').value,
            fontSize: document.getElementById('font-size').value
        };
    }

    function renderResults(data) {
        if (!data.results) return;
        
        const verboseOn = document.getElementById('verbose-check').checked;
        const parts = data.results.map(r => {
            let section = `--- Results for ${r.locale} ---\n${r.text}`;
            if (verboseOn && r.filth) {
                section += `\n\n[VERBOSE LOG]\n` + r.filth.map(f => `- ${f.type}: "${f.text}" -> "${f.replacement}"`).join('\n');
            }
            return section;
        });
        
        outputText.value = parts.join('\n\n');
        resultMeta.textContent = `Processed ${data.results.length} locale(s).`;
    }

    function setLoading(isLoading) {
        scrubBtn.disabled = isLoading;
        scrubBtn.textContent = isLoading ? 'Processing...' : 'Scrub Text';
        if (isLoading) outputText.parentElement.classList.add('loading-overlay'); 
        else outputText.parentElement.classList.remove('loading-overlay');
    }

    async function updateCliPreview() {
        const state = getFormState();
        const cliCode = document.getElementById('cli-code');
        
        try {
            const res = await fetch('/cli-preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source: currentSource,
                    locale: state.locale,
                    detectors: state.detectors,
                    cleanup: state.cleanup,
                    verbose: state.verbose,
                    output_format: state.format,
                    pdf_mode: state.pdfMode,
                    font_size: state.fontSize
                })
            });
            const data = await res.json();
            cliCode.textContent = data.command;
        } catch (e) {
            console.error(e);
        }
    }
});

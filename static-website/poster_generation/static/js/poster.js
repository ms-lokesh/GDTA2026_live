document.addEventListener('DOMContentLoaded', () => {
    
    // --- Upload Logic ---
    const dropArea = document.getElementById('drop-area');
    const fileElem = document.getElementById('fileElem');
    const continueBtn = document.getElementById('continue-btn');
    const previewArea = document.getElementById('preview-area');
    const imagePreview = document.getElementById('image-preview');
    const fileName = document.getElementById('file-name');
    const removeBtn = document.getElementById('remove-btn');
    const errorMsg = document.getElementById('error-message');
    
    let selectedFile = null;

    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.add('hover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.remove('hover'), false);
        });

        dropArea.addEventListener('drop', (e) => {
            let dt = e.dataTransfer;
            let files = dt.files;
            handleFiles(files);
        });

        dropArea.addEventListener('click', () => {
            fileElem.click();
        });

        fileElem.addEventListener('change', function() {
            handleFiles(this.files);
        });

        removeBtn.addEventListener('click', () => {
            selectedFile = null;
            fileElem.value = '';
            dropArea.classList.remove('d-none');
            previewArea.classList.add('d-none');
            continueBtn.classList.add('d-none');
            continueBtn.disabled = true;
            errorMsg.classList.add('d-none');
        });

        continueBtn.addEventListener('click', () => {
            if (!selectedFile) return;
            
            const nameInput = document.getElementById('attendee-name-input');
            if (nameInput && !nameInput.value.trim()) {
                showError('Please enter your name for the poster.');
                return;
            }
            
            // Show loading state
            continueBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Uploading...';
            continueBtn.disabled = true;
            
            let formData = new FormData();
            formData.append('file', selectedFile);

            fetch('/poster/api/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const nameInput = document.getElementById('attendee-name-input');
                    const nameParam = nameInput && nameInput.value ? `&name=${encodeURIComponent(nameInput.value)}` : '';
                    window.location.href = `/poster/processing?id=${data.temp_id}${nameParam}`;
                } else {
                    showError(data.error || 'Upload failed');
                    resetBtn();
                }
            })
            .catch(error => {
                showError('Network error occurred');
                resetBtn();
            });
        });

        function handleFiles(files) {
            if (files.length === 0) return;
            const file = files[0];
            
            // Validate file
            const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
            if (!validTypes.includes(file.type)) {
                showError('Invalid file type. Please upload a JPG, PNG, or WEBP image.');
                return;
            }
            
            if (file.size > 10 * 1024 * 1024) {
                showError('File is too large. Max size is 10MB.');
                return;
            }
            
            errorMsg.classList.add('d-none');
            selectedFile = file;
            
            // Preview
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onloadend = function() {
                imagePreview.src = reader.result;
                fileName.textContent = file.name;
                dropArea.classList.add('d-none');
                previewArea.classList.remove('d-none');
                continueBtn.classList.remove('d-none');
                continueBtn.disabled = false;
            }
        }
        
        function showError(msg) {
            errorMsg.textContent = msg;
            errorMsg.classList.remove('d-none');
        }
        
        function resetBtn() {
            continueBtn.innerHTML = 'Continue <i class="fa fa-arrow-right ms-2"></i>';
            continueBtn.disabled = false;
        }
    }

    // --- Processing Logic ---
    const tempIdInput = document.getElementById('temp-id');
    const nameInput = document.getElementById('attendee-name');
    if (tempIdInput && tempIdInput.value) {
        // Automatically ping the backend to generate
        fetch('/poster/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ id: tempIdInput.value, name: nameInput ? nameInput.value : '' })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.href = `/poster/result?id=${data.poster_id}`;
            } else {
                alert('Generation failed: ' + (data.error || 'Unknown error'));
                window.location.href = '/poster/upload';
            }
        })
        .catch(error => {
            alert('Network error occurred during generation.');
            window.location.href = '/poster/upload';
        });
    }

    // --- Result Logic ---
    const copyBtn = document.getElementById('copy-btn');
    const shareLinkedinBtn = document.getElementById('share-linkedin-btn');
    const captionText = document.getElementById('caption-text');
    const copyToast = document.getElementById('copy-toast');
    const shareInstructions = document.getElementById('share-instructions');
    const downloadBtn = document.getElementById('download-btn');

    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            copyToClipboard();
        });
    }

    if (shareLinkedinBtn) {
        shareLinkedinBtn.addEventListener('click', () => {
            // Trigger download if not done
            downloadBtn.click();
            
            // Copy caption
            copyToClipboard();
            
            // Show instructions
            shareInstructions.classList.remove('d-none');
            
            // Open LinkedIn in new tab with the text prefilled (if LinkedIn allows it)
            // By appending the URL to the text, LinkedIn will scrape it for the image preview.
            setTimeout(() => {
                const text = encodeURIComponent(captionText.value + '\n\n' + window.location.href);
                window.open(`https://www.linkedin.com/feed/?shareActive=true&text=${text}`, '_blank');
            }, 500);
        });
    }

    function copyToClipboard() {
        if (!captionText) return;
        captionText.select();
        captionText.setSelectionRange(0, 99999); // For mobile devices
        navigator.clipboard.writeText(captionText.value).then(() => {
            copyToast.classList.remove('d-none');
            setTimeout(() => {
                copyToast.classList.add('d-none');
            }, 3000);
        });
    }
});

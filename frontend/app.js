// DOM Elements
const fileInput = document.getElementById('resumeFile');
const uploadArea = document.getElementById('uploadArea');
const uploadBtn = document.getElementById('uploadBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const resultsSection = document.getElementById('resultsSection');
const closeResults = document.getElementById('closeResults');
const themeToggle = document.getElementById('themeToggleCheckbox');
const themeToggleResults = document.getElementById('themeToggleResultsCheckbox');
const downloadBtn = document.getElementById('downloadBtn');
const includeFitScoreCheckbox = document.getElementById('includeFitScoreCheckbox');
const includeBestSuitedRoleCheckbox = document.getElementById('includeBestSuitedRoleCheckbox');
const previewEditSkillsBtn = document.getElementById('previewEditSkillsBtn');

// State variables
let currentImageUrl = null;
let currentData = null;
let currentPreviewImageUrl = null;
let currentImageBlob = null;
let currentPreviewFile = null;
let isProcessing = false;

// Role selection state
let selectedJobRole = null;
let jobDescriptionText = null;

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeButton(savedTheme);
}

function updateThemeButton(theme) {
    const isDark = theme === 'dark';
    [themeToggle, themeToggleResults].forEach(checkbox => {
        if (checkbox) {
            checkbox.checked = isDark;
        }
    });
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeButton(newTheme);
}

// Helper Functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getScoreColor(score) {
    if (score >= 80) {
        return 'var(--success)'; // High score -> Green
    } else if (score >= 60) {
        return 'var(--info)';    // Above average -> Blue
    } else if (score >= 40) {
        return 'var(--gold)';    // Below average -> Gold
    } else {
        return 'var(--danger)';  // Worst -> Red
    }
}

// File Selection Handler
function setupFileSelection() {
    fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        const fileListDiv = document.getElementById('fileList');
        const selectedFilesList = document.getElementById('selectedFilesList');
        const previewBtn = document.getElementById('previewFileBtn');
        
        if (files.length > 0) {
            fileListDiv.style.display = 'block';
            selectedFilesList.innerHTML = '';
            files.forEach(file => {
                const li = document.createElement('li');
                li.innerHTML = `<i class="fas fa-file-pdf"></i> ${file.name} (${formatFileSize(file.size)})`;
                selectedFilesList.appendChild(li);
            });
            
            if (files.length === 1) {
                previewBtn.style.display = 'inline-flex';
                currentPreviewFile = files[0];
            } else {
                previewBtn.style.display = 'none';
            }
        } else {
            fileListDiv.style.display = 'none';
            selectedFilesList.innerHTML = '';
            previewBtn.style.display = 'none';
            closeFilePreview();
        }
    });

    const clearUploadsBtn = document.getElementById('clearUploadsBtn');
    if (clearUploadsBtn) {
        clearUploadsBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (isProcessing) return;
            fileInput.value = '';
            const event = new Event('change');
            fileInput.dispatchEvent(event);
        });
    }
}

// Upload Area Interactions
function setupUploadArea() {
    uploadArea.addEventListener('click', (e) => {
        if (isProcessing) return;
        if (e.target.closest('#previewFileBtn') || 
            e.target.closest('#uploadBtn') || 
            e.target.closest('#fileList') || 
            e.target.closest('#filePreviewContainer')) {
            return;
        }
        fileInput.click();
    });
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        if (isProcessing) return;
        uploadArea.classList.add('drag-over');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        if (isProcessing) return;
        uploadArea.classList.remove('drag-over');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        if (isProcessing) return;
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            const event = new Event('change');
            fileInput.dispatchEvent(event);
        }
    });
    
    uploadBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (isProcessing) return;
        const files = fileInput.files;
        
        if (files.length === 0) {
            fileInput.click();
        } else if (files.length === 1) {
            uploadResume();
        } else if (files.length > 1) {
            batchUploadResumes();
        }
    });
}

// Show Notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : type === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle'}"></i>
        <span>${message}</span>
    `;

    const borderColor = type === 'success' ? 'var(--success)'
        : type === 'error' ? 'var(--danger)'
        : type === 'warning' ? 'var(--warning)'
        : 'var(--navy)';

    notification.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: var(--bg-page);
        color: var(--text-primary);
        padding: 12px 16px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 10px;
        z-index: 10000;
        box-shadow: var(--shadow-lg);
        border: 1px solid var(--border);
        border-left: 4px solid ${borderColor};
        font-size: 13px;
        font-weight: 500;
        min-width: 280px;
        animation: slideIn 0.2s ease-out;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.2s ease-out';
        setTimeout(() => notification.remove(), 200);
    }, 3000);
}

// ─────────────────────────────────────────────────────────────
// Skill Customization Modal State
// ─────────────────────────────────────────────────────────────
let _skillModalData     = null;   // structured data from /api/analyze
let _skillModalAnalysis = null;   // gap_analysis from /api/analyze
let _skillModalResponse = null;   // full analyze response
let _selectedSkills     = [];     // currently selected skill objects
let _allSkills          = [];     // all skill objects from API

function getApiUrl() {
    const isProduction = window.location.hostname &&
                         !window.location.hostname.includes('localhost') &&
                         !window.location.hostname.includes('127.0.0.1') &&
                         !window.location.hostname.startsWith('192.168.') &&
                         window.location.protocol !== 'file:';
    return isProduction
        ? '/api'
        : (window.location.hostname ? `http://${window.location.hostname}:5000/api` : 'http://127.0.0.1:5000/api');
}

// Lock UI to prevent multiple submissions
function lockUploadUI() {
    isProcessing = true;
    const btn = document.getElementById('uploadBtn');
    if (btn) {
        btn.disabled = true;
        btn.style.opacity = '0.5';
        btn.style.cursor = 'not-allowed';
    }
    const area = document.getElementById('uploadArea');
    if (area) {
        area.style.opacity = '0.7';
        area.style.cursor = 'not-allowed';
    }
    const clearBtn = document.getElementById('clearUploadsBtn');
    if (clearBtn) {
        clearBtn.disabled = true;
        clearBtn.style.opacity = '0.5';
        clearBtn.style.cursor = 'not-allowed';
    }
}

function unlockUploadUI() {
    isProcessing = false;
    const btn = document.getElementById('uploadBtn');
    if (btn) {
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.style.cursor = 'pointer';
    }
    const area = document.getElementById('uploadArea');
    if (area) {
        area.style.opacity = '1';
        area.style.cursor = 'pointer';
    }
    const clearBtn = document.getElementById('clearUploadsBtn');
    if (clearBtn) {
        clearBtn.disabled = false;
        clearBtn.style.opacity = '1';
        clearBtn.style.cursor = 'pointer';
    }
}

// Single Resume Upload — step 1: analyze only
async function uploadResume() {
    currentImageUrl = null;
    currentImageBlob = null;
    currentPreviewImageUrl = null;

    if (!fileInput.files[0]) {
        showNotification('Please select a file first!', 'warning');
        return;
    }

    const file = fileInput.files[0];
    const validTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ];

    if (!validTypes.includes(file.type)) {
        showNotification('Please upload PDF or DOCX file only!', 'error');
        return;
    }

    if (file.size > 5 * 1024 * 1024) {
        showNotification('File size must be less than 5MB!', 'error');
        return;
    }

    // LOCK UI immediately
    lockUploadUI();

    const formData = new FormData();
    formData.append('resume', file);

    const activeRole = getActiveJobRole();
    const activeJD   = document.getElementById('jobDescriptionText')?.value?.trim() || '';
    if (activeRole) {
        formData.append('job_role', activeRole);
        if (activeJD) formData.append('job_description', activeJD);
    }

    loadingOverlay.style.display = 'flex';
    const loadingH3 = loadingOverlay.querySelector('.loading-text h3');
    const loadingP = loadingOverlay.querySelector('.loading-text p');
    const progressFill = loadingOverlay.querySelector('.progress-fill');
    const progressText = loadingOverlay.querySelector('.progress-text');
    
    if (loadingH3) loadingH3.textContent = "Analyzing Resume Intelligence";
    
    // Cycle through stages smoothly
    let currentStage = 0;
    const stages = [
        { text: "Uploading resume...", pct: 15 },
        { text: "Extracting content...", pct: 40 },
        { text: "Analyzing resume...", pct: 70 },
        { text: "Generating results...", pct: 90 }
    ];
    
    const updateStage = () => {
        if (currentStage < stages.length) {
            const stage = stages[currentStage];
            if (loadingP) loadingP.textContent = stage.text;
            if (progressFill) progressFill.style.width = `${stage.pct}%`;
            if (progressText) progressText.textContent = `${stage.pct}%`;
            currentStage++;
        }
    };
    
    updateStage();
    const stageInterval = setInterval(updateStage, 1000);

    try {
        const API_URL = getApiUrl();
        const response = await fetch(`${API_URL}/analyze`, {
            method: 'POST',
            body: formData
        });

        // Check for double submission / duplicate rejection
        if (response.status === 429) {
            const errData = await response.json();
            throw new Error(errData.error || 'Duplicate request detected.');
        }

        const data = await response.json();
        
        clearInterval(stageInterval);
        if (progressFill) progressFill.style.width = '100%';
        if (progressText) progressText.textContent = '100%';
        
        // Brief delay before closing the overlay
        await new Promise(r => setTimeout(r, 400));
        loadingOverlay.style.display = 'none';

        if (data.success) {
            // Store response for later use in /api/generate
            _skillModalResponse = data;
            _skillModalData     = data.data;
            _skillModalAnalysis = data.gap_analysis;
            _selectedSkills     = (data.recommended_skills || []).slice(0, 7);

            // Reset checkboxes for new upload
            const includeFitScoreCheckbox = document.getElementById('includeFitScoreCheckbox');
            if (includeFitScoreCheckbox) {
                includeFitScoreCheckbox.checked = false;
            }
            const includeBestSuitedRoleCheckbox = document.getElementById('includeBestSuitedRoleCheckbox');
            if (includeBestSuitedRoleCheckbox) {
                includeBestSuitedRoleCheckbox.checked = false;
                const wrapper = document.getElementById('customModalRoleWrapper');
                if (wrapper) wrapper.style.display = 'none';
                const input = document.getElementById('customModalRoleInput');
                if (input) input.value = '';
            }

            // Immediately display the analyzed details on the dashboard
            currentData = data.data;
            currentImageUrl = null;
            currentImageBlob = null;
            currentPreviewImageUrl = null;

            displayResults(data);
            resultsSection.style.display = 'block';
            document.body.classList.add('results-open');
            document.body.style.overflow = 'hidden';
        } else {
            throw new Error(data.error || 'Failed to analyze resume');
        }
    } catch (error) {
        clearInterval(stageInterval);
        loadingOverlay.style.display = 'none';
        showNotification(error.message || 'Error processing resume. Please try again.', 'error');
        console.error('Upload error:', error);
    } finally {
        unlockUploadUI();
    }
}

// ─────────────────────────────────────────────────────────────
// Skill Modal
// ─────────────────────────────────────────────────────────────
function openSkillModal(recommended, all) {
    if (!_selectedSkills || _selectedSkills.length === 0) {
        _selectedSkills = recommended.slice(0, 7);
    }
    _allSkills      = all.length > 0 ? all : recommended;

    renderSkillModal();
    document.getElementById('skillModal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeSkillModal() {
    document.getElementById('skillModal').style.display = 'none';
    document.body.style.overflow = 'auto';
}

function renderSkillModal(filter = '') {
    const selectedGrid = document.getElementById('selectedSkillsGrid');
    const allGrid      = document.getElementById('allSkillsGrid');
    const counter      = document.getElementById('skillCountNum');
    const counterWrap  = document.getElementById('skillCounter');
    const generateBtn  = document.getElementById('skillGenerateBtn');

    const count = _selectedSkills.length;
    counter.textContent = count;
    generateBtn.disabled = count === 0;

    // Selected chips
    selectedGrid.innerHTML = '';
    _selectedSkills.forEach(sp => {
        const isAI = _allSkills.slice(0, 7).some(r => r.skill === sp.skill);
        const chip = _makeChip(sp, true, isAI);
        
        // Setup click on name to deselect
        const nameEl = chip.querySelector('.skill-chip-name');
        if (nameEl) {
            nameEl.addEventListener('click', () => {
                _selectedSkills = _selectedSkills.filter(s => s.skill !== sp.skill);
                renderSkillModal(document.getElementById('skillSearchInput').value);
            });
        }
        
        // Setup click on remove cross to deselect
        const removeEl = chip.querySelector('.skill-chip-remove');
        if (removeEl) {
            removeEl.addEventListener('click', () => {
                _selectedSkills = _selectedSkills.filter(s => s.skill !== sp.skill);
                renderSkillModal(document.getElementById('skillSearchInput').value);
            });
        }
        
        selectedGrid.appendChild(chip);
    });
    if (_selectedSkills.length === 0) {
        selectedGrid.innerHTML = '<span style="color:var(--text-muted);font-size:13px;padding:4px 0;">No skills selected yet</span>';
    }

    // All skills grid (filtered + not already selected)
    allGrid.innerHTML = '';
    const lf = filter.toLowerCase();
    _allSkills.forEach(sp => {
        if (lf && !sp.skill.toLowerCase().includes(lf)) return;
        const isSelected = _selectedSkills.some(s => s.skill === sp.skill);
        if (isSelected) return; // already shown above
        const isAI = _allSkills.indexOf(sp) < 7;
        const chip = _makeChip(sp, false, isAI);
        chip.addEventListener('click', () => {
            _selectedSkills.push({ ...sp });
            renderSkillModal(document.getElementById('skillSearchInput').value);
        });
        allGrid.appendChild(chip);
    });
    if (allGrid.children.length === 0) {
        allGrid.innerHTML = '<span style="color:var(--text-muted);font-size:13px;padding:4px 0;">No matching skills found</span>';
    }
}

function _makeChip(sp, selected, isAI) {
    if (selected) {
        const chip = document.createElement('div');
        chip.className = `skill-chip selected${isAI ? ' ai-pick' : ''}`;
        
        let inner = '';
        inner += `<span class="skill-chip-name" title="Click to deselect">${escapeHtml(sp.skill)}</span>`;
        inner += `
            <div class="skill-pct-editor">
                <input type="number" class="skill-pct-input" min="10" max="100" value="${sp.percentage || 80}" />
                <span class="pct-symbol">%</span>
            </div>
        `;
        inner += `<button type="button" class="skill-chip-remove" title="Deselect skill">&times;</button>`;
        
        chip.innerHTML = inner;
        
        const pctInput = chip.querySelector('.skill-pct-input');
        if (pctInput) {
            pctInput.addEventListener('change', (e) => {
                let val = parseInt(e.target.value, 10);
                if (isNaN(val)) val = 80;
                val = Math.max(10, Math.min(100, val));
                e.target.value = val;
                
                const targetSkill = _selectedSkills.find(s => s.skill === sp.skill);
                if (targetSkill) targetSkill.percentage = val;
                
                const allSkill = _allSkills.find(s => s.skill === sp.skill);
                if (allSkill) allSkill.percentage = val;
            });
            pctInput.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }
        return chip;
    } else {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = `skill-chip${isAI ? ' ai-pick' : ''}`;

        let inner = '';
        if (isAI) inner += '<span class="ai-badge">AI</span>';
        inner += escapeHtml(sp.skill);
        if (sp.percentage) inner += ` <span class="chip-pct">${sp.percentage}%</span>`;
        chip.innerHTML = inner;
        return chip;
    }
}

function setupSkillModal() {
    // Search input
    const searchInput = document.getElementById('skillSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', () => renderSkillModal(searchInput.value));
    }

    // Add custom skill button
    const addCustomBtn = document.getElementById('addCustomSkillBtn');
    if (addCustomBtn) {
        addCustomBtn.addEventListener('click', () => {
            handleAddCustomSkill();
        });
    }

    const customNameInput = document.getElementById('customSkillNameInput');
    if (customNameInput) {
        customNameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleAddCustomSkill();
            }
        });
    }

    // Skip button — use AI selection as-is
    const skipBtn = document.getElementById('skillSkipBtn');
    if (skipBtn) {
        skipBtn.addEventListener('click', () => {
            // Already have _selectedSkills (AI picks); proceed
            triggerGenerateResume();
        });
    }

    // Generate button
    const generateBtn = document.getElementById('skillGenerateBtn');
    if (generateBtn) {
        generateBtn.addEventListener('click', () => {
            if (_selectedSkills.length === 0) {
                showNotification('Please select at least 1 skill', 'warning');
                return;
            }
            triggerGenerateResume();
        });
    }

    // Close button
    const closeBtn = document.getElementById('skillModalCloseBtn');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeSkillModal);
    }

    // Close on overlay click
    const overlay = document.getElementById('skillModal');
    if (overlay) {
        overlay.addEventListener('click', e => {
            if (e.target === overlay) closeSkillModal();
        });
    }
}

function handleAddCustomSkill() {
    const nameInput = document.getElementById('customSkillNameInput');
    const pctInput = document.getElementById('customSkillPctInput');
    if (!nameInput || !pctInput) return;

    const name = nameInput.value.trim();
    let pct = parseInt(pctInput.value, 10);
    if (isNaN(pct)) pct = 80;
    pct = Math.max(10, Math.min(100, pct));

    if (!name) {
        showNotification('Please enter a skill name', 'warning');
        return;
    }

    // Check if already selected
    const alreadySelected = _selectedSkills.some(s => s.skill.toLowerCase() === name.toLowerCase());
    if (alreadySelected) {
        showNotification(`"${name}" is already in your selected list`, 'warning');
        return;
    }

    // Create the skill object
    const newSkill = {
        skill: name,
        percentage: pct,
        category: 'Other'
    };

    // Add to selected list
    _selectedSkills.push(newSkill);

    // Also add to all list if not present so it shows up if deselected
    const existsInAll = _allSkills.some(s => s.skill.toLowerCase() === name.toLowerCase());
    if (!existsInAll) {
        _allSkills.push(newSkill);
    } else {
        // Update its percentage in all skills as well
        const match = _allSkills.find(s => s.skill.toLowerCase() === name.toLowerCase());
        if (match) match.percentage = pct;
    }

    // Reset inputs
    nameInput.value = '';
    pctInput.value = '80';

    // Rerender modal
    renderSkillModal(document.getElementById('skillSearchInput')?.value || '');
    showNotification(`Added custom skill "${name}"`, 'success');
}

// Step 2: Call /api/generate with selected skills
async function triggerGenerateResume() {
    // Show loading state inside modal
    const loader = document.querySelector('.skill-modal-loading');
    if (loader) {
        loader.style.display = 'flex';
    }

    try {
        const includeFitScore = document.getElementById('includeFitScoreCheckbox')?.checked || false;
        const includeBestSuitedRole = document.getElementById('includeBestSuitedRoleCheckbox')?.checked || false;
        const customRole = document.getElementById('customModalRoleInput')?.value?.trim() || '';
        const API_URL = getApiUrl();
        const response = await fetch(`${API_URL}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data: _skillModalData,
                selected_skills: _selectedSkills,
                include_fit_score: includeFitScore,
                include_best_suited_role: includeBestSuitedRole,
                job_role: selectedJobRole,
                custom_role: customRole
            })
        });

        const genData = await response.json();
        closeSkillModal();
        if (loader) {
            loader.style.display = 'none';
        }

        if (genData.success && genData.image_base64) {
            const byteCharacters = atob(genData.image_base64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray  = new Uint8Array(byteNumbers);
            const imageBlob  = new Blob([byteArray], { type: 'image/png' });
            const imageUrl   = URL.createObjectURL(imageBlob);

            currentData             = _skillModalData;
            currentImageUrl         = imageUrl;
            currentImageBlob        = imageBlob;
            currentPreviewImageUrl  = imageUrl;

            // Open the generated resume image in the preview modal
            showPreview(imageUrl, imageBlob);
        } else {
            throw new Error(genData.error || 'Image generation failed');
        }
    } catch (error) {
        closeSkillModal();
        if (loader) {
            loader.style.display = 'none';
        }
        loadingOverlay.style.display = 'none';
        showNotification(error.message || 'Error generating resume.', 'error');
        console.error('Generate error:', error);
    }
}


// Batch Upload Resumes
async function batchUploadResumes() {
    currentImageUrl = null;
    currentImageBlob = null;
    currentPreviewImageUrl = null;

    const files = Array.from(fileInput.files);
    
    if (files.length === 0) {
        showNotification('Please select at least one resume file!', 'warning');
        return;
    }
    
    if (files.length > 10) {
        showNotification('Maximum 10 files allowed per batch!', 'error');
        return;
    }
    
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const invalidFiles = files.filter(f => !validTypes.includes(f.type));
    
    if (invalidFiles.length > 0) {
        showNotification(`${invalidFiles.length} file(s) have invalid format. Use PDF or DOCX.`, 'error');
        return;
    }
    
    // LOCK UI immediately and REDIRECT to loading overlay page
    lockUploadUI();
    loadingOverlay.style.display = 'flex';
    
    const loadingH3 = loadingOverlay.querySelector('.loading-text h3');
    const loadingP = loadingOverlay.querySelector('.loading-text p');
    const progressFill = loadingOverlay.querySelector('.progress-fill');
    const progressText = loadingOverlay.querySelector('.progress-text');
    
    if (loadingH3) loadingH3.textContent = `Processing Batch (0 / ${files.length})`;
    if (loadingP) loadingP.textContent = "Preparing resumes...";
    if (progressFill) progressFill.style.width = '0%';
    if (progressText) progressText.textContent = '0%';
    
    batchResults = [];
    
    try {
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            
            if (loadingH3) loadingH3.textContent = `Processing Batch (${i + 1} / ${files.length})`;
            
            // Loop through progress states for this specific resume to show progress
            let fileStage = 0;
            const fileStages = [
                `[${file.name}] Uploading resumes...`,
                `[${file.name}] Extracting content...`,
                `[${file.name}] Analyzing resumes...`,
                `[${file.name}] Ranking candidates...`,
                `[${file.name}] Generating results...`
            ];
            
            const fileInterval = setInterval(() => {
                if (fileStage < fileStages.length) {
                    const txt = fileStages[fileStage];
                    if (loadingP) loadingP.textContent = txt;
                    
                    const basePct = (i / files.length) * 100;
                    const stepPct = (fileStage / fileStages.length) * (100 / files.length);
                    const totalPct = Math.round(basePct + stepPct);
                    
                    if (progressFill) progressFill.style.width = `${totalPct}%`;
                    if (progressText) progressText.textContent = `${totalPct}% — ${txt}`;
                    
                    fileStage++;
                }
            }, 600);
            
            const formData = new FormData();
            formData.append('resume', file);
            
            // Attach role data to each batch file
            const activeRole = getActiveJobRole();
            const activeJD = document.getElementById('jobDescriptionText')?.value?.trim() || '';
            if (activeRole) {
                formData.append('job_role', activeRole);
                if (activeJD) formData.append('job_description', activeJD);
            }
            
            try {
                const API_URL = getApiUrl();
                const response = await fetch(`${API_URL}/upload`, {
                    method: 'POST',
                    body: formData
                });
                
                // Check if duplicate request
                if (response.status === 429) {
                    const errData = await response.json();
                    throw new Error(errData.error || 'Duplicate request detected.');
                }
                
                const data = await response.json();
                
                if (data.success) {
                    batchResults.push({
                        name: file.name,
                        candidateName: data.data.name,
                        fitScore: data.fit_score,
                        success: true,
                        image_base64: data.image_base64,
                        data: data.data,
                        gap_analysis: data.gap_analysis
                    });
                } else {
                    batchResults.push({
                        name: file.name,
                        success: false,
                        error: data.error
                    });
                }
            } catch (error) {
                batchResults.push({
                    name: file.name,
                    success: false,
                    error: error.message
                });
            } finally {
                clearInterval(fileInterval);
            }
            
            // Set 100% segment progress after each file completes
            const completedPct = Math.round(((i + 1) / files.length) * 100);
            if (progressFill) progressFill.style.width = `${completedPct}%`;
            if (progressText) progressText.textContent = `${completedPct}% — Completed ${file.name}`;
        }
        
        // Show 100% final state briefly
        if (progressFill) progressFill.style.width = '100%';
        if (progressText) progressText.textContent = '100% — Batch Processing Complete!';
        await new Promise(r => setTimeout(r, 600));
        
    } catch (err) {
        console.error('Batch processing error:', err);
    } finally {
        loadingOverlay.style.display = 'none';
        unlockUploadUI();
        displayBatchResults(batchResults);
    }
}

// Display Batch Results
function displayBatchResults(results) {
    const batchSection = document.getElementById('batchResultsSection');
    const resultsGrid = document.getElementById('batchResultsGrid');
    const totalProcessed = document.getElementById('totalProcessed');
    const totalSuccess = document.getElementById('totalSuccess');
    const totalFailed = document.getElementById('totalFailed');
    const avgFitScore = document.getElementById('avgFitScore');
    
    const successCount = results.filter(r => r.success).length;
    const failCount = results.filter(r => !r.success).length;
    const avgScore = results.filter(r => r.success).reduce((sum, r) => sum + (r.fitScore || 0), 0) / (successCount || 1);
    
    totalProcessed.textContent = results.length;
    totalSuccess.textContent = successCount;
    totalFailed.textContent = failCount;
    avgFitScore.textContent = avgScore.toFixed(1);
    
    resultsGrid.innerHTML = '';
    
    results.forEach((result, index) => {
        const card = document.createElement('div');

        if (result.success) {
            card.className = 'batch-result-card';
            card.innerHTML = `
                <div class="batch-card-header">
                    <div class="batch-card-name">${escapeHtml(result.candidateName || result.name)}</div>
                    ${result.data && result.data.recommended_role ? `<div class="batch-card-role">${escapeHtml(result.data.recommended_role)}</div>` : ''}
                </div>
                <div class="batch-card-body">
                    <div class="batch-card-score">
                        <div>
                            <div class="batch-score-value">${result.fitScore || 0}</div>
                            <div class="batch-score-label">Fit Score</div>
                        </div>
                    </div>
                    <div class="batch-card-actions">
                        <button class="batch-view-btn" onclick="viewBatchResume(${index})">
                            <i class="fas fa-eye"></i> Preview
                        </button>
                        <button class="batch-download-btn" onclick="downloadBatchResume(${index})">
                            <i class="fas fa-download"></i> Download
                        </button>
                    </div>
                </div>
            `;
        } else {
            card.className = 'batch-error-card';
            card.innerHTML = `
                <i class="fas fa-exclamation-triangle"></i>
                <div>
                    <strong>${escapeHtml(result.name)}</strong><br>
                    <span>${escapeHtml(result.error)}</span>
                </div>
            `;
        }

        resultsGrid.appendChild(card);
    });
    
    batchSection.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

// View Batch Resume
window.viewBatchResume = function(index) {
    const result = batchResults[index];
    if (result && result.success && result.image_base64) {
        const imageUrl = `data:image/png;base64,${result.image_base64}`;
        const byteCharacters = atob(result.image_base64);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const imageBlob = new Blob([byteArray], { type: 'image/png' });
        showPreview(imageUrl, imageBlob);
    }
};

// Download Batch Resume
window.downloadBatchResume = function(index) {
    const result = batchResults[index];
    if (result && result.success && result.image_base64) {
        const link = document.createElement('a');
        link.href = `data:image/png;base64,${result.image_base64}`;
        link.download = `${result.candidateName || 'resume'}_${index + 1}.png`;
        link.click();
        showNotification('Resume downloaded!', 'success');
    }
};

// Close Batch Results
function closeBatchResults() {
    const batchSection = document.getElementById('batchResultsSection');
    if (batchSection) {
        batchSection.style.display = 'none';
        document.body.style.overflow = 'auto';
        fileInput.value = '';
        document.getElementById('fileList').style.display = 'none';
    }
}

// Display Results
function displayResults(data) {
    const resumeData = data.data;
    const gapAnalysis = data.gap_analysis;
    const skillGap = data.skill_gap || null;
    const jobRole = data.job_role || null;
    const fitScore = resumeData.fit_score || 85;
    
    updateScoreCircle(fitScore);
    
    // Show role label on score card
    const scoreCard = document.getElementById('scoreCard');
    const existingRoleLabel = scoreCard?.querySelector('.score-role-label');
    if (existingRoleLabel) existingRoleLabel.remove();
    if (jobRole && scoreCard) {
        const roleLabel = document.createElement('div');
        roleLabel.className = 'score-role-label';
        roleLabel.innerHTML = `<i class="fas fa-crosshairs"></i> ${jobRole}`;
        scoreCard.insertBefore(roleLabel, scoreCard.firstChild);
    }
    
    const scoreStatus = document.getElementById('scoreStatus');
    if (fitScore >= 80) {
        scoreStatus.textContent = 'Excellent Match';
        scoreStatus.className = 'score-status status-excellent';
    } else if (fitScore >= 60) {
        scoreStatus.textContent = 'Good Potential';
        scoreStatus.className = 'score-status status-good';
    } else {
        scoreStatus.textContent = 'Room for Growth';
        scoreStatus.className = 'score-status status-low';
    }
    
    document.getElementById('strengthCount').textContent = (resumeData.strengths || []).length;
    document.getElementById('expYears').textContent = resumeData.total_experience_years || '0';
    
    const skillsList = document.getElementById('skillsList');
    skillsList.innerHTML = '';
    (resumeData.skills || []).slice(0, 12).forEach(skill => {
        const skillTag = document.createElement('span');
        skillTag.className = 'skill-tag';
        skillTag.textContent = skill;
        skillsList.appendChild(skillTag);
    });
    
    const strengthsList = document.getElementById('strengthsList');
    strengthsList.innerHTML = '';
    (resumeData.strengths || []).forEach(strength => {
        const li = document.createElement('li');
        li.textContent = strength;
        strengthsList.appendChild(li);
    });
    
    const improvementsList = document.getElementById('improvementsList');
    improvementsList.innerHTML = '';
    (resumeData.areas_for_improvement || []).forEach(improvement => {
        const li = document.createElement('li');
        li.textContent = improvement;
        improvementsList.appendChild(li);
    });
    // Render Candidate Avatar (Profile image or initials fallback)
    const candidateAvatar = document.getElementById('candidateAvatar');
    if (candidateAvatar) {
        if (resumeData.profile_image_base64) {
            candidateAvatar.innerHTML = `<img src="data:image/png;base64,${resumeData.profile_image_base64}" alt="${escapeHtml(resumeData.name || 'Candidate')}" class="avatar-image">`;
        } else {
            const initials = (resumeData.name || 'P')
                .split(' ')
                .map(n => n[0])
                .slice(0, 2)
                .join('')
                .toUpperCase();
            candidateAvatar.innerHTML = `<span class="avatar-initials">${escapeHtml(initials)}</span>`;
        }
    }

    document.getElementById('candidateName').textContent = resumeData.name || 'Candidate';
    document.getElementById('candidateRole').textContent = resumeData.current_role || 'Professional';
    document.getElementById('candidateLocation').textContent = resumeData.location || 'Not specified';
    document.getElementById('candidateEmail').textContent = resumeData.email || 'Not provided';
    
    const candidatePhone = document.getElementById('candidatePhone');
    if (candidatePhone) {
        candidatePhone.textContent = resumeData.phone || 'Not provided';
    }
    
    document.getElementById('professionalSummary').textContent = resumeData.professional_summary || 'No summary available.';
    
    // Best Suited Role Badge
    const bestSuitedCard = document.getElementById('bestSuitedRoleCard');
    if (bestSuitedCard) {
        const recommendedRole = resumeData.recommended_role;
        const recommendationReason = resumeData.recommendation_reason;
        
        if (recommendedRole) {
            document.getElementById('suitedRoleTitle').textContent = recommendedRole;
            document.getElementById('suitedRoleReason').textContent = recommendationReason || '';
            bestSuitedCard.style.display = 'block';
        } else {
            bestSuitedCard.style.display = 'none';
        }
    }
    
    const experienceList = document.getElementById('experienceList');
    experienceList.innerHTML = '';
    (resumeData.latest_3_experiences || []).forEach(exp => {
        const expDiv = document.createElement('div');
        expDiv.className = 'experience-item';
        expDiv.innerHTML = `
            <div class="exp-header">
                <span class="exp-title">${escapeHtml(exp.role || 'Role')}</span>
                <span class="exp-duration">${escapeHtml(exp.duration || '')}</span>
            </div>
            <div class="exp-company">${escapeHtml(exp.company || 'Company')}</div>
            ${(exp.responsibilities || []).length > 0 ? `<ul class="exp-description">
                ${(exp.responsibilities || []).map(resp => `<li>${escapeHtml(resp)}</li>`).join('')}
            </ul>` : ''}
        `;
        experienceList.appendChild(expDiv);
    });

    // Render Projects Section
    const projects = resumeData.projects || [];
    const projectsCard = document.getElementById('projectsCard');
    const projectsList = document.getElementById('projectsList');
    
    if (projectsCard && projectsList) {
        if (projects.length > 0) {
            projectsCard.style.display = 'block';
            projectsList.innerHTML = '';
            projects.forEach(proj => {
                const projDiv = document.createElement('div');
                projDiv.className = 'project-item';
                
                const techTags = (proj.technologies || []).map(tech => 
                    `<span class="project-tech-tag">${escapeHtml(tech)}</span>`
                ).join('');
                
                projDiv.innerHTML = `
                    <div class="project-item-header">
                        <h4>${escapeHtml(proj.name || 'Project Name')}</h4>
                        ${proj.duration ? `<span class="project-duration">${escapeHtml(proj.duration)}</span>` : ''}
                    </div>
                    <p class="project-desc">${escapeHtml(proj.description || '')}</p>
                    ${techTags ? `<div class="project-techs">${techTags}</div>` : ''}
                `;
                projectsList.appendChild(projDiv);
            });
        } else {
            projectsCard.style.display = 'none';
        }
    }
    
    const certifications = resumeData.certifications || [];
    if (certifications.length > 0) {
        document.getElementById('certificationsCard').style.display = 'block';
        const certList = document.getElementById('certificationsList');
        certList.innerHTML = '';
        certifications.forEach(cert => {
            const certSpan = document.createElement('span');
            certSpan.className = 'certification-item';
            certSpan.textContent = cert;
            certList.appendChild(certSpan);
        });
    }
    
    const education = resumeData.education || {};
    const educationInfo = document.getElementById('educationInfo');
    if (educationInfo) {
        educationInfo.innerHTML = `
            <div class="edu-item">
                <div class="edu-degree">${escapeHtml(education.degree || 'Degree')}</div>
                <div class="edu-institution">${escapeHtml(education.institution || 'Institution')}</div>
                <div class="edu-year">${escapeHtml(education.year || '')}</div>
            </div>
        `;
    }
    
    // Resume Quality Score
    if (resumeData.resume_quality_score) {
        const qualityValue = document.getElementById('qualityValue');
        const qualityVerdict = document.getElementById('qualityVerdict');
        const qualityCircle = document.getElementById('qualityCircle');
        const qualityObservations = document.getElementById('qualityObservations');
        
        const qualityScore = resumeData.resume_quality_score;
        const qualityVerdictText = resumeData.resume_quality_verdict || 
            (qualityScore >= 90 ? "Excellent" : qualityScore >= 70 ? "Good" : qualityScore >= 50 ? "Average" : qualityScore >= 30 ? "Poor" : "Very Poor");
        
        if (qualityVerdict) {
            qualityVerdict.textContent = qualityVerdictText;
            qualityVerdict.className = `quality-verdict ${qualityVerdictText.toLowerCase().replace(' ', '-')}`;
        }
        
        if (qualityCircle) {
            let currentQ = 0;
            const targetQ = qualityScore;
            
            const color = getScoreColor(0);
            qualityCircle.style.background = `conic-gradient(${color} 0deg 0deg, var(--bg-surface-alt) 0deg 360deg)`;
            if (qualityValue) {
                qualityValue.textContent = 0;
                qualityValue.style.color = color;
            }
            
            if (targetQ > 0) {
                const qInterval = setInterval(() => {
                    if (currentQ >= targetQ) {
                        clearInterval(qInterval);
                    } else {
                        currentQ++;
                        if (qualityValue) qualityValue.textContent = currentQ;
                        const angle = (currentQ / 100) * 360;
                        const currentColor = getScoreColor(currentQ);
                        qualityCircle.style.background = `conic-gradient(${currentColor} 0deg ${angle}deg, var(--bg-surface-alt) ${angle}deg 360deg)`;
                        if (qualityValue) qualityValue.style.color = currentColor;
                    }
                }, 18);
            }
        } else if (qualityValue) {
            qualityValue.textContent = qualityScore;
            qualityValue.style.color = getScoreColor(qualityScore);
        }
        
        if (qualityObservations) {
            const observations = resumeData.quality_observations || [];
            qualityObservations.innerHTML = '';
            observations.forEach(obs => {
                const p = document.createElement('p');
                p.innerHTML = `<i class="fas fa-info-circle"></i> ${obs}`;
                qualityObservations.appendChild(p);
            });
        }
    }
    
    // Red Flags
    const redFlags = resumeData.red_flags || {};
    const redFlagsCard = document.getElementById('redFlagsCard');
    const redFlagsList = document.getElementById('redFlagsList');
    const hasRedFlags = Object.values(redFlags).some(flag => flag === true);
    
    if (hasRedFlags && redFlagsCard) {
        redFlagsCard.style.display = 'block';
        if (redFlagsList) {
            redFlagsList.innerHTML = '';
            
            const flagNames = {
                missing_contact_info: "Missing contact information",
                no_work_experience: "No work experience documented",
                vague_descriptions: "Vague job descriptions",
                generic_skills: "Generic or irrelevant skills",
                missing_dates: "Missing dates in experience/education",
                unprofessional_language: "Unprofessional language detected",
                incomplete_education: "Incomplete education section",
                poor_formatting: "Poor resume formatting",
                irrelevant_skills: "Irrelevant skills listed"
            };
            
            for (const [flag, isPresent] of Object.entries(redFlags)) {
                if (isPresent && flagNames[flag]) {
                    const flagItem = document.createElement('span');
                    flagItem.className = 'red-flag-item';
                    flagItem.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${flagNames[flag]}`;
                    redFlagsList.appendChild(flagItem);
                }
            }
        }
    } else if (redFlagsCard) {
        redFlagsCard.style.display = 'none';
    }
    
    // Gap Analysis
    if (gapAnalysis) {
        const gapCard = document.getElementById('gapAnalysisCard');
        if (gapCard) {
            gapCard.style.display = 'block';
            document.getElementById('gapCurrentStatus').textContent = gapAnalysis.current_status || 'Unknown';
            
            const eduGap = gapAnalysis.education_to_employment_gap;
            const eduGapRow = document.getElementById('eduGapRow');
            if (eduGap && eduGapRow) {
                document.getElementById('eduGapText').innerHTML = `${eduGap.description}: ${eduGap.duration_years} Year${eduGap.duration_years !== 1 ? 's' : ''}`;
                eduGapRow.style.display = 'flex';
            } else if (eduGapRow) {
                eduGapRow.style.display = 'none';
            }
            
            const empGaps = gapAnalysis.employment_gaps || [];
            const empGapsList = document.getElementById('empGapsList');
            if (empGaps.length > 0 && empGapsList) {
                empGapsList.innerHTML = '';
                empGaps.forEach(gap => {
                    const div = document.createElement('div');
                    div.className = 'gap-item';
                    div.innerHTML = `${gap.description}: ${gap.duration_years} Year${gap.duration_years !== 1 ? 's' : ''}`;
                    empGapsList.appendChild(div);
                });
                document.getElementById('empGapsRow').style.display = 'block';
            } else {
                document.getElementById('empGapsRow').style.display = 'none';
            }
            
            const careerBreaks = gapAnalysis.career_breaks || [];
            const careerBreaksList = document.getElementById('careerBreaksList');
            if (careerBreaks.length > 0 && careerBreaksList) {
                careerBreaksList.innerHTML = '';
                careerBreaks.forEach(breakItem => {
                    const div = document.createElement('div');
                    div.className = 'gap-item';
                    div.innerHTML = `${breakItem.description}: ${breakItem.duration_years} Year${breakItem.duration_years !== 1 ? 's' : ''}`;
                    careerBreaksList.appendChild(div);
                });
                document.getElementById('careerBreaksRow').style.display = 'block';
            } else {
                document.getElementById('careerBreaksRow').style.display = 'none';
            }
            
            const currentGap = gapAnalysis.current_employment_gap;
            const currentGapRow = document.getElementById('currentGapRow');
            if (currentGap && currentGapRow) {
                document.getElementById('currentGapText').innerHTML = `${currentGap.from_year} to ${currentGap.to_year}: ${currentGap.duration_years} Year${currentGap.duration_years !== 1 ? 's' : ''}`;
                currentGapRow.style.display = 'flex';
            } else if (currentGapRow) {
                currentGapRow.style.display = 'none';
            }
            
            const totalGap = gapAnalysis.total_gap_years || 0;
            document.getElementById('totalGap').textContent = `${totalGap} Year${totalGap !== 1 ? 's' : ''}`;
            
            const riskText = gapAnalysis.risk_indicator || 'No Gap (0 Years)';
            const riskElement = document.getElementById('riskIndicator');
            if (riskElement) {
                riskElement.textContent = riskText;
                const riskClass = riskText.includes('No Gap') ? 'low'
                    : riskText.includes('Minor') ? 'low'
                    : riskText.includes('Moderate') ? 'medium'
                    : 'high';
                riskElement.className = `gap-risk-value ${riskClass}`;
            }
        }
    }
    
    // Skill Gap Analysis
    if (skillGap && jobRole) {
        displaySkillGapPanel(skillGap, jobRole);
    } else {
        const gapCard = document.getElementById('skillGapCard');
        if (gapCard) gapCard.style.display = 'none';
    }
    
    // Truncation warning
    if (resumeData.resume_truncated) {
        const analysisCol = document.querySelector('.analysis-column');
        const existingWarn = analysisCol?.querySelector('.truncation-warning');
        if (!existingWarn && analysisCol) {
            const warn = document.createElement('div');
            warn.className = 'truncation-warning';
            warn.innerHTML = `<i class="fas fa-exclamation-triangle"></i>
                Resume exceeded 20,000 characters — some content was trimmed. 
                Consider shortening your resume for best results.`;
            analysisCol.insertBefore(warn, analysisCol.firstChild);
        }
    }
}

// Skill Gap Panel
function displaySkillGapPanel(skillGap, roleName) {
    const card = document.getElementById('skillGapCard');
    if (!card) return;
    
    card.style.display = 'block';
    
    // Role badge
    const badge = document.getElementById('roleTargetBadge');
    if (badge) badge.textContent = roleName;
    
    // Match bar
    const pct = skillGap.match_percentage || 0;
    const pctEl = document.getElementById('gapMatchPct');
    const fillEl = document.getElementById('gapBarFill');
    if (pctEl) pctEl.textContent = `${pct}%`;
    if (fillEl) {
        fillEl.style.width = '0%';
        setTimeout(() => { fillEl.style.width = `${pct}%`; }, 100);
        // Dynamic colour based on match
        if (pct >= 70) fillEl.style.background = 'var(--success)';
        else if (pct >= 40) fillEl.style.background = 'var(--navy)';
        else fillEl.style.background = 'var(--danger)';
    }
    
    // Skills grid
    const grid = document.getElementById('gapSkillsGrid');
    if (grid) {
        grid.innerHTML = '';
        (skillGap.matched_skills || []).forEach(skill => {
            const el = document.createElement('span');
            el.className = 'gap-skill-matched';
            el.innerHTML = `<i class="fas fa-check"></i> ${escapeHtml(skill)}`;
            grid.appendChild(el);
        });
        (skillGap.missing_skills || []).forEach(skill => {
            const el = document.createElement('span');
            el.className = 'gap-skill-missing';
            el.innerHTML = `<i class="fas fa-times"></i> ${escapeHtml(skill)}`;
            grid.appendChild(el);
        });
        (skillGap.preferred_matched || []).forEach(skill => {
            const el = document.createElement('span');
            el.className = 'gap-skill-preferred';
            el.innerHTML = `<i class="fas fa-star"></i> ${escapeHtml(skill)}`;
            grid.appendChild(el);
        });
        if (grid.children.length === 0) {
            grid.innerHTML = '<span style="color:var(--text-muted);font-size:12px;">No skill data available</span>';
        }
    }
    
    // Meta row
    const expEl = document.getElementById('gapExpPct');
    const certEl = document.getElementById('gapCertPct');
    if (expEl) expEl.textContent = `${skillGap.experience_match_pct || 0}%`;
    if (certEl) certEl.textContent = `${skillGap.certification_match_pct || 0}%`;
    
    // Recommendations
    const recDiv = document.getElementById('gapRecommendations');
    if (recDiv) {
        recDiv.innerHTML = '';
        const recs = skillGap.recommendations || [];
        if (recs.length > 0) {
            const header = document.createElement('div');
            header.className = 'gap-rec-header';
            header.innerHTML = `<i class="fas fa-lightbulb"></i> Recommendations`;
            recDiv.appendChild(header);
            recs.forEach(rec => {
                const item = document.createElement('div');
                item.className = 'gap-rec-item';
                item.innerHTML = `<i class="fas fa-arrow-right"></i> ${escapeHtml(rec)}`;
                recDiv.appendChild(item);
            });
        }
    }
}

function updateScoreCircle(score) {
    const scoreCircle = document.getElementById('scoreCircle');
    const scoreValue = document.querySelector('.score-value');
    if (!scoreCircle || !scoreValue) return;

    if (score === 0) {
        scoreValue.textContent = 0;
        scoreCircle.style.background = `conic-gradient(var(--danger) 0deg 0deg, var(--bg-surface-alt) 0deg 360deg)`;
        scoreValue.style.color = 'var(--danger)';
        return;
    }

    let currentScore = 0;
    const interval = setInterval(() => {
        if (currentScore >= score) {
            clearInterval(interval);
        } else {
            currentScore++;
            scoreValue.textContent = currentScore;
            const angle = (currentScore / 100) * 360;
            const color = getScoreColor(currentScore);
            scoreCircle.style.background = `conic-gradient(${color} 0deg ${angle}deg, var(--bg-surface-alt) ${angle}deg 360deg)`;
            scoreValue.style.color = color;
        }
    }, 20);
}

// File Preview Functions
async function previewSelectedFile() {
    const file = fileInput.files[0];
    if (!file) {
        showNotification('No file selected to preview', 'warning');
        return;
    }
    
    const previewContainer = document.getElementById('filePreviewContainer');
    const previewContent = document.getElementById('filePreviewContent');
    const previewFileName = document.getElementById('previewFileName');
    const previewFileSize = document.getElementById('previewFileSize');
    
    previewContainer.style.display = 'block';
    previewContent.innerHTML = '<div class="preview-loading"><i class="fas fa-spinner fa-pulse"></i><span>Loading preview...</span></div>';
    
    previewFileName.textContent = file.name;
    previewFileSize.textContent = formatFileSize(file.size);
    
    try {
        const fileType = file.type;
        const fileExtension = file.name.split('.').pop().toLowerCase();
        
        if (fileType === 'application/pdf' || fileExtension === 'pdf') {
            const fileUrl = URL.createObjectURL(file);
            previewContent.innerHTML = `
                <iframe src="${fileUrl}" style="width:100%; height:400px; border:none; border-radius:8px;"></iframe>
            `;
        } else if (fileType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' || fileExtension === 'docx') {
            previewContent.innerHTML = `
                <div style="text-align: center; padding: 40px;">
                    <i class="fas fa-file-word" style="font-size: 64px; color: #2b5797; margin-bottom: 16px; display: block;"></i>
                    <p><strong>DOCX File Preview</strong></p>
                    <p>Click "Upload & Process" to analyze this resume.</p>
                </div>
            `;
        } else {
            const reader = new FileReader();
            reader.onload = function(e) {
                const text = e.target.result;
                const previewText = text.substring(0, 2000);
                previewContent.innerHTML = `
                    <pre style="white-space: pre-wrap; font-family: monospace; font-size: 12px; margin: 0; padding: 16px;">${escapeHtml(previewText)}${text.length > 2000 ? '\n\n... (file truncated)' : ''}</pre>
                `;
            };
            reader.readAsText(file.slice(0, 2000));
        }
    } catch (error) {
        console.error('Preview error:', error);
        previewContent.innerHTML = `<div class="preview-loading"><i class="fas fa-exclamation-triangle"></i><span>Could not preview this file.</span></div>`;
    }
}

function closeFilePreview() {
    const previewContainer = document.getElementById('filePreviewContainer');
    if (previewContainer) {
        previewContainer.style.display = 'none';
    }
    const previewContent = document.getElementById('filePreviewContent');
    if (previewContent) {
        previewContent.innerHTML = '';
    }
}

// Preview Modal Functions
function showPreview(imageUrl, imageBlob) {
    const modal = document.getElementById('previewModal');
    const previewImg = document.getElementById('previewImage');
    
    if (!modal || !previewImg) {
        showNotification('Preview not available', 'error');
        return;
    }
    
    currentPreviewImageUrl = imageUrl;
    currentImageBlob = imageBlob;
    previewImg.src = imageUrl;
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closePreview() {
    const modal = document.getElementById('previewModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

function downloadFromPreview() {
    const previewImg = document.getElementById('previewImage');
    if (previewImg && previewImg.src) {
        const link = document.createElement('a');
        link.href = previewImg.src;
        
        let filename = 'resume_output.png';
        if (_skillModalData && _skillModalData.name) {
            const cleanName = _skillModalData.name.toLowerCase().trim().replace(/[^a-z0-9]/g, '_');
            if (cleanName) {
                filename = `${cleanName}_resume.png`;
            }
        } else if (currentData && currentData.name) {
            const cleanName = currentData.name.toLowerCase().trim().replace(/[^a-z0-9]/g, '_');
            if (cleanName) {
                filename = `${cleanName}_resume.png`;
            }
        } else {
            filename = `resume_report_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.png`;
        }
        
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showNotification('Resume downloaded successfully!', 'success');
        closePreview();
    } else {
        showNotification('No image available to download', 'error');
    }
}

function downloadImage() {
    if (_skillModalResponse) {
        openSkillModal(_skillModalResponse.recommended_skills || [], _skillModalResponse.all_skills || []);
    } else {
        showNotification('No analyzed resume data available', 'error');
    }
}

function closeResultsHandler() {
    resultsSection.style.display = 'none';
    document.body.classList.remove('results-open');
    document.body.style.overflow = 'auto';
    fileInput.value = '';
    document.getElementById('fileList').style.display = 'none';
    closeFilePreview();
}

function setupPreviewModal() {
    const previewCloseBtn = document.getElementById('previewCloseBtn');
    const previewCancelBtn = document.getElementById('previewCancelBtn');
    const previewDownloadBtn = document.getElementById('previewDownloadBtn');
    const modal = document.getElementById('previewModal');
    
    if (previewCloseBtn) previewCloseBtn.addEventListener('click', closePreview);
    if (previewCancelBtn) previewCancelBtn.addEventListener('click', closePreview);
    if (previewDownloadBtn) previewDownloadBtn.addEventListener('click', downloadFromPreview);
    
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closePreview();
        });
    }
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const modalEl = document.getElementById('previewModal');
            if (modalEl && modalEl.style.display === 'flex') closePreview();
        }
    });
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    @keyframes slideUp {
        from { transform: translateY(100%); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
`;
document.head.appendChild(style);

async function generateDefaultResume() {
    loadingOverlay.style.display = 'flex';
    const loadingP = loadingOverlay.querySelector('.loading-text p');
    if (loadingP) {
        loadingP.textContent = 'Generating professional resume preview…';
    }

    try {
        const API_URL = getApiUrl();
        const response = await fetch(`${API_URL}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data: _skillModalData,
                selected_skills: _selectedSkills,
                include_fit_score: false,
                include_best_suited_role: false,
                job_role: selectedJobRole
            })
        });

        const genData = await response.json();
        loadingOverlay.style.display = 'none';

        if (genData.success && genData.image_base64) {
            const byteCharacters = atob(genData.image_base64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray  = new Uint8Array(byteNumbers);
            const imageBlob  = new Blob([byteArray], { type: 'image/png' });
            const imageUrl   = URL.createObjectURL(imageBlob);

            currentData             = _skillModalData;
            currentImageUrl         = imageUrl;
            currentImageBlob        = imageBlob;
            currentPreviewImageUrl  = imageUrl;

            showPreview(imageUrl, imageBlob);
        } else {
            throw new Error(genData.error || 'Image generation failed');
        }
    } catch (error) {
        loadingOverlay.style.display = 'none';
        showNotification(error.message || 'Error generating resume.', 'error');
        console.error('Generate error:', error);
    }
}

function handlePreviewDownloadClick() {
    if (currentImageUrl && currentImageBlob) {
        showPreview(currentImageUrl, currentImageBlob);
    } else if (_skillModalResponse) {
        generateDefaultResume();
    } else {
        showNotification('No analyzed resume data available', 'error');
    }
}

// Event Listeners
themeToggle.addEventListener('change', toggleTheme);
if (themeToggleResults) {
    themeToggleResults.addEventListener('change', toggleTheme);
}
if (downloadBtn) {
    downloadBtn.addEventListener('click', handlePreviewDownloadClick);
}
if (previewEditSkillsBtn) {
    previewEditSkillsBtn.addEventListener('click', () => {
        closePreview();
        if (_skillModalResponse) {
            openSkillModal(_skillModalResponse.recommended_skills || [], _skillModalResponse.all_skills || []);
        }
    });
}
closeResults.addEventListener('click', closeResultsHandler);

// Role Selector Setup
function getActiveJobRole() {
    const sel = document.getElementById('jobRoleSelect');
    const custom = document.getElementById('customRoleInput');
    if (!sel) return null;
    if (sel.value === '__custom__') {
        const customVal = custom?.value?.trim();
        return customVal || null;
    }
    return sel.value || null;
}

async function setupRoleSelector() {
    const select = document.getElementById('jobRoleSelect');
    if (!select) return;
    try {
        const isProduction = window.location.hostname && 
                             !window.location.hostname.includes('localhost') && 
                             !window.location.hostname.includes('127.0.0.1') && 
                             !window.location.hostname.startsWith('192.168.') && 
                             window.location.protocol !== 'file:';
        const API_URL = isProduction 
            ? '/api' 
            : (window.location.hostname ? `http://${window.location.hostname}:5000/api` : 'http://127.0.0.1:5000/api');
        const res = await fetch(`${API_URL}/job-roles`);
        if (res.ok) {
            const data = await res.json();
            (data.roles || []).forEach(role => {
                const opt = document.createElement('option');
                opt.value = role;
                opt.textContent = role;
                select.appendChild(opt);
            });
        }
    } catch(e) {
        console.warn('Could not load job roles:', e);
    }
    
    const customWrapper = document.getElementById('customRoleWrapper');
    const clearBtn = document.getElementById('roleClearBtn');
    const badge = document.getElementById('roleSelectedBadge');
    const badgeName = document.getElementById('roleSelectedName');
    const customInput = document.getElementById('customRoleInput');
    const jdToggle = document.getElementById('jdToggleBtn');
    const jdWrapper = document.getElementById('jdTextareaWrapper');
    const jdChevron = document.getElementById('jdChevron');
    const jdTextarea = document.getElementById('jobDescriptionText');
    const jdCount = document.getElementById('jdCharCount');
    
    function updateBadge() {
        const role = getActiveJobRole();
        if (role) {
            badge.style.display = 'flex';
            badgeName.textContent = role;
            clearBtn.style.display = 'flex';
        } else {
            badge.style.display = 'none';
            clearBtn.style.display = 'none';
        }
    }
    
    select.addEventListener('change', () => {
        if (select.value === '__custom__') {
            customWrapper.style.display = 'block';
            customInput.focus();
        } else {
            customWrapper.style.display = 'none';
        }
        updateBadge();
    });
    
    customInput?.addEventListener('input', updateBadge);
    
    clearBtn?.addEventListener('click', () => {
        select.value = '';
        if (customInput) customInput.value = '';
        if (jdTextarea) jdTextarea.value = '';
        customWrapper.style.display = 'none';
        jdWrapper.style.display = 'none';
        jdChevron?.classList.remove('open');
        badge.style.display = 'none';
        clearBtn.style.display = 'none';
        if (jdCount) jdCount.textContent = '0 / 4000 characters';
    });
    
    jdToggle?.addEventListener('click', () => {
        const isOpen = jdWrapper.style.display !== 'none';
        jdWrapper.style.display = isOpen ? 'none' : 'block';
        jdChevron?.classList.toggle('open', !isOpen);
    });
    
    jdTextarea?.addEventListener('input', () => {
        const len = jdTextarea.value.length;
        if (jdCount) jdCount.textContent = `${len} / 4000 characters`;
        if (len > 4000) jdTextarea.value = jdTextarea.value.slice(0, 4000);
    });
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && resultsSection.style.display === 'block') {
        closeResultsHandler();
    }
});

const previewFileBtn = document.getElementById('previewFileBtn');
if (previewFileBtn) {
    previewFileBtn.addEventListener('click', previewSelectedFile);
}

const closePreviewBtn = document.getElementById('closePreviewBtn');
if (closePreviewBtn) {
    closePreviewBtn.addEventListener('click', closeFilePreview);
}

const downloadAllBtn = document.getElementById('downloadAllBtn');
if (downloadAllBtn) {
    downloadAllBtn.addEventListener('click', () => {
        showNotification('ZIP download feature coming soon', 'info');
    });
}

const closeBatchResultsBtn = document.getElementById('closeBatchResults');
if (closeBatchResultsBtn) {
    closeBatchResultsBtn.addEventListener('click', closeBatchResults);
}

function setupTooltips() {
    const infoButtons = document.querySelectorAll('.score-info');
    infoButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (e.target.closest('.tooltip-content')) {
                return;
            }
            e.stopPropagation();
            infoButtons.forEach(otherBtn => {
                if (otherBtn !== btn) {
                    otherBtn.classList.remove('active');
                }
            });
            btn.classList.toggle('active');
        });
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.score-info')) {
            infoButtons.forEach(btn => {
                btn.classList.remove('active');
            });
        }
    });
}

// Preview Original Uploaded Resume Functions
function previewOriginalUploadedFile() {
    const file = fileInput.files[0] || currentPreviewFile;
    if (!file) {
        showNotification('No uploaded file found to preview', 'warning');
        return;
    }
    const modal = document.getElementById('originalResumePreviewModal');
    const previewContent = document.getElementById('originalResumePreviewContent');
    if (!modal || !previewContent) return;
    
    previewContent.innerHTML = '<div class="preview-loading"><i class="fas fa-spinner fa-pulse"></i><span>Loading preview...</span></div>';
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    
    try {
        const fileType = file.type;
        const fileExtension = file.name.split('.').pop().toLowerCase();
        
        if (fileType === 'application/pdf' || fileExtension === 'pdf') {
            const fileUrl = URL.createObjectURL(file);
            previewContent.innerHTML = `
                <iframe src="${fileUrl}" style="width:100%; height:550px; border:none; border-radius:8px;"></iframe>
            `;
        } else if (fileType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' || fileExtension === 'docx') {
            previewContent.innerHTML = `
                <div style="text-align: center; padding: 60px 40px; color: var(--text-primary);">
                    <i class="fas fa-file-word" style="font-size: 80px; color: #2b5797; margin-bottom: 20px; display: block;"></i>
                    <h4 style="margin-bottom: 10px;">${escapeHtml(file.name)}</h4>
                    <p style="color: var(--text-secondary);">Direct browser preview is not available for DOCX files. The file was successfully uploaded and processed by the system.</p>
                </div>
            `;
        } else {
            const reader = new FileReader();
            reader.onload = function(e) {
                const text = e.target.result;
                const previewText = text.substring(0, 5000);
                previewContent.innerHTML = `
                    <pre style="white-space: pre-wrap; font-family: monospace; font-size: 13px; margin: 0; padding: 16px; background: var(--bg-surface-alt); border-radius: 8px; color: var(--text-primary);">${escapeHtml(previewText)}${text.length > 5000 ? '\n\n... (file truncated)' : ''}</pre>
                `;
            };
            reader.readAsText(file.slice(0, 5000));
        }
    } catch (error) {
        console.error('Original preview error:', error);
        previewContent.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-primary);"><i class="fas fa-exclamation-triangle" style="font-size: 48px; color: var(--danger); margin-bottom: 16px; display: block;"></i><span>Could not preview this file.</span></div>`;
    }
}

function closeOriginalResumePreview() {
    const modal = document.getElementById('originalResumePreviewModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'hidden'; // Keep body scroll locked for results page
    }
}

function setupOriginalResumePreview() {
    const previewInputResumeBtn = document.getElementById('previewInputResumeBtn');
    if (previewInputResumeBtn) {
        previewInputResumeBtn.addEventListener('click', previewOriginalUploadedFile);
    }
    const originalResumePreviewCloseBtn = document.getElementById('originalResumePreviewCloseBtn');
    if (originalResumePreviewCloseBtn) {
        originalResumePreviewCloseBtn.addEventListener('click', closeOriginalResumePreview);
    }
    const originalResumePreviewCancelBtn = document.getElementById('originalResumePreviewCancelBtn');
    if (originalResumePreviewCancelBtn) {
        originalResumePreviewCancelBtn.addEventListener('click', closeOriginalResumePreview);
    }
    const originalResumePreviewModal = document.getElementById('originalResumePreviewModal');
    if (originalResumePreviewModal) {
        originalResumePreviewModal.addEventListener('click', (e) => {
            if (e.target === originalResumePreviewModal) closeOriginalResumePreview();
        });
    }
    
    // Toggle custom role input field in the skill modal
    const includeBestSuitedRoleCheckbox = document.getElementById('includeBestSuitedRoleCheckbox');
    if (includeBestSuitedRoleCheckbox) {
        includeBestSuitedRoleCheckbox.addEventListener('change', () => {
            const wrapper = document.getElementById('customModalRoleWrapper');
            if (wrapper) {
                if (includeBestSuitedRoleCheckbox.checked) {
                    wrapper.style.display = 'block';
                } else {
                    wrapper.style.display = 'none';
                    const input = document.getElementById('customModalRoleInput');
                    if (input) input.value = '';
                }
            }
        });
    }
}

// Initialize
initTheme();
setupFileSelection();
setupUploadArea();
setupPreviewModal();
setupRoleSelector();
setupTooltips();
setupSkillModal();
setupOriginalResumePreview();

// Store batch results globally
let batchResults = [];
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
let _editableProfile    = null;   // cloned profile for Live Edit mode

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

    // Live Edit button
    const editBtn = document.getElementById('skillEditBtn');
    if (editBtn) {
        editBtn.addEventListener('click', () => {
            openLiveEditModal();
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
        const header = scoreCard.querySelector('.card-header');
        if (header) {
            header.after(roleLabel);
        } else {
            scoreCard.insertBefore(roleLabel, scoreCard.firstChild);
        }
    }

    const cardSelect = document.getElementById('cardJobRoleSelect');
    if (cardSelect && jobRole) {
        cardSelect.value = jobRole;
    }
    
    const scoreStatus = document.getElementById('scoreStatus');
    if (scoreStatus) {
        if (fitScore >= 80) {
            scoreStatus.textContent = 'Excellent Match';
            scoreStatus.className = 'score-status clickable-verdict status-excellent';
        } else if (fitScore >= 60) {
            scoreStatus.textContent = 'Good Potential';
            scoreStatus.className = 'score-status clickable-verdict status-good';
        } else {
            scoreStatus.textContent = 'Room for Growth';
            scoreStatus.className = 'score-status clickable-verdict status-low';
        }
    }

    const fitScoreReasonText = document.getElementById('fitScoreReasonText');
    if (fitScoreReasonText) {
        const recommendationReason = resumeData.recommendation_reason || '';
        if (recommendationReason) {
            fitScoreReasonText.textContent = recommendationReason;
        } else {
            if (fitScore >= 80) {
                fitScoreReasonText.textContent = "The candidate represents an excellent match for this position based on key strengths, relevant experience, and role alignment.";
            } else if (fitScore >= 60) {
                fitScoreReasonText.textContent = "The candidate has good potential for this position, with solid foundation skills though there are minor areas of growth or alignment gaps.";
            } else {
                fitScoreReasonText.textContent = "The candidate requires significant skill development, certifications, or additional work experience to be fully suited for this position.";
            }
        }
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
            qualityVerdict.className = `quality-verdict clickable-verdict ${qualityVerdictText.toLowerCase().replace(' ', '-')}`;
        }
        
        const qualityVerdictReasonList = document.getElementById('qualityVerdictReasonList');
        if (qualityVerdictReasonList) {
            const observations = resumeData.quality_observations || [];
            qualityVerdictReasonList.innerHTML = '';
            if (observations.length > 0) {
                observations.forEach(obs => {
                    const li = document.createElement('li');
                    li.innerHTML = `<i class="fas fa-info-circle"></i> ${obs}`;
                    qualityVerdictReasonList.appendChild(li);
                });
            } else {
                const li = document.createElement('li');
                li.innerHTML = `<i class="fas fa-check-circle"></i> No quality concerns detected. The resume structure is professional.`;
                qualityVerdictReasonList.appendChild(li);
            }
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
            const cardSelect = document.getElementById('cardJobRoleSelect');
            
            select.innerHTML = '';
            if (cardSelect) cardSelect.innerHTML = '';
            
            (data.roles || []).forEach(role => {
                const opt1 = document.createElement('option');
                opt1.value = role;
                opt1.textContent = role;
                select.appendChild(opt1);
                
                if (cardSelect) {
                    const opt2 = document.createElement('option');
                    opt2.value = role;
                    opt2.textContent = role;
                    cardSelect.appendChild(opt2);
                }
            });
            
            if (cardSelect) {
                const optCustom = document.createElement('option');
                optCustom.value = '__custom__';
                optCustom.textContent = 'Custom Role...';
                cardSelect.appendChild(optCustom);
            }
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

    const cardSelect = document.getElementById('cardJobRoleSelect');
    if (cardSelect) {
        cardSelect.addEventListener('change', (e) => {
            const val = e.target.value;
            const customRoleWrapper = document.getElementById('cardCustomRoleWrapper');
            if (customRoleWrapper) {
                if (val === '__custom__') {
                    customRoleWrapper.style.display = 'block';
                    const input = document.getElementById('cardCustomRoleInput');
                    if (input) input.focus();
                } else {
                    customRoleWrapper.style.display = 'none';
                    // Auto-recalculate if it's a predefined role and no JD is added yet
                    const jdWrapper = document.getElementById('cardJdTextareaWrapper');
                    if (jdWrapper && jdWrapper.style.display === 'none') {
                        recalculateRoleFit(val);
                    }
                }
            }
        });
    }

    // Collapsible JD toggle button
    const cardJdToggleBtn = document.getElementById('cardJdToggleBtn');
    const cardJdWrapper = document.getElementById('cardJdTextareaWrapper');
    if (cardJdToggleBtn && cardJdWrapper) {
        cardJdToggleBtn.addEventListener('click', () => {
            const isHidden = cardJdWrapper.style.display === 'none';
            cardJdWrapper.style.display = isHidden ? 'block' : 'none';
            cardJdToggleBtn.innerHTML = isHidden 
                ? '<i class="fas fa-minus"></i> Remove Job Description' 
                : '<i class="fas fa-plus"></i> Add Job Description';
            cardJdToggleBtn.classList.toggle('active', isHidden);
            if (isHidden) {
                const textarea = document.getElementById('cardJdTextarea');
                if (textarea) textarea.focus();
            } else {
                const textarea = document.getElementById('cardJdTextarea');
                if (textarea) textarea.value = '';
            }
        });
    }

    // Check fit score button click listener
    const cardCheckFitBtn = document.getElementById('cardCheckFitBtn');
    if (cardCheckFitBtn) {
        cardCheckFitBtn.addEventListener('click', () => {
            let targetRole = '';
            const val = cardSelect?.value;
            if (val === '__custom__') {
                targetRole = document.getElementById('cardCustomRoleInput')?.value?.trim() || '';
            } else {
                targetRole = val || '';
            }
            
            if (!targetRole) {
                showNotification('Please specify a job role', 'warning');
                return;
            }
            
            recalculateRoleFit(targetRole);
        });
    }
}

async function recalculateRoleFit(newRole) {
    if (!_skillModalResponse) return;
    
    const scoreCircle = document.getElementById('scoreCircle');
    const scoreValue = document.querySelector('.score-value');
    if (scoreValue) scoreValue.textContent = '...';
    
    try {
        const API_URL = getApiUrl();
        const response = await fetch(`${API_URL}/recalculate-fit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                structured_data: _skillModalResponse.data,
                job_role: newRole,
                extracted_text: _skillModalResponse.extracted_text || '',
                job_description: document.getElementById('jobDescriptionInput')?.value || ''
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                _skillModalResponse.fit_score = result.fit_score;
                _skillModalResponse.data.fit_score = result.fit_score;
                _skillModalResponse.skill_gap = result.skill_gap;
                _skillModalResponse.job_role = newRole;
                _skillModalResponse.data.job_role = newRole;
                
                updateScoreCircle(result.fit_score);
                
                const scoreStatus = document.getElementById('scoreStatus');
                if (scoreStatus) {
                    if (result.fit_score >= 80) {
                        scoreStatus.textContent = 'Excellent Match';
                        scoreStatus.className = 'score-status clickable-verdict status-excellent';
                    } else if (result.fit_score >= 60) {
                        scoreStatus.textContent = 'Good Potential';
                        scoreStatus.className = 'score-status clickable-verdict status-good';
                    } else {
                        scoreStatus.textContent = 'Room for Growth';
                        scoreStatus.className = 'score-status clickable-verdict status-low';
                    }
                }
                
                const fitScoreReasonText = document.getElementById('fitScoreReasonText');
                if (fitScoreReasonText) {
                    const recommendationReason = _skillModalResponse.data.recommendation_reason || '';
                    if (recommendationReason) {
                        fitScoreReasonText.textContent = recommendationReason;
                    } else {
                        if (result.fit_score >= 80) {
                            fitScoreReasonText.textContent = `The candidate represents an excellent match for the position of ${newRole} based on key strengths, relevant experience, and role alignment.`;
                        } else if (result.fit_score >= 60) {
                            fitScoreReasonText.textContent = `The candidate has good potential for the position of ${newRole}, with solid foundation skills though there are minor areas of growth or alignment gaps.`;
                        } else {
                            fitScoreReasonText.textContent = `The candidate requires significant skill development, certifications, or additional work experience to be fully suited for the position of ${newRole}.`;
                        }
                    }
                }
                
                const scoreCard = document.getElementById('scoreCard');
                const roleLabel = scoreCard?.querySelector('.score-role-label');
                if (roleLabel) {
                    roleLabel.innerHTML = `<i class="fas fa-crosshairs"></i> ${newRole}`;
                }
                
                if (result.skill_gap) {
                    displaySkillGapPanel(result.skill_gap, newRole);
                }
            }
        } else {
            if (scoreValue) scoreValue.textContent = _skillModalResponse.fit_score || 0;
        }
    } catch (err) {
        console.error('Error recalculating role fit:', err);
        if (scoreValue) scoreValue.textContent = _skillModalResponse.fit_score || 0;
    }
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
    const tooltipContainers = document.querySelectorAll('.score-info, .verdict-wrapper');
    tooltipContainers.forEach(container => {
        const trigger = container.classList.contains('score-info') ? container : container.querySelector('.clickable-verdict');
        
        if (trigger) {
            trigger.addEventListener('click', (e) => {
                if (e.target.closest('.tooltip-content')) {
                    return;
                }
                e.stopPropagation();
                
                tooltipContainers.forEach(otherContainer => {
                    if (otherContainer !== container) {
                        otherContainer.classList.remove('active');
                    }
                });
                container.classList.toggle('active');
            });
        }
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.score-info, .verdict-wrapper')) {
            tooltipContainers.forEach(container => {
                container.classList.remove('active');
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

// ─────────────────────────────────────────────────────────────
// LIVE EDIT MODE FUNCTIONALITY
// ─────────────────────────────────────────────────────────────

function openLiveEditModal() {
    if (!_skillModalData) {
        showNotification('No resume analysis data found to edit', 'error');
        return;
    }
    
    // Deep clone original data
    _editableProfile = JSON.parse(JSON.stringify(_skillModalData));
    
    // Defensive normalization of dynamic sub-lists
    if (!_editableProfile.skill_proficiency) {
        if (_editableProfile.skills) {
            _editableProfile.skill_proficiency = _editableProfile.skills.slice(0, 12).map(s => ({ skill: s, percentage: 80 }));
        } else {
            _editableProfile.skill_proficiency = [];
        }
    } else if (!Array.isArray(_editableProfile.skill_proficiency)) {
        _editableProfile.skill_proficiency = [_editableProfile.skill_proficiency];
    }
    
    // Align with skill modal selections
    if (_selectedSkills && _selectedSkills.length > 0) {
        _editableProfile.skill_proficiency = JSON.parse(JSON.stringify(_selectedSkills));
    }
    
    // Normalize Experience List
    if (_editableProfile.latest_3_experiences) {
        if (!Array.isArray(_editableProfile.latest_3_experiences)) {
            _editableProfile.latest_3_experiences = [_editableProfile.latest_3_experiences];
        }
        _editableProfile.latest_3_experiences = _editableProfile.latest_3_experiences.map(exp => {
            if (exp && typeof exp === 'object') {
                return {
                    role: exp.role || exp.title || '',
                    company: exp.company || '',
                    duration: exp.duration || '',
                    responsibilities: Array.isArray(exp.responsibilities) ? exp.responsibilities : [exp.responsibilities || ''],
                    technologies: Array.isArray(exp.technologies) ? exp.technologies : (exp.technologies ? [exp.technologies] : [])
                };
            }
            return { role: String(exp || ''), company: '', duration: '', responsibilities: [], technologies: [] };
        });
    } else {
        _editableProfile.latest_3_experiences = [];
    }

    // Normalize Projects List
    if (_editableProfile.projects) {
        if (!Array.isArray(_editableProfile.projects)) {
            _editableProfile.projects = [_editableProfile.projects];
        }
        _editableProfile.projects = _editableProfile.projects.map(p => {
            if (p && typeof p === 'object') {
                return {
                    name: p.name || p.title || '',
                    description: p.description || p.desc || ''
                };
            } else if (typeof p === 'string') {
                const idxColon = p.indexOf(':');
                if (idxColon > 0) {
                    return {
                        name: p.slice(0, idxColon).trim(),
                        description: p.slice(idxColon + 1).trim()
                    };
                }
                return { name: p.trim(), description: '' };
            }
            return { name: '', description: '' };
        });
    } else {
        _editableProfile.projects = [];
    }

    // Normalize Education List
    if (_editableProfile.education) {
        if (!Array.isArray(_editableProfile.education)) {
            _editableProfile.education = [_editableProfile.education];
        }
        _editableProfile.education = _editableProfile.education.map(e => {
            if (e && typeof e === 'object') {
                return {
                    degree: e.degree || '',
                    institution: e.institution || e.university || '',
                    year: e.year || e.duration || ''
                };
            }
            return { degree: String(e || ''), institution: '', year: '' };
        });
    } else {
        _editableProfile.education = [];
    }

    // Normalize Certifications List (convert dict objects to clean display strings)
    if (_editableProfile.certifications) {
        if (!Array.isArray(_editableProfile.certifications)) {
            _editableProfile.certifications = [_editableProfile.certifications];
        }
        _editableProfile.certifications = _editableProfile.certifications.map(c => {
            if (c && typeof c === 'object') {
                const cName = c.name || c.title || c.certification_name || '';
                const cOrg = c.organization || c.authority || c.issuer || c.org || '';
                const cYear = c.year || c.date || '';
                let val = cName;
                if (cOrg) val += ` from ${cOrg}`;
                if (cYear) val += ` (${cYear})`;
                return val.trim();
            }
            return String(c || '');
        }).filter(Boolean);
    } else {
        _editableProfile.certifications = [];
    }
    
    // Populate simple inputs
    document.getElementById('editName').value = _editableProfile.name || '';
    
    const customRoleInput = document.getElementById('customModalRoleInput');
    const customRoleVal = customRoleInput ? customRoleInput.value.trim() : '';
    const resolvedRole = customRoleVal || _editableProfile.custom_role || _editableProfile.job_role || _editableProfile.recommended_role || _editableProfile.current_role || 'Professional';
    document.getElementById('editTitle').value = resolvedRole;
    
    document.getElementById('editEmail').value = _editableProfile.email || '';
    document.getElementById('editPhone').value = _editableProfile.phone || '';
    document.getElementById('editLocation').value = _editableProfile.location || '';
    document.getElementById('editLinkedIn').value = _editableProfile.linkedin || '';
    document.getElementById('editSummary').value = _editableProfile.professional_summary || '';
    
    // Fit score elements
    const includeFitScore = document.getElementById('includeFitScoreCheckbox')?.checked || false;
    const fitScore = _editableProfile.fit_score !== undefined ? _editableProfile.fit_score : 85;
    document.getElementById('editIncludeFitScore').checked = includeFitScore;
    document.getElementById('editFitScore').value = fitScore;
    document.getElementById('editFitScoreVal').textContent = fitScore + '%';
    
    // Render all subcards
    renderEditSkills();
    renderEditExperience();
    renderEditProjects();
    renderEditEducation();
    renderEditCertifications();
    
    // Render visual live preview
    renderLivePreview();
    
    // Transition modals
    closeSkillModal();
    document.getElementById('liveEditModal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeLiveEditModal() {
    document.getElementById('liveEditModal').style.display = 'none';
    document.body.style.overflow = 'auto';
    document.getElementById('skillModal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function renderEditSkills() {
    const container = document.getElementById('editSkillsContainer');
    if (!container) return;
    container.innerHTML = '';
    
    const list = _editableProfile.skill_proficiency || [];
    list.forEach((sp, idx) => {
        const row = document.createElement('div');
        row.className = 'edit-row skill-row';
        row.innerHTML = `
            <input type="text" class="edit-skill-name" value="${escapeHtml(sp.skill || '')}" placeholder="Skill Name">
            <input type="range" class="edit-skill-pct-slider" min="10" max="100" value="${sp.percentage || 80}">
            <span class="edit-skill-pct-val">${sp.percentage || 80}%</span>
            <button type="button" class="btn-delete-item" aria-label="Delete skill"><i class="fas fa-trash-alt"></i></button>
        `;
        
        row.querySelector('.edit-skill-name').addEventListener('input', (e) => {
            _editableProfile.skill_proficiency[idx].skill = e.target.value;
            renderLivePreview();
        });
        
        const slider = row.querySelector('.edit-skill-pct-slider');
        const label = row.querySelector('.edit-skill-pct-val');
        slider.addEventListener('input', (e) => {
            const val = parseInt(e.target.value, 10);
            _editableProfile.skill_proficiency[idx].percentage = val;
            label.textContent = val + '%';
            renderLivePreview();
        });
        
        row.querySelector('.btn-delete-item').addEventListener('click', () => {
            _editableProfile.skill_proficiency.splice(idx, 1);
            renderEditSkills();
            renderLivePreview();
        });
        
        container.appendChild(row);
    });
    
    if (list.length === 0) {
        container.innerHTML = '<span class="preview-empty">No skills listed. Click Add Skill to build list.</span>';
    }
}

function renderEditExperience() {
    const container = document.getElementById('editExpContainer');
    if (!container) return;
    container.innerHTML = '';
    
    const list = _editableProfile.latest_3_experiences || [];
    list.forEach((exp, idx) => {
        const card = document.createElement('div');
        card.className = 'edit-item-subcard';
        
        const respText = Array.isArray(exp.responsibilities) ? exp.responsibilities.join(' ') : exp.responsibilities || '';
        const techsText = Array.isArray(exp.technologies) ? exp.technologies.join(', ') : exp.technologies || '';
        
        card.innerHTML = `
            <div class="subcard-header">
                <h4>Experience #${idx + 1}</h4>
                <button type="button" class="btn-delete-item"><i class="fas fa-trash-alt"></i> Remove</button>
            </div>
            <div class="input-group-row">
                <div class="input-field">
                    <label>Company</label>
                    <input type="text" class="edit-exp-company" value="${escapeHtml(exp.company || '')}">
                </div>
                <div class="input-field">
                    <label>Role</label>
                    <input type="text" class="edit-exp-role" value="${escapeHtml(exp.role || '')}">
                </div>
            </div>
            <div class="input-group-row">
                <div class="input-field">
                    <label>Duration</label>
                    <input type="text" class="edit-exp-duration" value="${escapeHtml(exp.duration || '')}">
                </div>
                <div class="input-field">
                    <label>Tools & Techs (comma separated)</label>
                    <input type="text" class="edit-exp-techs" value="${escapeHtml(techsText)}">
                </div>
            </div>
            <div class="input-field full-width">
                <label>Description / Responsibilities</label>
                <textarea class="edit-exp-desc" rows="3">${escapeHtml(respText)}</textarea>
            </div>
        `;
        
        card.querySelector('.edit-exp-company').addEventListener('input', (e) => {
            _editableProfile.latest_3_experiences[idx].company = e.target.value;
            renderLivePreview();
        });
        card.querySelector('.edit-exp-role').addEventListener('input', (e) => {
            _editableProfile.latest_3_experiences[idx].role = e.target.value;
            renderLivePreview();
        });
        card.querySelector('.edit-exp-duration').addEventListener('input', (e) => {
            _editableProfile.latest_3_experiences[idx].duration = e.target.value;
            renderLivePreview();
        });
        card.querySelector('.edit-exp-techs').addEventListener('input', (e) => {
            const items = e.target.value.split(',').map(t => t.trim()).filter(Boolean);
            _editableProfile.latest_3_experiences[idx].technologies = items;
            renderLivePreview();
        });
        card.querySelector('.edit-exp-desc').addEventListener('input', (e) => {
            _editableProfile.latest_3_experiences[idx].responsibilities = [e.target.value];
            renderLivePreview();
        });
        card.querySelector('.btn-delete-item').addEventListener('click', () => {
            _editableProfile.latest_3_experiences.splice(idx, 1);
            renderEditExperience();
            renderLivePreview();
        });
        
        container.appendChild(card);
    });
    
    if (list.length === 0) {
        container.innerHTML = '<span class="preview-empty">No experience listed. Click Add Experience.</span>';
    }
}

function renderEditProjects() {
    const container = document.getElementById('editProjContainer');
    if (!container) return;
    container.innerHTML = '';
    
    const list = _editableProfile.projects || [];
    list.forEach((proj, idx) => {
        let name = '';
        let desc = '';
        if (typeof proj === 'object') {
            name = proj.name || proj.title || '';
            desc = proj.description || '';
        } else {
            const idxColon = proj.indexOf(':');
            if (idxColon > 0) {
                name = proj.slice(0, idxColon).trim();
                desc = proj.slice(idxColon + 1).trim();
            } else {
                name = proj;
            }
        }
        
        const card = document.createElement('div');
        card.className = 'edit-item-subcard';
        card.innerHTML = `
            <div class="subcard-header">
                <h4>Project #${idx + 1}</h4>
                <button type="button" class="btn-delete-item"><i class="fas fa-trash-alt"></i> Remove</button>
            </div>
            <div class="input-field full-width">
                <label>Project Name</label>
                <input type="text" class="edit-proj-name" value="${escapeHtml(name)}">
            </div>
            <div class="input-field full-width">
                <label>Project Description</label>
                <textarea class="edit-proj-desc" rows="2">${escapeHtml(desc)}</textarea>
            </div>
        `;
        
        card.querySelector('.edit-proj-name').addEventListener('input', (e) => {
            if (typeof _editableProfile.projects[idx] !== 'object') {
                _editableProfile.projects[idx] = { name: '', description: '' };
            }
            _editableProfile.projects[idx].name = e.target.value;
            renderLivePreview();
        });
        
        card.querySelector('.edit-proj-desc').addEventListener('input', (e) => {
            if (typeof _editableProfile.projects[idx] !== 'object') {
                _editableProfile.projects[idx] = { name: '', description: '' };
            }
            _editableProfile.projects[idx].description = e.target.value;
            renderLivePreview();
        });
        
        card.querySelector('.btn-delete-item').addEventListener('click', () => {
            _editableProfile.projects.splice(idx, 1);
            renderEditProjects();
            renderLivePreview();
        });
        
        container.appendChild(card);
    });
    
    if (list.length === 0) {
        container.innerHTML = '<span class="preview-empty">No projects listed. Click Add Project.</span>';
    }
}

function renderEditEducation() {
    const container = document.getElementById('editEduContainer');
    if (!container) return;
    container.innerHTML = '';
    
    const list = _editableProfile.education || [];
    list.forEach((edu, idx) => {
        const card = document.createElement('div');
        card.className = 'edit-item-subcard';
        card.innerHTML = `
            <div class="subcard-header">
                <h4>Education Entry #${idx + 1}</h4>
                <button type="button" class="btn-delete-item"><i class="fas fa-trash-alt"></i> Remove</button>
            </div>
            <div class="input-group-row">
                <div class="input-field">
                    <label>Degree</label>
                    <input type="text" class="edit-edu-degree" value="${escapeHtml(edu.degree || '')}">
                </div>
                <div class="input-field">
                    <label>Institution</label>
                    <input type="text" class="edit-edu-inst" value="${escapeHtml(edu.institution || '')}">
                </div>
            </div>
            <div class="input-field">
                <label>Year / Duration</label>
                <input type="text" class="edit-edu-year" value="${escapeHtml(edu.year || '')}">
            </div>
        `;
        
        card.querySelector('.edit-edu-degree').addEventListener('input', (e) => {
            _editableProfile.education[idx].degree = e.target.value;
            renderLivePreview();
        });
        card.querySelector('.edit-edu-inst').addEventListener('input', (e) => {
            _editableProfile.education[idx].institution = e.target.value;
            renderLivePreview();
        });
        card.querySelector('.edit-edu-year').addEventListener('input', (e) => {
            _editableProfile.education[idx].year = e.target.value;
            renderLivePreview();
        });
        card.querySelector('.btn-delete-item').addEventListener('click', () => {
            _editableProfile.education.splice(idx, 1);
            renderEditEducation();
            renderLivePreview();
        });
        
        container.appendChild(card);
    });
    
    if (list.length === 0) {
        container.innerHTML = '<span class="preview-empty">No education listed. Click Add Education.</span>';
    }
}

function renderEditCertifications() {
    const container = document.getElementById('editCertContainer');
    if (!container) return;
    container.innerHTML = '';
    
    const list = _editableProfile.certifications || [];
    list.forEach((cert, idx) => {
        const row = document.createElement('div');
        row.className = 'edit-row cert-row';
        row.innerHTML = `
            <input type="text" class="edit-cert-name" value="${escapeHtml(cert || '')}" placeholder="Certification Name / Details" style="flex:1; padding:8px 10px; font-size:13px; border:1px solid var(--border); border-radius:var(--radius-sm); background:var(--bg-page); color:var(--text-primary);">
            <button type="button" class="btn-delete-item" aria-label="Delete certification"><i class="fas fa-trash-alt"></i></button>
        `;
        
        row.querySelector('.edit-cert-name').addEventListener('input', (e) => {
            _editableProfile.certifications[idx] = e.target.value;
            renderLivePreview();
        });
        
        row.querySelector('.btn-delete-item').addEventListener('click', () => {
            _editableProfile.certifications.splice(idx, 1);
            renderEditCertifications();
            renderLivePreview();
        });
        
        container.appendChild(row);
    });
    
    if (list.length === 0) {
        container.innerHTML = '<span class="preview-empty">No certifications listed. Click Add Certification.</span>';
    }
}

function renderLivePreview() {
    const previewContainer = document.getElementById('resumeReportPreview');
    if (!previewContainer) return;

    const data = _editableProfile;
    if (!data) return;

    // Name and simple details
    const nameVal = document.getElementById('editName').value.trim() || data.name || 'Candidate Name';
    const name = nameVal.toUpperCase();
    
    // Fit score details
    const includeFitScore = document.getElementById('editIncludeFitScore')?.checked || false;
    const fitScore = parseInt(document.getElementById('editFitScore').value, 10);
    
    let scoreColor = '#2ecc71';
    if (fitScore < 60) scoreColor = '#e74c3c';
    else if (fitScore < 80) scoreColor = '#f1c40f';

    // Skills preview list
    const skills = data.skill_proficiency || [];
    let skillsHtml = '';
    skills.slice(0, 12).forEach(sp => {
        const skillName = sp.skill || '';
        const pct = sp.percentage || 80;
        skillsHtml += `
            <div class="preview-skill-item">
                <div class="preview-skill-header">
                    <span class="preview-skill-name">${escapeHtml(skillName)}</span>
                    <span class="preview-skill-pct">${pct}%</span>
                </div>
                <div class="preview-skill-bar-bg">
                    <div class="preview-skill-bar-fill" style="width: ${pct}%"></div>
                </div>
            </div>
        `;
    });

    // Education preview list
    const education = data.education || [];
    let eduHtml = '';
    education.slice(0, 4).forEach(edu => {
        const degree = edu.degree || 'Degree';
        const inst = edu.institution || 'Institution';
        const year = edu.year || '';
        eduHtml += `
            <div class="preview-edu-item">
                <div class="preview-edu-degree">${escapeHtml(degree)}</div>
                <div class="preview-edu-inst">${escapeHtml(inst)} ${year ? `(${escapeHtml(year)})` : ''}</div>
            </div>
        `;
    });

    // Contact preview fields
    const phone = document.getElementById('editPhone').value.trim();
    const email = document.getElementById('editEmail').value.trim();
    const location = document.getElementById('editLocation').value.trim();
    const linkedin = document.getElementById('editLinkedIn').value.trim();

    // Summary text
    const summary = document.getElementById('editSummary').value.trim();

    // Experience list
    const experiences = data.latest_3_experiences || [];
    let expHtml = '';
    experiences.slice(0, 3).forEach(exp => {
        const role = exp.role || 'Role';
        const company = exp.company || 'Company';
        const duration = exp.duration || 'Duration';
        const respText = Array.isArray(exp.responsibilities) ? exp.responsibilities.join(' ') : exp.responsibilities || '';
        
        let techs = exp.technologies || [];
        if (typeof techs === 'string') {
            techs = techs.split(',').map(t => t.trim()).filter(Boolean);
        }
        const techsText = techs.slice(0, 4).join(' • ');

        expHtml += `
            <div class="preview-exp-item">
                <div class="preview-exp-header">
                    <div>
                        <div class="preview-exp-role">${escapeHtml(role)}</div>
                        <div class="preview-exp-company">${escapeHtml(company)}</div>
                    </div>
                    <div class="preview-exp-duration">${escapeHtml(duration)}</div>
                </div>
                <div class="preview-exp-desc">${escapeHtml(respText)}</div>
                ${techsText ? `
                <div class="preview-exp-tech">
                    <span class="preview-tech-label">Tools & Techs:</span>
                    <span class="preview-tech-list">${escapeHtml(techsText)}</span>
                </div>` : ''}
            </div>
        `;
    });

    // Certifications preview
    const certs = data.certifications || [];
    let certsHtml = '';
    certs.slice(0, 4).forEach(cert => {
        if (!cert) return;
        certsHtml += `
            <div class="preview-bullet-item">
                <span class="preview-bullet"></span>
                <span class="preview-bullet-text">${escapeHtml(cert)}</span>
            </div>
        `;
    });

    // Projects preview
    const projects = data.projects || [];
    let projectsHtml = '';
    projects.slice(0, 4).forEach(p => {
        let pText = '';
        if (typeof p === 'object') {
            const pName = p.name || p.title || '';
            const pDesc = p.description || '';
            pText = pName ? `${pName}: ${pDesc}` : pDesc;
        } else {
            pText = p || '';
        }
        if (!pText) return;
        projectsHtml += `
            <div class="preview-bullet-item">
                <span class="preview-bullet"></span>
                <span class="preview-bullet-text">${escapeHtml(pText)}</span>
            </div>
        `;
    });

    // Avatar
    let avatarHtml = '';
    if (data.profile_image_base64) {
        avatarHtml = `<img src="data:image/png;base64,${data.profile_image_base64}" alt="${escapeHtml(name)}" class="preview-avatar-image">`;
    } else {
        const initials = name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase() || 'C';
        avatarHtml = `<div class="preview-avatar-initials">${initials}</div>`;
    }

    const customRole = document.getElementById('editTitle').value.trim() || 'Professional';

    previewContainer.innerHTML = `
        <div class="preview-header">
            <div class="preview-avatar-container">
                ${avatarHtml}
            </div>
            <div class="preview-header-text">
                <div class="preview-name">${escapeHtml(name)}</div>
                <div class="preview-title">${escapeHtml(customRole)}</div>
            </div>
            ${includeFitScore ? `
            <div class="preview-fit-score-badge" style="background-color: ${scoreColor}">
                <div class="preview-fit-val">${fitScore}</div>
                <div class="preview-fit-lbl">/100</div>
            </div>
            ` : ''}
        </div>
        <div class="preview-body">
            <div class="preview-col-left">
                <div class="preview-section-title">
                    <span class="preview-title-icon"><i class="fas fa-code"></i></span>
                    TECHNICAL SKILLS
                </div>
                <div class="preview-skills-list">
                    ${skillsHtml || '<div class="preview-empty">No skills listed</div>'}
                </div>

                <div class="preview-divider"></div>

                <div class="preview-section-title">
                    <span class="preview-title-icon"><i class="fas fa-graduation-cap"></i></span>
                    EDUCATION
                </div>
                <div class="preview-edu-list">
                    ${eduHtml || '<div class="preview-empty">No education listed</div>'}
                </div>

                <div class="preview-divider"></div>

                <div class="preview-section-title">
                    <span class="preview-title-icon"><i class="fas fa-address-book"></i></span>
                    CONTACT
                </div>
                <div class="preview-contact-list">
                    ${phone ? `
                    <div class="preview-contact-item">
                        <span class="preview-contact-icon"><i class="fas fa-phone-alt"></i></span>
                        <div>
                            <div class="preview-contact-lbl">Phone</div>
                            <div class="preview-contact-val">${escapeHtml(phone)}</div>
                        </div>
                    </div>` : ''}
                    ${location ? `
                    <div class="preview-contact-item">
                        <span class="preview-contact-icon"><i class="fas fa-map-marker-alt"></i></span>
                        <div>
                            <div class="preview-contact-lbl">Location</div>
                            <div class="preview-contact-val">${escapeHtml(location)}</div>
                        </div>
                    </div>` : ''}
                    ${email ? `
                    <div class="preview-contact-item">
                        <span class="preview-contact-icon"><i class="fas fa-envelope"></i></span>
                        <div>
                            <div class="preview-contact-lbl">Email</div>
                            <div class="preview-contact-val">${escapeHtml(email)}</div>
                        </div>
                    </div>` : ''}
                    ${linkedin ? `
                    <div class="preview-contact-item">
                        <span class="preview-contact-icon"><i class="fab fa-linkedin-in"></i></span>
                        <div>
                            <div class="preview-contact-lbl">LinkedIn</div>
                            <div class="preview-contact-val">${escapeHtml(linkedin)}</div>
                        </div>
                    </div>` : ''}
                </div>
            </div>
            <div class="preview-col-divider"></div>
            <div class="preview-col-right">
                <div class="preview-section-title">
                    <span class="preview-title-icon"><i class="fas fa-user"></i></span>
                    SUMMARY
                </div>
                <div class="preview-summary-text">
                    ${escapeHtml(summary) || 'No summary available.'}
                </div>

                <div class="preview-section-title" style="margin-top: 20px;">
                    <span class="preview-title-icon"><i class="fas fa-briefcase"></i></span>
                    PROFESSIONAL EXPERIENCE
                </div>
                <div class="preview-exp-list">
                    ${expHtml || '<div class="preview-empty">No experience listed</div>'}
                </div>

                ${certsHtml ? `
                <div class="preview-section-title" style="margin-top: 20px;">
                    <span class="preview-title-icon"><i class="fas fa-certificate"></i></span>
                    CERTIFICATIONS
                </div>
                <div class="preview-certs-grid">
                    ${certsHtml}
                </div>` : ''}

                ${projectsHtml ? `
                <div class="preview-section-title" style="margin-top: 20px;">
                    <span class="preview-title-icon"><i class="fas fa-trophy"></i></span>
                    PROJECTS
                </div>
                <div class="preview-projects-grid">
                    ${projectsHtml}
                </div>` : ''}
            </div>
        </div>
        <div class="preview-watermark">TALENTLENS AI REPORT</div>
    `;
}

function setupLiveEditModal() {
    const closeBtn = document.getElementById('liveEditCloseBtn');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeLiveEditModal);
    }
    
    const cancelBtn = document.getElementById('liveEditCancelBtn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', closeLiveEditModal);
    }
    
    const saveBtn = document.getElementById('liveEditSaveBtn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveLiveEditChanges);
    }
    
    // Sliders & Simple Inputs event bindings
    const nameInput = document.getElementById('editName');
    if (nameInput) {
        nameInput.addEventListener('input', (e) => {
            if (_editableProfile) _editableProfile.name = e.target.value;
            renderLivePreview();
        });
    }
    
    const titleInput = document.getElementById('editTitle');
    if (titleInput) {
        titleInput.addEventListener('input', (e) => {
            if (_editableProfile) {
                _editableProfile.custom_role = e.target.value;
                _editableProfile.current_role = e.target.value;
            }
            renderLivePreview();
        });
    }
    
    const emailInput = document.getElementById('editEmail');
    if (emailInput) {
        emailInput.addEventListener('input', (e) => {
            if (_editableProfile) _editableProfile.email = e.target.value;
            renderLivePreview();
        });
    }
    
    const phoneInput = document.getElementById('editPhone');
    if (phoneInput) {
        phoneInput.addEventListener('input', (e) => {
            if (_editableProfile) _editableProfile.phone = e.target.value;
            renderLivePreview();
        });
    }
    
    const locInput = document.getElementById('editLocation');
    if (locInput) {
        locInput.addEventListener('input', (e) => {
            if (_editableProfile) _editableProfile.location = e.target.value;
            renderLivePreview();
        });
    }
    
    const liInput = document.getElementById('editLinkedIn');
    if (liInput) {
        liInput.addEventListener('input', (e) => {
            if (_editableProfile) _editableProfile.linkedin = e.target.value;
            renderLivePreview();
        });
    }
    
    const summaryInput = document.getElementById('editSummary');
    if (summaryInput) {
        summaryInput.addEventListener('input', (e) => {
            if (_editableProfile) _editableProfile.professional_summary = e.target.value;
            renderLivePreview();
        });
    }
    
    const fitScoreSlider = document.getElementById('editFitScore');
    const fitScoreVal = document.getElementById('editFitScoreVal');
    if (fitScoreSlider) {
        fitScoreSlider.addEventListener('input', (e) => {
            const val = parseInt(e.target.value, 10);
            if (_editableProfile) _editableProfile.fit_score = val;
            if (fitScoreVal) fitScoreVal.textContent = val + '%';
            renderLivePreview();
        });
    }
    
    const fitScoreCheckbox = document.getElementById('editIncludeFitScore');
    if (fitScoreCheckbox) {
        fitScoreCheckbox.addEventListener('change', () => {
            renderLivePreview();
        });
    }
    
    // Add Item click listeners
    const addSkillBtn = document.getElementById('addEditSkillBtn');
    if (addSkillBtn) {
        addSkillBtn.addEventListener('click', () => {
            if (!_editableProfile.skill_proficiency) _editableProfile.skill_proficiency = [];
            _editableProfile.skill_proficiency.push({ skill: 'New Skill', percentage: 80 });
            renderEditSkills();
            renderLivePreview();
        });
    }
    
    const addExpBtn = document.getElementById('addEditExpBtn');
    if (addExpBtn) {
        addExpBtn.addEventListener('click', () => {
            if (!_editableProfile.latest_3_experiences) _editableProfile.latest_3_experiences = [];
            _editableProfile.latest_3_experiences.push({
                role: 'Role Name',
                company: 'Company Name',
                duration: 'Duration',
                responsibilities: ['Key responsibility description'],
                technologies: []
            });
            renderEditExperience();
            renderLivePreview();
        });
    }
    
    const addProjBtn = document.getElementById('addEditProjBtn');
    if (addProjBtn) {
        addProjBtn.addEventListener('click', () => {
            if (!_editableProfile.projects) _editableProfile.projects = [];
            _editableProfile.projects.push({ name: 'Project Name', description: 'Project Description' });
            renderEditProjects();
            renderLivePreview();
        });
    }
    
    const addEduBtn = document.getElementById('addEditEduBtn');
    if (addEduBtn) {
        addEduBtn.addEventListener('click', () => {
            if (!_editableProfile.education) _editableProfile.education = [];
            _editableProfile.education.push({ degree: 'Degree Name', institution: 'Institution', year: 'Year' });
            renderEditEducation();
            renderLivePreview();
        });
    }
    
    const addCertBtn = document.getElementById('addEditCertBtn');
    if (addCertBtn) {
        addCertBtn.addEventListener('click', () => {
            if (!_editableProfile.certifications) _editableProfile.certifications = [];
            _editableProfile.certifications.push('Certification Details');
            renderEditCertifications();
            renderLivePreview();
        });
    }
}

async function saveLiveEditChanges() {
    if (!_editableProfile) return;
    
    // Save standard form field values back to state
    _editableProfile.name = document.getElementById('editName').value.trim();
    
    const editedTitle = document.getElementById('editTitle').value.trim();
    _editableProfile.custom_role = editedTitle;
    _editableProfile.current_role = editedTitle;
    
    _editableProfile.email = document.getElementById('editEmail').value.trim();
    _editableProfile.phone = document.getElementById('editPhone').value.trim();
    _editableProfile.location = document.getElementById('editLocation').value.trim();
    _editableProfile.linkedin = document.getElementById('editLinkedIn').value.trim();
    _editableProfile.professional_summary = document.getElementById('editSummary').value.trim();
    
    const includeFitScore = document.getElementById('editIncludeFitScore').checked;
    const fitScore = parseInt(document.getElementById('editFitScore').value, 10);
    _editableProfile.fit_score = fitScore;
    
    // Synchronize experience and education raw lists for the backend GapAnalyzer
    _editableProfile.education_raw = (_editableProfile.education || []).map(edu => {
        return `${edu.degree || ''} at ${edu.institution || ''} ${edu.year || ''}`.trim();
    }).filter(Boolean);
    
    _editableProfile.experience_raw = (_editableProfile.latest_3_experiences || []).map(exp => {
        const respText = Array.isArray(exp.responsibilities) ? exp.responsibilities.join(' ') : exp.responsibilities || '';
        return `${exp.role || ''} at ${exp.company || ''} ${exp.duration || ''} - ${respText}`.trim();
    }).filter(Boolean);
    
    // Synchronize states of the original skills modal for visual consistency
    const fitScoreCheckbox = document.getElementById('includeFitScoreCheckbox');
    if (fitScoreCheckbox) fitScoreCheckbox.checked = includeFitScore;
    
    const bestRoleCheckbox = document.getElementById('includeBestSuitedRoleCheckbox');
    if (bestRoleCheckbox) bestRoleCheckbox.checked = true;
    
    const customRoleInput = document.getElementById('customModalRoleInput');
    if (customRoleInput) {
        customRoleInput.value = editedTitle;
        const wrapper = document.getElementById('customModalRoleWrapper');
        if (wrapper) wrapper.style.display = 'block';
    }
    
    // Save skill chips back to global selected array
    _selectedSkills = JSON.parse(JSON.stringify(_editableProfile.skill_proficiency));
    
    // Close live edit overlay
    document.getElementById('liveEditModal').style.display = 'none';
    document.body.style.overflow = 'auto';
    
    // Trigger image generation
    await triggerGenerateResumeFromEdit();
}

async function triggerGenerateResumeFromEdit() {
    loadingOverlay.style.display = 'flex';
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const statusText = document.getElementById('analysisStatusText');
    
    if (progressFill) progressFill.style.width = '75%';
    if (progressText) progressText.textContent = '75%';
    if (statusText) statusText.textContent = 'Generating final report from custom edits...';

    try {
        const includeFitScore = document.getElementById('editIncludeFitScore')?.checked || false;
        const editedTitle = document.getElementById('editTitle')?.value?.trim() || '';
        const API_URL = getApiUrl();
        
        const response = await fetch(`${API_URL}/api/generate-from-edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data: _editableProfile,
                selected_skills: _editableProfile.skill_proficiency,
                include_fit_score: includeFitScore,
                include_best_suited_role: true,
                job_role: selectedJobRole,
                custom_role: editedTitle
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

            // Update globals
            currentData             = _editableProfile;
            _skillModalData         = _editableProfile;
            currentImageUrl         = imageUrl;
            currentImageBlob        = imageBlob;
            currentPreviewImageUrl  = imageUrl;

            // Rerender skills modal details just in case it is opened again
            renderSkillModal();
            
            // Show preview modal
            showPreview(imageUrl, imageBlob);
            showNotification('Final resume report generated from custom edits', 'success');
        } else {
            throw new Error(genData.error || 'Image generation failed');
        }
    } catch (error) {
        loadingOverlay.style.display = 'none';
        showNotification(error.message || 'Error generating resume.', 'error');
        console.error('Generate error:', error);
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
setupLiveEditModal();

// Store batch results globally
let batchResults = [];
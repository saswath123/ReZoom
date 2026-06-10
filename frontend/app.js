// DOM Elements
const fileInput = document.getElementById('resumeFile');
const uploadArea = document.getElementById('uploadArea');
const uploadBtn = document.getElementById('uploadBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const resultsSection = document.getElementById('resultsSection');
const closeResults = document.getElementById('closeResults');
const themeToggle = document.getElementById('themeToggle');
const downloadBtn = document.getElementById('downloadBtn');

// State variables
let currentImageUrl = null;
let currentData = null;
let currentPreviewImageUrl = null;
let currentImageBlob = null;
let currentPreviewFile = null;

// Role selection state
let selectedJobRole = null;
let jobDescriptionText = null;

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeButton(savedTheme);
}

function updateThemeButton(theme) {
    const icon = themeToggle.querySelector('i');
    const text = themeToggle.querySelector('span');
    
    if (theme === 'light') {
        icon.className = 'fas fa-sun';
        text.textContent = 'Light';
    } else {
        icon.className = 'fas fa-moon';
        text.textContent = 'Dark';
    }
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
            previewBtn.style.display = 'none';
            closeFilePreview();
        }
    });
}

// Upload Area Interactions
function setupUploadArea() {
    uploadArea.addEventListener('click', (e) => {
        if (e.target.closest('#previewFileBtn') || e.target.closest('#uploadBtn')) {
            return;
        }
        fileInput.click();
    });
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            const event = new Event('change');
            fileInput.dispatchEvent(event);
        }
    });
    
    uploadBtn.addEventListener('click', (e) => {
        e.stopPropagation();
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
        <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
        <span>${message}</span>
    `;
    
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: var(--bg-card);
        color: var(--text-primary);
        padding: 15px 20px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        gap: 10px;
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
        box-shadow: var(--shadow-lg);
        border-left: 4px solid ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Single Resume Upload
async function uploadResume() {
    if (!fileInput.files[0]) {
        showNotification('Please select a file first!', 'warning');
        return;
    }
    
    const file = fileInput.files[0];
    
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    
    if (!validTypes.includes(file.type)) {
        showNotification('Please upload PDF or DOCX file only!', 'error');
        return;
    }
    
    if (file.size > 5 * 1024 * 1024) {
        showNotification('File size must be less than 5MB!', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('resume', file);
    
    // Attach role data if selected
    const activeRole = getActiveJobRole();
    const activeJD = document.getElementById('jobDescriptionText')?.value?.trim() || '';
    if (activeRole) {
        formData.append('job_role', activeRole);
        if (activeJD) formData.append('job_description', activeJD);
    }
    
    loadingOverlay.style.display = 'flex';
    // Update loading text with role
    const loadingP = loadingOverlay.querySelector('.loading-text p');
    if (loadingP && activeRole) {
        loadingP.textContent = `Analyzing resume against "${activeRole}" role requirements...`;
    } else if (loadingP) {
        loadingP.textContent = 'Extracting skills, experiences, and generating insights...';
    }
    
    try {
        const isProduction = window.location.hostname && 
                             !window.location.hostname.includes('localhost') && 
                             !window.location.hostname.includes('127.0.0.1') && 
                             !window.location.hostname.startsWith('192.168.') && 
                             window.location.protocol !== 'file:';
        const API_URL = isProduction 
            ? '/api' 
            : (window.location.hostname ? `http://${window.location.hostname}:5000/api` : 'http://127.0.0.1:5000/api');

const response = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentData = data.data;
            
            let imageUrl;
            let imageBlob;
            
            if (data.image_base64) {
                const byteCharacters = atob(data.image_base64);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                imageBlob = new Blob([byteArray], { type: 'image/png' });
                imageUrl = URL.createObjectURL(imageBlob);
                currentImageBlob = imageBlob;
            } else if (data.image_download_url) {
                imageUrl = `${API_URL}${data.image_download_url}`;
                const imgResponse = await fetch(imageUrl);
                imageBlob = await imgResponse.blob();
                currentImageBlob = imageBlob;
            }
            
            currentImageUrl = imageUrl;
            currentPreviewImageUrl = imageUrl;
            
            displayResults(data);
            
            loadingOverlay.style.display = 'none';
            resultsSection.style.display = 'block';
            document.body.style.overflow = 'hidden';
        } else {
            throw new Error(data.error || 'Failed to process resume');
        }
    } catch (error) {
        loadingOverlay.style.display = 'none';
        showNotification(error.message || 'Error processing resume. Please try again.', 'error');
        console.error('Upload error:', error);
    }
}

// Batch Upload Resumes
async function batchUploadResumes() {
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
    
    const batchProgress = document.getElementById('batchProgress');
    const progressCount = document.getElementById('progressCount');
    const progressFill = document.getElementById('batchProgressFill');
    
    batchProgress.style.display = 'block';
    progressCount.textContent = `0 / ${files.length}`;
    progressFill.style.width = '0%';
    
    batchResults = [];
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
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
            const isProduction = window.location.hostname && 
                                 !window.location.hostname.includes('localhost') && 
                                 !window.location.hostname.includes('127.0.0.1') && 
                                 !window.location.hostname.startsWith('192.168.') && 
                                 window.location.protocol !== 'file:';
            const API_URL = isProduction 
                ? '/api' 
                : (window.location.hostname ? `http://${window.location.hostname}:5000/api` : 'http://127.0.0.1:5000/api');
            const response = await fetch(`${API_URL}/upload`, {
                method: 'POST',
                body: formData
            });
            
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
        }
        
        const completed = i + 1;
        progressCount.textContent = `${completed} / ${files.length}`;
        progressFill.style.width = `${(completed / files.length) * 100}%`;
    }
    
    batchProgress.style.display = 'none';
    displayBatchResults(batchResults);
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
        card.className = 'batch-result-card';
        
        if (result.success) {
            card.innerHTML = `
                <div class="result-header">
                    <i class="fas fa-check-circle success-icon"></i>
                    <span class="result-name">${escapeHtml(result.candidateName || result.name)}</span>
                    <span class="fit-score-badge">${result.fitScore || 0}</span>
                </div>
                ${result.data && result.data.recommended_role ? `
                <div class="batch-role-badge">
                    <i class="fas fa-trophy"></i> ${escapeHtml(result.data.recommended_role)}
                </div>` : ''}
                <div class="result-preview">
                    <img src="data:image/png;base64,${result.image_base64}" alt="Preview" 
                         onclick="viewBatchResume(${index})">
                </div>
                <div class="result-actions">
                    <button class="view-btn" onclick="viewBatchResume(${index})">
                        <i class="fas fa-eye"></i> Preview
                    </button>
                    <button class="download-btn" onclick="downloadBatchResume(${index})">
                        <i class="fas fa-download"></i> Download
                    </button>
                </div>
            `;
        } else {
            card.innerHTML = `
                <div class="result-header">
                    <i class="fas fa-times-circle error-icon"></i>
                    <span class="result-name">${escapeHtml(result.name)}</span>
                </div>
                <div class="result-error">
                    <i class="fas fa-exclamation-triangle"></i>
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
        scoreStatus.style.color = '#10b981';
    } else if (fitScore >= 60) {
        scoreStatus.textContent = 'Good Potential';
        scoreStatus.style.color = '#f59e0b';
    } else {
        scoreStatus.textContent = 'Room for Growth';
        scoreStatus.style.color = '#ef4444';
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
            <h4>${exp.role || 'Role'}</h4>
            <div class="company">${exp.company || 'Company'}</div>
            <div class="duration">${exp.duration || 'Duration'}</div>
            <ul>
                ${(exp.responsibilities || []).map(resp => `<li>${resp}</li>`).join('')}
            </ul>
        `;
        experienceList.appendChild(expDiv);
    });
    
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
    educationInfo.innerHTML = `
        <h4>${education.degree || 'Degree'}</h4>
        <p>${education.institution || 'Institution'} | ${education.year || 'Year'}</p>
    `;
    
    // Resume Quality Score
    if (resumeData.resume_quality_score) {
        const qualityValue = document.getElementById('qualityValue');
        const qualityVerdict = document.getElementById('qualityVerdict');
        const qualityCircle = document.getElementById('qualityCircle');
        const qualityObservations = document.getElementById('qualityObservations');
        
        const qualityScore = resumeData.resume_quality_score;
        const qualityVerdictText = resumeData.resume_quality_verdict || 
            (qualityScore >= 90 ? "Excellent" : qualityScore >= 70 ? "Good" : qualityScore >= 50 ? "Average" : qualityScore >= 30 ? "Poor" : "Very Poor");
        
        if (qualityValue) qualityValue.textContent = qualityScore;
        if (qualityVerdict) {
            qualityVerdict.textContent = qualityVerdictText;
            qualityVerdict.className = `quality-verdict ${qualityVerdictText.toLowerCase().replace(' ', '-')}`;
        }
        
        if (qualityCircle) {
            const angle = (qualityScore / 100) * 360;
            qualityCircle.style.background = `conic-gradient(var(--accent-primary) 0deg ${angle}deg, var(--bg-hover) ${angle}deg 360deg)`;
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
                if (riskText.includes('No Gap')) riskElement.style.color = '#10b981';
                else if (riskText.includes('Minor')) riskElement.style.color = '#f59e0b';
                else if (riskText.includes('Moderate')) riskElement.style.color = '#f97316';
                else if (riskText.includes('Significant')) riskElement.style.color = '#ef4444';
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
        if (pct >= 70) fillEl.style.background = 'linear-gradient(90deg,#10b981,#059669)';
        else if (pct >= 40) fillEl.style.background = 'var(--gradient-1)';
        else fillEl.style.background = 'linear-gradient(90deg,#ef4444,#dc2626)';
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

// Update Score Circle
function updateScoreCircle(score) {
    const scoreCircle = document.getElementById('scoreCircle');
    const scoreValue = document.querySelector('.score-value');
    
    let currentScore = 0;
    const interval = setInterval(() => {
        if (currentScore >= score) {
            clearInterval(interval);
        } else {
            currentScore++;
            scoreValue.textContent = currentScore;
            const angle = (currentScore / 100) * 360;
            scoreCircle.style.background = `conic-gradient(var(--accent-primary) 0deg ${angle}deg, var(--bg-hover) ${angle}deg 360deg)`;
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
    if (currentImageBlob) {
        const url = URL.createObjectURL(currentImageBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `resume_report_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        showNotification('Resume downloaded successfully!', 'success');
        closePreview();
    } else if (currentPreviewImageUrl) {
        const link = document.createElement('a');
        link.href = currentPreviewImageUrl;
        link.download = `resume_report_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.png`;
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
    if (currentImageUrl) {
        if (currentImageBlob) {
            showPreview(currentImageUrl, currentImageBlob);
        } else {
            fetch(currentImageUrl)
                .then(res => res.blob())
                .then(blob => {
                    currentImageBlob = blob;
                    showPreview(currentImageUrl, blob);
                })
                .catch(err => {
                    showNotification('Error loading preview', 'error');
                });
        }
    } else {
        showNotification('No image available to download', 'error');
    }
}

function closeResultsHandler() {
    resultsSection.style.display = 'none';
    document.body.style.overflow = 'auto';
    currentData = null;
    currentImageUrl = null;
    currentImageBlob = null;
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

// Event Listeners
themeToggle.addEventListener('click', toggleTheme);
downloadBtn.addEventListener('click', downloadImage);
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

// Initialize
initTheme();
setupFileSelection();
setupUploadArea();
setupPreviewModal();
setupRoleSelector();

// Store batch results globally
let batchResults = [];
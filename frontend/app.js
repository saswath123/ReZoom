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

// Upload Area Interactions
function setupUploadArea() {
    uploadArea.addEventListener('click', () => fileInput.click());
    
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
            uploadResume();
        }
    });
    
    uploadBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });
    
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            uploadResume();
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

// Upload Resume Function
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
    
    loadingOverlay.style.display = 'flex';
    
    try {
        const response = await fetch('http://127.0.0.1:5000/upload', {
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
                imageUrl = `http://127.0.0.1:5000${data.image_download_url}`;
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

// Display Results
function displayResults(data) {
    const resumeData = data.data;  // ← MUST BE FIRST!
    const gapAnalysis = data.gap_analysis;
    const fitScore = resumeData.fit_score || 85;
    
    // ===== 1. UPDATE FIT SCORE =====
    updateScoreCircle(fitScore);
    
    const scoreStatus = document.getElementById('scoreStatus');
    if (fitScore >= 80) {
        scoreStatus.textContent = '🌟 Excellent Match';
        scoreStatus.style.color = '#10b981';
    } else if (fitScore >= 60) {
        scoreStatus.textContent = '👍 Good Potential';
        scoreStatus.style.color = '#f59e0b';
    } else {
        scoreStatus.textContent = '📈 Room for Growth';
        scoreStatus.style.color = '#ef4444';
    }
    
    // ===== 2. UPDATE STATS =====
    document.getElementById('strengthCount').textContent = (resumeData.strengths || []).length;
    document.getElementById('expYears').textContent = resumeData.total_experience_years || '0';
    
    // ===== 3. UPDATE SKILLS =====
    const skillsList = document.getElementById('skillsList');
    skillsList.innerHTML = '';
    (resumeData.skills || []).slice(0, 12).forEach(skill => {
        const skillTag = document.createElement('span');
        skillTag.className = 'skill-tag';
        skillTag.textContent = skill;
        skillsList.appendChild(skillTag);
    });
    
    // ===== 4. UPDATE STRENGTHS =====
    const strengthsList = document.getElementById('strengthsList');
    strengthsList.innerHTML = '';
    (resumeData.strengths || []).forEach(strength => {
        const li = document.createElement('li');
        li.textContent = strength;
        strengthsList.appendChild(li);
    });
    
    // ===== 5. UPDATE IMPROVEMENTS =====
    const improvementsList = document.getElementById('improvementsList');
    improvementsList.innerHTML = '';
    (resumeData.areas_for_improvement || []).forEach(improvement => {
        const li = document.createElement('li');
        li.textContent = improvement;
        improvementsList.appendChild(li);
    });
    
    // ===== 6. UPDATE CANDIDATE INFO =====
    document.getElementById('candidateName').textContent = resumeData.name || 'Candidate';
    document.getElementById('candidateRole').textContent = resumeData.current_role || 'Professional';
    document.getElementById('candidateLocation').textContent = resumeData.location || 'Not specified';
    document.getElementById('candidateEmail').textContent = resumeData.email || 'Not provided';
    
    // Add phone display
    const candidatePhone = document.getElementById('candidatePhone');
    if (candidatePhone) {
        candidatePhone.textContent = resumeData.phone || 'Not provided';
    }
    
    // ===== 7. UPDATE PROFESSIONAL SUMMARY =====
    document.getElementById('professionalSummary').textContent = resumeData.professional_summary || 'No summary available.';
    
    // ===== 8. UPDATE EXPERIENCE =====
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
    
    // ===== 9. UPDATE CERTIFICATIONS =====
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
    
    // ===== 10. UPDATE EDUCATION =====
    const education = resumeData.education || {};
    const educationInfo = document.getElementById('educationInfo');
    educationInfo.innerHTML = `
        <h4>${education.degree || 'Degree'}</h4>
        <p>${education.institution || 'Institution'} | ${education.year || 'Year'}</p>
    `;
    
    // ===== 11. UPDATE RESUME QUALITY SCORE (NEW) =====
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
        
        // Update quality circle
        if (qualityCircle) {
            const angle = (qualityScore / 100) * 360;
            qualityCircle.style.background = `conic-gradient(var(--accent-primary) 0deg ${angle}deg, var(--bg-hover) ${angle}deg 360deg)`;
        }
        
        // Display observations
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
    
    // ===== 12. UPDATE RED FLAGS (NEW) =====
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
    
    // ===== 13. UPDATE GAP ANALYSIS =====
    if (gapAnalysis) {
        const gapCard = document.getElementById('gapAnalysisCard');
        if (gapCard) {
            gapCard.style.display = 'block';
            document.getElementById('gapCurrentStatus').textContent = gapAnalysis.current_status || 'Unknown';
            
            // Education Gap
            const eduGap = gapAnalysis.education_to_employment_gap;
            const eduGapRow = document.getElementById('eduGapRow');
            if (eduGap && eduGapRow) {
                document.getElementById('eduGapText').innerHTML = `• ${eduGap.description}: ${eduGap.duration_years} Year${eduGap.duration_years !== 1 ? 's' : ''}`;
                eduGapRow.style.display = 'flex';
            } else if (eduGapRow) {
                eduGapRow.style.display = 'none';
            }
            
            // Employment Gaps
            const empGaps = gapAnalysis.employment_gaps || [];
            const empGapsList = document.getElementById('empGapsList');
            if (empGaps.length > 0 && empGapsList) {
                empGapsList.innerHTML = '';
                empGaps.forEach(gap => {
                    const div = document.createElement('div');
                    div.className = 'gap-item';
                    div.innerHTML = `• ${gap.description}: ${gap.duration_years} Year${gap.duration_years !== 1 ? 's' : ''}`;
                    empGapsList.appendChild(div);
                });
                document.getElementById('empGapsRow').style.display = 'block';
            } else {
                document.getElementById('empGapsRow').style.display = 'none';
            }
            
            // Career Breaks
            const careerBreaks = gapAnalysis.career_breaks || [];
            const careerBreaksList = document.getElementById('careerBreaksList');
            if (careerBreaks.length > 0 && careerBreaksList) {
                careerBreaksList.innerHTML = '';
                careerBreaks.forEach(breakItem => {
                    const div = document.createElement('div');
                    div.className = 'gap-item';
                    div.innerHTML = `• ${breakItem.description}: ${breakItem.duration_years} Year${breakItem.duration_years !== 1 ? 's' : ''}`;
                    careerBreaksList.appendChild(div);
                });
                document.getElementById('careerBreaksRow').style.display = 'block';
            } else {
                document.getElementById('careerBreaksRow').style.display = 'none';
            }
            
            // Current Gap
            const currentGap = gapAnalysis.current_employment_gap;
            const currentGapRow = document.getElementById('currentGapRow');
            if (currentGap && currentGapRow) {
                document.getElementById('currentGapText').innerHTML = `• ${currentGap.from_year} to ${currentGap.to_year}: ${currentGap.duration_years} Year${currentGap.duration_years !== 1 ? 's' : ''}`;
                currentGapRow.style.display = 'flex';
            } else if (currentGapRow) {
                currentGapRow.style.display = 'none';
            }
            
            // Total Gap
            const totalGap = gapAnalysis.total_gap_years || 0;
            document.getElementById('totalGap').textContent = `${totalGap} Year${totalGap !== 1 ? 's' : ''}`;
            
            // Risk Indicator
            const riskText = gapAnalysis.risk_indicator || '🟢 No Gap (0 Years)';
            const riskElement = document.getElementById('riskIndicator');
            if (riskElement) {
                riskElement.textContent = riskText;
                if (riskText.includes('🟢')) riskElement.style.color = '#10b981';
                else if (riskText.includes('🟡')) riskElement.style.color = '#f59e0b';
                else if (riskText.includes('🟠')) riskElement.style.color = '#f97316';
                else if (riskText.includes('🔴')) riskElement.style.color = '#ef4444';
            }
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

// Preview Modal Functions
function showPreview(imageUrl, imageBlob) {
    const modal = document.getElementById('previewModal');
    const previewImg = document.getElementById('previewImage');
    
    if (!modal || !previewImg) {
        console.error('Preview modal not found');
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

// Download Image (shows preview first)
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
                    console.error('Error fetching image:', err);
                    showNotification('Error loading preview', 'error');
                });
        }
    } else {
        showNotification('No image available to download', 'error');
    }
}

// Close Results
function closeResultsHandler() {
    resultsSection.style.display = 'none';
    document.body.style.overflow = 'auto';
    currentData = null;
    currentImageUrl = null;
    currentImageBlob = null;
    fileInput.value = '';
}

// Setup Preview Modal Event Listeners
function setupPreviewModal() {
    const previewCloseBtn = document.getElementById('previewCloseBtn');
    const previewCancelBtn = document.getElementById('previewCancelBtn');
    const previewDownloadBtn = document.getElementById('previewDownloadBtn');
    const modal = document.getElementById('previewModal');
    
    if (previewCloseBtn) {
        previewCloseBtn.addEventListener('click', closePreview);
    }
    
    if (previewCancelBtn) {
        previewCancelBtn.addEventListener('click', closePreview);
    }
    
    if (previewDownloadBtn) {
        previewDownloadBtn.addEventListener('click', downloadFromPreview);
    }
    
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
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && resultsSection.style.display === 'block') {
        closeResultsHandler();
    }
});

// Initialize
initTheme();
setupUploadArea();
setupPreviewModal();
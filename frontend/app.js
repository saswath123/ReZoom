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

// Upload Resume Function - COMPLETE VERSION
async function uploadResume() {
    if (!fileInput.files[0]) {
        showNotification('Please select a file first!', 'warning');
        return;
    }
    
    const file = fileInput.files[0];
    
    // Validate file type
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    
    if (!validTypes.includes(file.type)) {
        showNotification('Please upload PDF or DOCX file only!', 'error');
        return;
    }
    
    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
        showNotification('File size must be less than 5MB!', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('resume', file);
    
    // Show loading overlay
    loadingOverlay.style.display = 'flex';
    
    try {
        const response = await fetch('http://127.0.0.1:5000/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentData = data.data;
            currentImageUrl = `http://127.0.0.1:5000${data.image_download_url}`;
            
            // Display results
            displayResults(data);
            
            // Hide loading, show results
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

// Display Results in Dashboard
function displayResults(data) {
    const resumeData = data.data;
    const gapAnalysis = data.gap_analysis;
    const fitScore = resumeData.fit_score || 85;
    
    // Update fit score circle
    updateScoreCircle(fitScore);
    
    // Update score status
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
    
    // Update stats
    document.getElementById('strengthCount').textContent = (resumeData.strengths || []).length;
    document.getElementById('expYears').textContent = resumeData.total_experience_years || '0';
    
    // Update skills
    const skillsList = document.getElementById('skillsList');
    skillsList.innerHTML = '';
    (resumeData.skills || []).slice(0, 12).forEach(skill => {
        const skillTag = document.createElement('span');
        skillTag.className = 'skill-tag';
        skillTag.textContent = skill;
        skillsList.appendChild(skillTag);
    });
    
    // Update strengths
    const strengthsList = document.getElementById('strengthsList');
    strengthsList.innerHTML = '';
    (resumeData.strengths || ['Strong technical background', 'Excellent communication']).forEach(strength => {
        const li = document.createElement('li');
        li.textContent = strength;
        strengthsList.appendChild(li);
    });
    
    // Update improvements
    const improvementsList = document.getElementById('improvementsList');
    improvementsList.innerHTML = '';
    (resumeData.areas_for_improvement || ['Add more quantifiable achievements', 'Include relevant certifications']).forEach(improvement => {
        const li = document.createElement('li');
        li.textContent = improvement;
        improvementsList.appendChild(li);
    });
    
    // Update candidate info
    document.getElementById('candidateName').textContent = resumeData.name || 'Candidate';
    document.getElementById('candidateRole').textContent = resumeData.current_role || 'Professional';
    document.getElementById('candidateLocation').textContent = resumeData.location || 'Not specified';
    document.getElementById('candidateEmail').textContent = resumeData.email || 'Not provided';
    
    // Update avatar based on gender
    const gender = resumeData.gender || 'neutral';
    const avatarIcon = document.querySelector('.candidate-avatar i');
    if (gender === 'male') avatarIcon.className = 'fas fa-user-tie';
    else if (gender === 'female') avatarIcon.className = 'fas fa-user-circle';
    else avatarIcon.className = 'fas fa-user';
    
    // Update professional summary
    document.getElementById('professionalSummary').textContent = resumeData.professional_summary || 'No summary available.';
    
    // Update experience
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
    
    // Update certifications
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
    
    // Update education
    const education = resumeData.education || {};
    const educationInfo = document.getElementById('educationInfo');
    educationInfo.innerHTML = `
        <h4>${education.degree || 'Degree'}</h4>
        <p>${education.institution || 'Institution'} | ${education.year || 'Year'}</p>
    `;
    
    // Display Gap Analysis
    if (gapAnalysis) {
        const gapCard = document.getElementById('gapAnalysisCard');
        if (gapCard) {
            gapCard.style.display = 'block';
            
            document.getElementById('gapCurrentStatus').textContent = gapAnalysis.current_status || 'Unknown';
            
            const eduGap = gapAnalysis.education_to_employment_gap;
            const eduGapRow = document.getElementById('eduGapRow');
            if (eduGap && eduGapRow) {
                document.getElementById('eduGapText').innerHTML = `• ${eduGap.description}: ${eduGap.duration_years} Year${eduGap.duration_years !== 1 ? 's' : ''}`;
                eduGapRow.style.display = 'flex';
            } else if (eduGapRow) {
                eduGapRow.style.display = 'none';
            }
            
            const empGaps = gapAnalysis.employment_gaps || [];
            const empGapsRow = document.getElementById('empGapsRow');
            const empGapsList = document.getElementById('empGapsList');
            if (empGaps.length > 0 && empGapsList) {
                empGapsList.innerHTML = '';
                empGaps.forEach(gap => {
                    const div = document.createElement('div');
                    div.className = 'gap-item';
                    div.innerHTML = `• ${gap.description}: ${gap.duration_years} Year${gap.duration_years !== 1 ? 's' : ''}`;
                    empGapsList.appendChild(div);
                });
                if (empGapsRow) empGapsRow.style.display = 'block';
            } else if (empGapsRow) {
                empGapsRow.style.display = 'none';
            }
            
            const currentGap = gapAnalysis.current_employment_gap;
            const currentGapRow = document.getElementById('currentGapRow');
            if (currentGap && currentGapRow) {
                document.getElementById('currentGapText').innerHTML = `• ${currentGap.from_date} to ${currentGap.to_date}: ${currentGap.duration_years} Year${currentGap.duration_years !== 1 ? 's' : ''}`;
                currentGapRow.style.display = 'flex';
            } else if (currentGapRow) {
                currentGapRow.style.display = 'none';
            }
            
            const totalGap = gapAnalysis.total_gap_years || 0;
            document.getElementById('totalGap').textContent = `${totalGap} Year${totalGap !== 1 ? 's' : ''}`;
            
            const riskText = gapAnalysis.risk_indicator || '🟢 No Gap (0 Years)';
            const riskElement = document.getElementById('riskIndicator');
            if (riskElement) {
                riskElement.textContent = riskText;
                if (riskText.includes('🟢')) {
                    riskElement.style.color = '#10b981';
                } else if (riskText.includes('🟡')) {
                    riskElement.style.color = '#f59e0b';
                } else if (riskText.includes('🟠')) {
                    riskElement.style.color = '#f97316';
                } else if (riskText.includes('🔴')) {
                    riskElement.style.color = '#ef4444';
                }
            }
        }
    }
}

// Update Score Circle Animation
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

// Download Image Function
function downloadImage() {
    if (currentImageUrl) {
        const link = document.createElement('a');
        link.href = currentImageUrl;
        link.download = '';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showNotification('PNG image downloaded!', 'success');
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
    fileInput.value = '';
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Event Listeners
themeToggle.addEventListener('click', toggleTheme);
downloadBtn.addEventListener('click', downloadImage);
closeResults.addEventListener('click', closeResultsHandler);

// Initialize
initTheme();
setupUploadArea();

// Prevent body scroll when results are open
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && resultsSection.style.display === 'block') {
        closeResultsHandler();
    }
});
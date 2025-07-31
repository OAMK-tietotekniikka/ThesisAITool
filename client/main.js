// API Configuration
const API_BASE_URL = 'http://localhost:8000'; // Update with your API URL

// Global variables
let currentUser = null;
let authToken = null;
let currentThesisId = null;

// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    // Set current date
    const now = new Date();
    document.getElementById('currentDate').textContent = now.toLocaleDateString('en-US', { 
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' 
    });
    
    // Initialize event listeners
    initEventListeners();
    
    // Check if user is already logged in
    checkAuthStatus();
});

// Initialize all event listeners
function initEventListeners() {
    // Login form
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    
    // Upload thesis
    const uploadArea = document.getElementById('uploadForm');
    uploadArea.addEventListener('click', (e) => {
        // Don't trigger file dialog if clicking on a button
        if (e.target.tagName === 'BUTTON') {
            return;
        }
        const fileInput = document.getElementById('thesisFile');
        if (fileInput) {
            fileInput.click();  // Ensure the file input is clicked properly
        }
    });

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('border-indigo-500', 'bg-indigo-50');
    });
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('border-indigo-500', 'bg-indigo-50');
    });
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('border-indigo-500', 'bg-indigo-50');
        if (e.dataTransfer.files.length) {
            document.getElementById('thesisFile').files = e.dataTransfer.files;
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });
    
    document.getElementById('thesisFile').addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFileSelect(e.target.files[0]);
        }
    });
    
    // AI Feedback
    document.getElementById('requestFeedbackBtn').addEventListener('click', requestAIFeedback);
    
    // Supervisor Feedback
    document.getElementById('submitFeedbackBtn').addEventListener('click', submitSupervisorFeedback);
    document.getElementById('cancelFeedbackBtn').addEventListener('click', () => {
        showSection('reviewTheses');
    });
    
    // Admin functions
    document.getElementById('newRole').addEventListener('change', (e) => {
        if (e.target.value === 'student') {
            document.getElementById('supervisorField').classList.remove('hidden');
        } else {
            document.getElementById('supervisorField').classList.add('hidden');
        }
    });
    
    document.getElementById('confirmAddUser').addEventListener('click', addNewUser);
    
    // Assign supervisors
    document.getElementById('assignSupervisorBtn').addEventListener('click', assignSupervisor);
    
    // Toggle sidebar
    document.getElementById('toggleSidebar').addEventListener('click', toggleSidebar);
}

// Toggle sidebar collapse
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('content');
    
    sidebar.classList.toggle('collapsed');
    content.classList.toggle('expanded');
}

// Check if user is authenticated
function checkAuthStatus() {
    const token = localStorage.getItem('authToken');
    const sidebar = document.getElementById('sidebar');

    if (token) {
        authToken = token;
        sidebar.classList.remove('hidden')
        fetchCurrentUser();
    } else {
        sidebar.classList.add('hidden')
    }
}

// Handle login
async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    showLoading();
    
    try {
        const params = new URLSearchParams();
        params.append('username', username);
        params.append('password', password);
        params.append('grant_type', 'password');

        const response = await axios.post(`${API_BASE_URL}/token`, params, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });

        authToken = response.data.access_token;
        localStorage.setItem('authToken', authToken);
        
        await fetchCurrentUser();
        hideLoading();
    } catch (error) {
        hideLoading();
        document.getElementById('loginError').classList.remove('hidden');
        console.error('Login failed:', error);
    }

    checkAuthStatus();
}

// Fetch current user details
async function fetchCurrentUser() {
    try {
        const response = await axios.get(`${API_BASE_URL}/me`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        currentUser = response.data;
        updateUIForUserRole();
        
        // Hide login, show dashboard
        document.getElementById('loginSection').classList.add('hidden');
        document.getElementById('dashboardSection').classList.remove('hidden');
        
        // Load dashboard data
        loadDashboardData();
    } catch (error) {
        console.error('Failed to fetch user:', error);
        logout();
    }
}

// Update UI based on user role
function updateUIForUserRole() {
    // Set user info in sidebar
    document.getElementById('usernameDisplay').textContent = currentUser.full_name;
    document.getElementById('userRoleDisplay').textContent = currentUser.role.charAt(0).toUpperCase() + currentUser.role.slice(1);
    
    // Show/hide navigation based on role
    document.getElementById('studentNav').classList.add('hidden');
    document.getElementById('supervisorNav').classList.add('hidden');
    document.getElementById('adminNav').classList.add('hidden');
    
    document.getElementById('studentDashboard').classList.add('hidden');
    document.getElementById('supervisorDashboard').classList.add('hidden');
    document.getElementById('adminDashboard').classList.add('hidden');
    
    if (currentUser.role === 'student') {
        document.getElementById('studentNav').classList.remove('hidden');
        document.getElementById('studentDashboard').classList.remove('hidden');
    } else if (currentUser.role === 'supervisor') {
        document.getElementById('supervisorNav').classList.remove('hidden');
        document.getElementById('supervisorDashboard').classList.remove('hidden');
    } else if (currentUser.role === 'admin') {
        document.getElementById('adminNav').classList.remove('hidden');
        document.getElementById('adminDashboard').classList.remove('hidden');
    }
}

// Load dashboard data based on user role
async function loadDashboardData() {
    showLoading();
    
    try {
        if (currentUser.role === 'student') {
            await loadStudentDashboard();
        } else if (currentUser.role === 'supervisor') {
            await loadSupervisorDashboard();
        } else if (currentUser.role === 'admin') {
            await loadAdminDashboard();
        }
    } catch (error) {
        console.log('Require admin privileges.');
    }
    
    hideLoading();
}

// Load student dashboard data
async function loadStudentDashboard() {
    // Load theses count
    const thesesResponse = await axios.get(`${API_BASE_URL}/my-theses`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    const theses = thesesResponse.data;
    document.getElementById('thesesCount').textContent = theses.length;
    
    // Count approved theses
    const approvedCount = theses.filter(t => t.status === 'approved').length;
    document.getElementById('approvedTheses').textContent = approvedCount;
    
    // Count pending feedback
    const pendingCount = theses.filter(t => t.status === 'pending' || t.status === 'reviewed_by_ai').length;
    document.getElementById('pendingFeedback').textContent = pendingCount;
    
    // Load recent activity
    const activityList = document.getElementById('studentActivity');
    activityList.innerHTML = '';
    
    theses.slice(0, 5).forEach(thesis => {
        const activityItem = document.createElement('div');
        activityItem.className = 'flex items-start';
        activityItem.innerHTML = `
            <div class="flex-shrink-0 mt-1">
                <i class="fas fa-file-alt text-indigo-500"></i>
            </div>
            <div class="ml-3">
                <p class="text-sm font-medium text-gray-700">${thesis.filename}</p>
                <p class="text-xs text-gray-500">Uploaded on ${new Date(thesis.upload_date).toLocaleDateString()} - ${thesis.status.replace(/_/g, ' ')}</p>
            </div>
        `;
        activityList.appendChild(activityItem);
    });
    
    // Load supervisor info if available
    if (currentUser.supervisor_id) {
        const supervisorResponse = await axios.get(`${API_BASE_URL}/users`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const supervisor = supervisorResponse.data.find(u => u.username === currentUser.supervisor_id);
        if (supervisor) {
            const supervisorInfo = document.getElementById('supervisorInfo');
            supervisorInfo.innerHTML = `
                <div class="flex-shrink-0">
                    <i class="fas fa-user-tie text-2xl text-indigo-500"></i>
                </div>
                <div class="ml-4">
                    <h4 class="text-sm font-medium text-gray-800">${supervisor.full_name}</h4>
                    <p class="text-sm text-gray-500">${supervisor.email}</p>
                    <p class="text-xs text-indigo-600 mt-1">Your assigned supervisor</p>
                </div>
            `;
        }
    }
}

// Load supervisor dashboard data
async function loadSupervisorDashboard() {
    // Load assigned students count
    const studentsResponse = await axios.get(`${API_BASE_URL}/students`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    document.getElementById('studentCount').textContent = studentsResponse.data.length;
    
    // Load theses to review
    const thesesResponse = await axios.get(`${API_BASE_URL}/my-theses`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    const thesesToReview = thesesResponse.data.filter(t => t.status === 'reviewed_by_ai' || t.status === 'pending');
    document.getElementById('thesesToReview').textContent = thesesToReview.length;
    
    // Count completed reviews
    const completedReviews = thesesResponse.data.filter(t => t.status === 'reviewed_by_supervisor' || t.status === 'approved').length;
    document.getElementById('completedReviews').textContent = completedReviews;
    
    // Load recent student submissions
    const submissionsList = document.getElementById('studentSubmissions');
    submissionsList.innerHTML = '';
    
    thesesResponse.data.slice(0, 5).forEach(thesis => {
        const student = studentsResponse.data.find(s => s.id === thesis.student_id);
        const submissionItem = document.createElement('div');
        submissionItem.className = 'flex items-start';
        submissionItem.innerHTML = `
            <div class="flex-shrink-0 mt-1">
                <i class="fas fa-file-upload ${thesis.status === 'pending' ? 'text-yellow-500' : 'text-indigo-500'}"></i>
            </div>
            <div class="ml-3">
                <p class="text-sm font-medium text-gray-700">${thesis.filename}</p>
                <p class="text-xs text-gray-500">Submitted by ${student ? student.full_name : 'Unknown'} on ${new Date(thesis.upload_date).toLocaleDateString()}</p>
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusClass(thesis.status)} mt-1">
                    ${thesis.status.replace(/_/g, ' ')}
                </span>
            </div>
        `;
        submissionsList.appendChild(submissionItem);
    });
}

// Load admin dashboard data
async function loadAdminDashboard() {
    // Load users count
    const usersResponse = await axios.get(`${API_BASE_URL}/users`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    document.getElementById('totalUsers').textContent = usersResponse.data.length;
    
    // Count supervisors
    const supervisorCount = usersResponse.data.filter(u => u.role === 'supervisor').length;
    document.getElementById('supervisorCount').textContent = supervisorCount;
    
    // Load all theses count
    const thesesResponse = await axios.get(`${API_BASE_URL}/my-theses`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    document.getElementById('totalTheses').textContent = thesesResponse.data.length;
    
    // Load recent system activity
    const activityList = document.getElementById('systemActivity');
    activityList.innerHTML = '';
    
    // Mock activity - in a real app, you'd have actual activity data
    const mockActivities = [
        { action: 'New user registered', details: 'John Doe (student)', time: '2 minutes ago' },
        { action: 'Thesis uploaded', details: 'Research on AI by student123', time: '15 minutes ago' },
        { action: 'Feedback provided', details: 'By Dr. Smith on thesis #45', time: '1 hour ago' },
        { action: 'System update', details: 'Applied security patches', time: '3 hours ago' }
    ];
    
    mockActivities.forEach(activity => {
        const activityItem = document.createElement('div');
        activityItem.className = 'flex items-start';
        activityItem.innerHTML = `
            <div class="flex-shrink-0 mt-1">
                <i class="fas fa-circle-notch text-indigo-500 text-xs"></i>
            </div>
            <div class="ml-3">
                <p class="text-sm font-medium text-gray-700">${activity.action}</p>
                <p class="text-xs text-gray-500">${activity.details} • ${activity.time}</p>
            </div>
        `;
        activityList.appendChild(activityItem);
    });
}

// Show/hide sections
function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('[id$="Section"]').forEach(section => {
        section.classList.add('hidden');
    });
    
    // Show the requested section
    document.getElementById(`${sectionId}Section`).classList.remove('hidden');
    
    // Load data for the section if needed
    if (sectionId === 'myTheses') {
        loadMyTheses();
    } else if (sectionId === 'aiFeedback') {
        loadAIFeedback();
    } else if (sectionId === 'supervisorFeedback') {
        loadSupervisorFeedback();
    } else if (sectionId === 'assignedStudents') {
        loadAssignedStudents();
    } else if (sectionId === 'reviewTheses') {
        loadThesesToReview();
    } else if (sectionId === 'manageUsers') {
        loadAllUsers();
    } else if (sectionId === 'assignSupervisors') {
        loadAssignSupervisors();
    } else if (sectionId === 'allTheses') {
        loadAllTheses();
    }
}

// Handle file selection for thesis upload
function handleFileSelect(file) {
    const uploadArea = document.getElementById('uploadForm');
    const fileInput = document.getElementById('thesisFile');

    // Update the upload area content while keeping the file input intact
    const fileInputClone = fileInput.cloneNode(true);
    fileInputClone.files = fileInput.files;
    
    uploadArea.innerHTML = `
        <div class="flex items-center justify-center">
            <i class="fas fa-file-word text-indigo-500 text-2xl mr-3"></i>
            <div>
                <p class="text-sm font-medium text-gray-700">${file.name}</p>
                <p class="text-xs text-gray-500">${(file.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
        </div>
        <button type="button" onclick="uploadThesis()" class="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-sm">
            Upload Thesis
        </button>
    `;

    // Add the file input back to the upload area
    uploadArea.appendChild(fileInputClone);
}

// Upload thesis file
async function uploadThesis() {
    const fileInput = document.getElementById('thesisFile');
    if (!fileInput || !fileInput.files || !fileInput.files.length) {
        console.error('No file selected or file input not found');
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    showLoading();
    
    try {
        document.getElementById('uploadForm').classList.add('hidden');
        document.getElementById('uploadProgress').classList.remove('hidden');
        
        const response = await axios.post(`${API_BASE_URL}/upload-thesis`, formData, {
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'multipart/form-data'
            },
            onUploadProgress: progressEvent => {
                const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                document.getElementById('uploadBar').style.width = `${percentCompleted}%`;
                document.getElementById('uploadPercent').textContent = `${percentCompleted}%`;
            }
        });
        
        // Simulate processing delay
        setTimeout(() => {
            document.getElementById('uploadProgress').classList.add('hidden');
            document.getElementById('uploadSuccess').classList.remove('hidden');
            
            // Reset the upload area after successful upload
            const uploadArea = document.getElementById('uploadForm');
            uploadArea.innerHTML = `
                <i class="fas fa-cloud-upload-alt text-4xl text-indigo-500 mb-3"></i>
                <p class="text-lg font-medium text-gray-700">Drag & drop your thesis file here or click to browse</p>
                <p class="text-sm text-gray-500 mt-2">Supported formats: PDF, DOC, DOCX</p>
            `;
            uploadArea.classList.remove('hidden');
            
            // Create a new file input and add it to the upload area
            const newFileInput = document.createElement('input');
            newFileInput.type = 'file';
            newFileInput.id = 'thesisFile';
            newFileInput.className = 'hidden';
            newFileInput.accept = '.pdf,.doc,.docx';
            
            // Add event listener to the new file input
            newFileInput.addEventListener('change', (e) => {
                if (e.target.files.length) {
                    handleFileSelect(e.target.files[0]);
                }
            });
            
            uploadArea.appendChild(newFileInput);
            
            // Refresh my theses list
            loadMyTheses();
            
            hideLoading();
        }, 1500);
    } catch (error) {
        hideLoading();
        document.getElementById('uploadError').classList.remove('hidden');
        document.getElementById('uploadErrorMessage').textContent = error.response?.data?.detail || 'Failed to upload thesis';
        console.error('Upload failed:', error);
    }
}

// Upload another thesis - reset the form
function uploadAnotherThesis() {
    // Hide the success message
    document.getElementById('uploadSuccess').classList.add('hidden');
    
    // Reset the upload area
    const uploadArea = document.getElementById('uploadForm');
    uploadArea.innerHTML = `
        <i class="fas fa-cloud-upload-alt text-4xl text-indigo-500 mb-3"></i>
        <p class="text-lg font-medium text-gray-700">Drag & drop your thesis file here or click to browse</p>
        <p class="text-sm text-gray-500 mt-2">Supported formats: PDF, DOC, DOCX</p>
    `;
    uploadArea.classList.remove('hidden');
    
    // Create a new file input and add it to the upload area
    const newFileInput = document.createElement('input');
    newFileInput.type = 'file';
    newFileInput.id = 'thesisFile';
    newFileInput.className = 'hidden';
    newFileInput.accept = '.pdf,.doc,.docx';
    
    // Add event listener to the new file input
    newFileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFileSelect(e.target.files[0]);
        }
    });
    
    uploadArea.appendChild(newFileInput);
}

// Load student's theses
async function loadMyTheses() {
    showLoading();
    
    try {
        const response = await axios.get(`${API_BASE_URL}/my-theses`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const thesesList = document.getElementById('thesesList');
        thesesList.innerHTML = '';
        
        if (response.data.length === 0) {
            document.getElementById('noThesesMessage').classList.remove('hidden');
        } else {
            document.getElementById('noThesesMessage').classList.add('hidden');
            
            response.data.forEach(thesis => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-medium text-gray-900">${thesis.filename}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm text-gray-500">${new Date(thesis.upload_date).toLocaleDateString()}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusClass(thesis.status)}">
                            ${thesis.status.replace(/_/g, ' ')}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button onclick="viewThesis('${thesis.id}')" class="text-indigo-600 hover:text-indigo-900 mr-3">View</button>
                        ${thesis.status === 'pending' ? `<button onclick="deleteThesis('${thesis.id}')" class="text-red-600 hover:text-red-900">Delete</button>` : ''}
                    </td>
                `;
                thesesList.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Failed to load theses:', error);
    }
    
    hideLoading();
}

// View thesis details
async function viewThesis(thesisId) {
    showLoading();
    
    try {
        const response = await axios.get(`${API_BASE_URL}/theses/${thesisId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const thesis = response.data;
        document.getElementById('thesisModalTitle').textContent = thesis.filename;
        
        // Set basic info
        const basicInfo = document.getElementById('thesisBasicInfo');
        basicInfo.innerHTML = `
            <p><strong>Student:</strong> ${thesis.student_name || 'N/A'}</p>
            <p><strong>Upload Date:</strong> ${new Date(thesis.upload_date).toLocaleDateString()}</p>
            <p><strong>Status:</strong> <span class="${getStatusClass(thesis.status)}">${thesis.status.replace(/_/g, ' ')}</span></p>
            <p><strong>File Size:</strong> ${(thesis.file_size / 1024 / 1024).toFixed(2)} MB</p>
        `;
        
        // Set AI feedback if available
        const aiFeedback = document.getElementById('thesisAIFeedback');
        if (thesis.ai_feedback) {
            aiFeedback.innerHTML = thesis.ai_feedback;
        } else {
            aiFeedback.innerHTML = '<p>No AI feedback available yet.</p>';
        }
        
        // Set supervisor feedback if available
        const supervisorFeedback = document.getElementById('thesisSupervisorFeedback');
        if (thesis.supervisor_feedback) {
            supervisorFeedback.innerHTML = thesis.supervisor_feedback;
        } else {
            supervisorFeedback.innerHTML = '<p>No supervisor feedback available yet.</p>';
        }
        
        // Set document preview (simplified - in a real app you'd use a proper viewer)
        const docPreview = document.getElementById('thesisDocumentPreview');
        docPreview.innerHTML = `
            <div class="mt-2 flex items-center">
                <i class="fas fa-file-word text-4xl text-blue-500 mr-3"></i>
                <div>
                    <p class="text-sm font-medium">${thesis.filename}</p>
                    <p class="text-xs text-gray-500">${thesis.file_type.toUpperCase()} • ${(thesis.file_size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
            </div>
        `;
        
        currentThesisId = thesisId;
        showViewThesisModal();
    } catch (error) {
        console.error('Failed to load thesis:', error);
    }
    
    hideLoading();
}

// Delete thesis
async function deleteThesis(thesisId) {
    if (!confirm('Are you sure you want to delete this thesis? This action cannot be undone.')) return;
    
    showLoading();
    
    try {
        await axios.delete(`${API_BASE_URL}/theses/${thesisId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        // Refresh the list
        loadMyTheses();
    } catch (error) {
        console.error('Failed to delete thesis:', error);
        hideLoading();
        alert('Failed to delete thesis. Please try again.');
    }
}

// Load AI feedback section
async function loadAIFeedback() {
    showLoading();
    
    try {
        const response = await axios.get(`${API_BASE_URL}/my-theses`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const thesisSelect = document.getElementById('thesisSelect');
        thesisSelect.innerHTML = '<option value="">-- Select a thesis --</option>';
        
        if (response.data.length === 0) {
            // Show no theses message and hide the feedback form
            document.getElementById('noThesesForFeedback').classList.remove('hidden');
            document.getElementById('aiFeedbackContent').classList.add('hidden');
        } else {
            // Show feedback form and hide no theses message
            document.getElementById('noThesesForFeedback').classList.add('hidden');
            document.getElementById('aiFeedbackContent').classList.remove('hidden');
            
            response.data.forEach(thesis => {
                const option = document.createElement('option');
                option.value = thesis.id;
                option.textContent = thesis.filename;
                thesisSelect.appendChild(option);
            });
        }
        
        // Hide feedback results by default
        document.getElementById('feedbackResults').classList.add('hidden');
    } catch (error) {
        console.error('Failed to load theses for feedback:', error);
    }
    
    hideLoading();
}

// Request AI feedback - Completely rewritten
async function requestAIFeedback() {
    const thesisId = document.getElementById('thesisSelect').value;
    if (!thesisId) {
        alert('Please select a thesis first');
        return;
    }

    const selectedOption = document.getElementById('thesisSelect').selectedOptions[0];
    const thesisTitle = selectedOption.textContent;
    const customInstructions = "Please review this thesis and provide comprehensive feedback.";
    const selectedQuestions = [
        "Strengths?",
        "Areas for improvement?",
        "Methodology alignment?",
        "Reference formatting?",
        "Theoretical foundation?"
    ];

    // Show results section
    document.getElementById('feedbackResults').classList.remove('hidden');
    document.getElementById('feedbackThesisTitle').textContent = thesisTitle;
    document.getElementById('feedbackThesisDate').textContent = `Uploaded on ${new Date().toLocaleDateString()}`;
    document.getElementById('feedbackThesisStatus').textContent = 'AI Reviewed';

    const feedbackContainer = document.getElementById('feedbackContent');
    const statusBadge = document.getElementById('streamStatus');
    const requestFeedbackBtn = document.getElementById('requestFeedbackBtn');
    
    // Disable button and show loading
    requestFeedbackBtn.disabled = true;
    requestFeedbackBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Requesting...';
    statusBadge.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Generating...';
    feedbackContainer.innerHTML = '';

    try {
        const data = new URLSearchParams();
        data.append('custom_instructions', customInstructions);
        selectedQuestions.forEach((q, i) => data.append(`predefined_questions[${i}]`, q));

        const url = `${API_BASE_URL}/request-ai-feedback?thesis_id=${encodeURIComponent(thesisId)}`;
        const headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': `Bearer ${authToken}`
        };

        const response = await fetch(url, { 
            method: 'POST', 
            headers, 
            body: data.toString() 
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let accumulatedContent = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.trim() === '') continue;
                
                // Handle Server-Sent Events format
                if (line.startsWith('data: ')) {
                    const data = line.substring(6); // Remove 'data: ' prefix
                    if (data.trim() === '') continue;
                    
                    try {
                        // Parse the JSON data
                        const jsonData = JSON.parse(data);
                        
                        if (jsonData.type === 'content') {
                            accumulatedContent += jsonData.content;
                            // Convert accumulated markdown to HTML
                            const htmlContent = marked.parse(accumulatedContent);
                            // Sanitize HTML
                            const sanitizedHtml = DOMPurify ? DOMPurify.sanitize(htmlContent) : htmlContent;
                            feedbackContainer.innerHTML = sanitizedHtml;
                            feedbackContainer.scrollTop = feedbackContainer.scrollHeight;
                        } else if (jsonData.type === 'progress') {
                            statusBadge.innerHTML = `<i class="fas fa-spinner fa-spin mr-1"></i>${jsonData.content}`;
                        } else if (jsonData.type === 'error') {
                            throw new Error(jsonData.content);
                        } else if (jsonData.type === 'complete') {
                            // Stream completed
                            break;
                        }
                    } catch (e) {
                        if (e.message && e.message !== 'Unexpected end of JSON input') {
                            throw e; // Re-throw actual errors
                        }
                        // Ignore JSON parsing errors for incomplete chunks
                    }
                } else {
                    // Handle plain text (fallback)
                    accumulatedContent += line;
                    const htmlContent = marked.parse(accumulatedContent);
                    const sanitizedHtml = DOMPurify ? DOMPurify.sanitize(htmlContent) : htmlContent;
                    feedbackContainer.innerHTML = sanitizedHtml;
                    feedbackContainer.scrollTop = feedbackContainer.scrollHeight;
                }
            }
        }

        statusBadge.innerHTML = '<i class="fas fa-check-circle mr-1"></i>Complete';
        statusBadge.classList.remove('bg-yellow-100', 'text-yellow-800');
        statusBadge.classList.add('bg-green-100', 'text-green-800');

        // Save feedback
        const saveData = new URLSearchParams();
        saveData.append('feedback_content', accumulatedContent);
        await axios.post(`${API_BASE_URL}/save-ai-feedback?thesis_id=${thesisId}`, saveData, {
            headers: { 
                'Content-Type': 'application/x-www-form-urlencoded', 
                'Authorization': `Bearer ${authToken}` 
            }
        });

    } catch (error) {
        console.error('Failed to stream AI feedback:', error);
        statusBadge.innerHTML = `<i class="fas fa-exclamation-circle mr-1"></i>Error: ${error.message}`;
        statusBadge.classList.remove('bg-yellow-100', 'text-yellow-800');
        statusBadge.classList.add('bg-red-100', 'text-red-800');
        feedbackContainer.innerHTML = `<p class="text-red-600">Failed to generate feedback: ${error.message}</p>`;
    } finally {
        // Re-enable button
        requestFeedbackBtn.disabled = false;
        requestFeedbackBtn.innerHTML = '<i class="fas fa-robot mr-2" aria-hidden="true"></i> Request AI Feedback';
    }
}

// Request new feedback function
function requestNewFeedback() {
    // Hide current results and show the form again
    document.getElementById('feedbackResults').classList.add('hidden');
    document.getElementById('aiFeedbackContent').classList.remove('hidden');
    
    // Reset the thesis select
    document.getElementById('thesisSelect').value = '';
}

// Download feedback as PDF using html2pdf
function downloadFeedback() {
    const feedbackContent = document.getElementById('feedbackContent');
    const thesisTitle = document.getElementById('feedbackThesisTitle').textContent;
    const thesisDate = document.getElementById('feedbackThesisDate').textContent;

    // Get the current date and time
    const currentDate = new Date();
    const formattedDate = currentDate.toLocaleString();

    // Create a clean version of the feedback content for PDF
    const cleanContent = feedbackContent.cloneNode(true);
    
    // Add title and metadata to the feedback content
    const title = `<h1 style="text-align:center; padding-bottom: 20px; font-weight: bold; font-size:1.5rem; color: #1f2937;">Thesis AI Feedback Report</h1>`;
    const metadata = `
        <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #6366f1;">
            <h3 style="margin: 0 0 10px 0; color: #374151; font-size: 1.1rem;">Thesis Information</h3>
            <p style="margin: 5px 0; color: #6b7280;"><strong>Thesis:</strong> ${thesisTitle}</p>
            <p style="margin: 5px 0; color: #6b7280;"><strong>${thesisDate}</strong></p>
            <p style="margin: 5px 0; color: #6b7280;"><strong>Generated:</strong> ${formattedDate}</p>
        </div>
    `;
    const date = `<p style="text-align:right; font-size: 12px; color: #6b7280; margin-bottom: 20px;">Report generated on: ${formattedDate}</p>`;

    // Apply styling for better PDF formatting
    const contentWithTitleAndMetadata = title + metadata + date + cleanContent.outerHTML;

    // Generate PDF from HTML content
    html2pdf()
        .from(contentWithTitleAndMetadata)
        .set({
            margin: [20, 20, 20, 20], // Add padding around the content (top, right, bottom, left)
            filename: `ai_feedback_${thesisTitle.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`,
            html2canvas: { scale: 2 },  // Improve rendering quality
            jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
        })
        .save();   // Save the PDF
}

// Load supervisor feedback
async function loadSupervisorFeedback() {
    showLoading();
    
    try {
        const response = await axios.get(`${API_BASE_URL}/supervisor-feedback`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const feedbackList = document.getElementById('supervisorFeedbackList');
        feedbackList.innerHTML = '';
        
        if (response.data.length === 0) {
            document.getElementById('noSupervisorFeedback').classList.remove('hidden');
            document.getElementById('supervisorFeedbackList').classList.add('hidden');
        } else {
            document.getElementById('noSupervisorFeedback').classList.add('hidden');
            document.getElementById('supervisorFeedbackList').classList.remove('hidden');
            
            response.data.forEach(feedback => {
                const feedbackCard = document.createElement('div');
                feedbackCard.className = 'feedback-card bg-white rounded-lg shadow p-6';
                feedbackCard.innerHTML = `
                    <div class="flex justify-between items-start mb-2">
                        <h3 class="text-lg font-medium text-gray-800">${feedback.thesis_title}</h3>
                        <span class="text-xs text-gray-500">${new Date(feedback.feedback_date).toLocaleDateString()}</span>
                    </div>
                    <div class="prose max-w-none text-sm text-gray-600 mb-4">
                        ${feedback.feedback_text}
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-xs text-indigo-600">From: ${feedback.supervisor_name}</span>
                        <button onclick="viewThesis('${feedback.thesis_id}')" class="text-xs text-indigo-600 hover:text-indigo-800">
                            View Thesis
                        </button>
                    </div>
                `;
                feedbackList.appendChild(feedbackCard);
            });
        }
    } catch (error) {
        console.error('Failed to load supervisor feedback:', error);
    }
    
    hideLoading();
}

// Load assigned students (for supervisors)
async function loadAssignedStudents() {
    showLoading();
    
    try {
        const response = await axios.get(`${API_BASE_URL}/students`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const studentsList = document.getElementById('studentsList');
        studentsList.innerHTML = '';
        
        if (response.data.length === 0) {
            document.getElementById('noStudentsMessage').classList.remove('hidden');
        } else {
            document.getElementById('noStudentsMessage').classList.add('hidden');
            
            response.data.forEach(student => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="flex items-center">
                            <div class="flex-shrink-0 h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center">
                                <i class="fas fa-user text-indigo-500"></i>
                            </div>
                            <div class="ml-4">
                                <div class="text-sm font-medium text-gray-900">${student.full_name}</div>
                                <div class="text-sm text-gray-500">${student.username}</div>
                            </div>
                        </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm text-gray-500">${student.email}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm text-gray-500">${student.theses_count || 0}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm text-gray-500">${student.pending_reviews || 0}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button onclick="viewStudentTheses('${student.username}')" class="text-indigo-600 hover:text-indigo-900">View Theses</button>
                    </td>
                `;
                studentsList.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Failed to load assigned students:', error);
    }
    
    hideLoading();
}

// View student's theses (for supervisors)
async function viewStudentTheses(studentId) {
    // In a real app, this would show the theses for the selected student
    alert(`This would show theses for student ${studentId} in a real implementation`);
}

// Load theses to review (for supervisors)
async function loadThesesToReview() {
    showLoading();
    
    try {
const response = await axios.get(`${API_BASE_URL}/theses-to-review`, {
    headers: { 'Authorization': `Bearer ${authToken}` }
});

console.log("theses-to-review response:", response);  // Log the full response object

const thesesList = document.getElementById('thesesToReviewList');
thesesList.innerHTML = '';

if (response.data.length === 0) {
    document.getElementById('noThesesToReview').classList.remove('hidden');
} else {
    document.getElementById('noThesesToReview').classList.add('hidden');
    
    response.data.forEach(thesis => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">${thesis.student_name}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900">${thesis.filename}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-500">${new Date(thesis.upload_date).toLocaleDateString()}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusClass(thesis.status)}">
                    ${thesis.status.replace(/_/g, ' ')}
                </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button onclick="provideFeedback('${thesis.id}')" class="text-indigo-600 hover:text-indigo-900">Provide Feedback</button>
            </td>
        `;
        thesesList.appendChild(row);
    });
}


    } catch (error) {
        console.error('Failed to load theses to review:', error);
    }
    
    hideLoading();
}

// Provide feedback for a thesis
async function provideFeedback(thesisId) {
    showLoading();
    
    try {
        const response = await axios.get(`${API_BASE_URL}/theses/${thesisId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const thesis = response.data;
        currentThesisId = thesisId;
        
        // Set thesis details
        const thesisDetails = document.getElementById('thesisDetails');
        thesisDetails.innerHTML = `
            <p><strong>Student:</strong> ${thesis.student_name}</p>
            <p><strong>Thesis Title:</strong> ${thesis.filename}</p>
            <p><strong>Upload Date:</strong> ${new Date(thesis.upload_date).toLocaleDateString()}</p>
            <p><strong>Status:</strong> <span class="${getStatusClass(thesis.status)}">${thesis.status.replace(/_/g, ' ')}</span></p>
        `;
        
        // Set AI feedback preview if available
        const aiFeedback = document.getElementById('aiFeedbackPreview');
        if (thesis.ai_feedback) {
            aiFeedback.innerHTML = thesis.ai_feedback.length > 200 
                ? thesis.ai_feedback.substring(0, 200) + '...' 
                : thesis.ai_feedback;
        } else {
            aiFeedback.innerHTML = 'No AI feedback available for this thesis.';
        }
        
        // Clear previous feedback text
        document.getElementById('supervisorFeedbackText').value = '';
        
        // Show the form
        document.getElementById('feedbackFormContainer').classList.remove('hidden');
        document.getElementById('noThesisSelected').classList.add('hidden');
        
        // Show the section
        showSection('provideFeedback');
    } catch (error) {
        console.error('Failed to load thesis for feedback:', error);
    }
    
    hideLoading();
}

// Submit supervisor feedback
async function submitSupervisorFeedback() {
    const feedbackText = document.getElementById('supervisorFeedbackText').value.trim();
    if (!feedbackText) {
        alert('Please enter your feedback before submitting.');
        return;
    }
    
    showLoading();
    
    try {
        await axios.post(`${API_BASE_URL}/submit-feedback`, {
            thesis_id: currentThesisId,
            feedback_text: feedbackText
        }, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        // Go back to review theses section
        showSection('reviewTheses');
        loadThesesToReview();
    } catch (error) {
        console.error('Failed to submit feedback:', error);
        hideLoading();
        alert('Failed to submit feedback. Please try again.');
    }
}

// Load all users (for admin)
async function loadAllUsers() {
    showLoading();
    
    try {
        const response = await axios.get(`${API_BASE_URL}/users`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const usersList = document.getElementById('usersList');
        usersList.innerHTML = '';
        
        response.data.forEach(user => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900">${user.username}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900">${user.full_name}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-500">${user.email}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getRoleClass(user.role)}">
                        ${user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                        Active
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button onclick="editUser('${user.username}')" class="text-indigo-600 hover:text-indigo-900 mr-3">Edit</button>
                    <button onclick="deleteUser('${user.username}')" class="text-red-600 hover:text-red-900">Delete</button>
                </td>
            `;
            usersList.appendChild(row);
        });
    } catch (error) {
        console.error('Failed to load users:', error);
    }
    
    hideLoading();
}

// Show add user modal
function showAddUserModal() {
    document.getElementById('addUserModal').classList.remove('hidden');
}

// Hide add user modal
function hideAddUserModal() {
    document.getElementById('addUserModal').classList.add('hidden');
}

// Add new user (admin)
async function addNewUser() {
    const username = document.getElementById('newUsername').value.trim();
    const email = document.getElementById('newEmail').value.trim();
    const fullName = document.getElementById('newFullName').value.trim();
    const password = document.getElementById('newPassword').value;
    const role = document.getElementById('newRole').value;
    const supervisor = role === 'student' ? document.getElementById('newSupervisor').value : null;
    
    if (!username || !email || !fullName || !password) {
        alert('Please fill in all required fields.');
        return;
    }
    
    showLoading();
    
    try {
        console.log("ttttttttttt", );
        const params = new URLSearchParams();
        params.append('username', username);
        params.append('email', email);
        params.append('full_name', fullName);
        params.append('password', password);
        params.append('role', role);

        if (role === 'student') {
            params.append('supervisor_id', supervisor);
        }

        const response = await axios.post(`${API_BASE_URL}/register`, params, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': `Bearer ${authToken}`
            }
        });

        // Handle success (e.g., show a success message, redirect, etc.)
        console.log('User registered successfully:', response.data);

        // Refresh users list
        loadAllUsers();
        hideAddUserModal();
        
        // Clear form
        document.getElementById('addUserForm').reset();
    } catch (error) {
        let errorMessage = 'An unexpected error occurred during registration.';

        // Check if the error response contains the message in the first array element
        if (error.response && error.response.data && error.response.data.detail && typeof error.response.data.detail[0].msg === 'string') {
            errorMessage = error.response.data.detail[0].msg;
        }
        // Check if there's a general message in detail
        else if (error.response && error.response.data && error.response.data.detail) {
            errorMessage = error.response.data.detail;
        }

        // Display the error message
        console.error('Registration failed:', errorMessage);
        alert(errorMessage);
        hideLoading();
    }

}

// Edit user (placeholder)
function editUser(username) {
    alert(`This would edit user ${username} in a real implementation`);
}

// Delete user (placeholder)
function deleteUser(username) {
    if (!confirm(`Are you sure you want to delete user ${username}? This action cannot be undone.`)) return;
    alert(`This would delete user ${username} in a real implementation`);
}

// Load assign supervisors section (admin)
async function loadAssignSupervisors() {
    showLoading();
    
    try {
        // Load current assignments
        const assignmentsResponse = await axios.get(`${API_BASE_URL}/supervisor-assignments`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const assignmentsList = document.getElementById('assignmentsList');
        assignmentsList.innerHTML = '';
        
        if (assignmentsResponse.data.length === 0) {
            document.getElementById('noStudentsToAssign').classList.remove('hidden');
        } else {
            document.getElementById('noStudentsToAssign').classList.add('hidden');
            
            assignmentsResponse.data.forEach(assignment => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-medium text-gray-900">${assignment.student_name}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm text-gray-900">${assignment.supervisor_name || 'Not assigned'}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button onclick="changeSupervisor('${assignment.student_id}')" class="text-indigo-600 hover:text-indigo-900">Change</button>
                    </td>
                `;
                assignmentsList.appendChild(row);
            });
        }
        
        // Load students and supervisors for dropdowns
        const studentsResponse = await axios.get(`${API_BASE_URL}/students`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        console.log("studentsResponse:", studentsResponse);
        
        const supervisorsResponse = await axios.get(`${API_BASE_URL}/supervisors`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        console.log("supervisorsResponse:", supervisorsResponse);
        
        const studentSelect = document.getElementById('studentToAssign');
        studentSelect.innerHTML = '<option value="">-- Select a student --</option>';
        
        studentsResponse.data.forEach(student => {
            if (!student.supervisor_id) {
                const option = document.createElement('option');
                option.value = student.username;
                option.textContent = student.full_name;
                studentSelect.appendChild(option);
            }
        });
        
        const supervisorSelect = document.getElementById('supervisorToAssign');
        supervisorSelect.innerHTML = '<option value="">-- Select a supervisor --</option>';
        
        supervisorsResponse.data.forEach(supervisor => {
            const option = document.createElement('option');
            option.value = supervisor.username;
            option.textContent = supervisor.full_name;
            supervisorSelect.appendChild(option);
        });
        
        // Also populate supervisor dropdown in add user modal
        const addUserSupervisorSelect = document.getElementById('newSupervisor');
        addUserSupervisorSelect.innerHTML = '<option value="">-- Select a supervisor --</option>';
        
        supervisorsResponse.data.forEach(supervisor => {
            const option = document.createElement('option');
            option.value = supervisor.username;
            option.textContent = supervisor.full_name;
            addUserSupervisorSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load supervisor assignments:', error);
    }
    
    hideLoading();
}

// Assign supervisor to student (admin)
async function assignSupervisor() {
    const studentId = document.getElementById('studentToAssign').value;
    const supervisorId = document.getElementById('supervisorToAssign').value;
    
    if (!studentId || !supervisorId) {
        alert('Please select both a student and a supervisor.');
        return;
    }
    
    showLoading();
    
    try {
        // Prepare data as URLSearchParams
        const params = new URLSearchParams();
        params.append("student_username", studentId);
        params.append("supervisor_username", supervisorId);

        // Send POST request with URL-encoded data
        await axios.post(`${API_BASE_URL}/assign-supervisor`, params, {
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });

        // Refresh assignments list
        loadAssignSupervisors();
        
        // Reset dropdowns
        document.getElementById('studentToAssign').value = '';
        document.getElementById('supervisorToAssign').value = '';
    } catch (error) {
        console.error('Failed to assign supervisor:', error);
        hideLoading();
        alert('Failed to assign supervisor. Please try again.');
    }
}

// Change supervisor (placeholder)
function changeSupervisor(studentId) {
    alert(`This would change supervisor for student ${studentId} in a real implementation`);
}

// Load all theses (admin)
async function loadAllTheses() {
    showLoading();
    
    try {
        const response = await axios.get(`${API_BASE_URL}/all-theses`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const thesesList = document.getElementById('allThesesList');
        thesesList.innerHTML = '';
        
        if (response.data.length === 0) {
            document.getElementById('noThesesInSystem').classList.remove('hidden');
        } else {
            document.getElementById('noThesesInSystem').classList.add('hidden');
            
            response.data.forEach(thesis => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-medium text-gray-900">${thesis.student_name}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm text-gray-900">${thesis.filename}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm text-gray-500">${new Date(thesis.upload_date).toLocaleDateString()}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusClass(thesis.status)}">
                            ${thesis.status.replace(/_/g, ' ')}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button onclick="viewThesis('${thesis.id}')" class="text-indigo-600 hover:text-indigo-900">View</button>
                    </td>
                `;
                thesesList.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Failed to load all theses:', error);
    }
    
    hideLoading();
}

// Show view thesis modal
function showViewThesisModal() {
    document.getElementById('viewThesisModal').classList.remove('hidden');
}

// Hide view thesis modal
function hideViewThesisModal() {
    document.getElementById('viewThesisModal').classList.add('hidden');
}

// Download thesis (placeholder)
function downloadThesis() {
    alert('This would download the thesis in a real implementation');
}

// Show loading overlay
function showLoading() {
    document.getElementById('loadingOverlay').classList.remove('hidden');
}

// Hide loading overlay
function hideLoading() {
    document.getElementById('loadingOverlay').classList.add('hidden');
}

// Logout
function logout() {
    localStorage.removeItem('authToken');
    authToken = null;
    currentUser = null;
    
    // Show login, hide all other sections
    document.getElementById('loginSection').classList.remove('hidden');
    document.querySelectorAll('[id$="Section"]').forEach(section => {
        if (section.id !== 'loginSection') {
            section.classList.add('hidden');
        }
    });
    
    // Clear login form
    document.getElementById('loginForm').reset();
    document.getElementById('loginError').classList.add('hidden');

    checkAuthStatus();
}

// Helper function to get status class for styling
function getStatusClass(status) {
    switch (status) {
        case 'pending':
            return 'bg-yellow-100 text-yellow-800';
        case 'reviewed_by_ai':
            return 'bg-blue-100 text-blue-800';
        case 'reviewed_by_supervisor':
            return 'bg-purple-100 text-purple-800';
        case 'approved':
            return 'bg-green-100 text-green-800';
        case 'rejected':
            return 'bg-red-100 text-red-800';
        default:
            return 'bg-gray-100 text-gray-800';
    }
}

// Helper function to get role class for styling
function getRoleClass(role) {
    switch (role) {
        case 'student':
            return 'bg-indigo-100 text-indigo-800';
        case 'supervisor':
            return 'bg-purple-100 text-purple-800';
        case 'admin':
            return 'bg-green-100 text-green-800';
        default:
            return 'bg-gray-100 text-gray-800';
    }
}

function convertMarkdownToDiv(markdownText) {
  const htmlContent = marked.parse(markdownText);

  const container = document.createElement('div');
  container.className = 'markdown-body';
  container.innerHTML = htmlContent;

  return container;
}

// Render streaming content with better formatting
// function renderStreamingContent(text, container) {
//     // Clean up the text first
//     let cleanText = text
//         // Fix common streaming issues
//         .replace(/([a-zA-Z])([A-Z])/g, '$1 $2') // Add space between camelCase
//         .replace(/([a-zA-Z])(\d)/g, '$1 $2') // Add space between letter and number
//         .replace(/(\d)([a-zA-Z])/g, '$1 $2') // Add space between number and letter
//         .replace(/([.!?])([A-Z])/g, '$1\n\n$2') // Add paragraph breaks after sentences
//         .replace(/([.!?])\s+([A-Z])/g, '$1\n\n$2') // Fix existing sentence breaks
//         .replace(/\n{3,}/g, '\n\n') // Remove excessive line breaks
//         .trim();

//     // Use marked.js for proper markdown rendering
//     try {
//         const htmlContent = marked.parse(cleanText, {
//             breaks: true,
//             gfm: true
//         });
        
//         container.innerHTML = `
//             <div class="prose prose-indigo max-w-none">
//                 ${htmlContent}
//             </div>
//         `;
//     } catch (error) {
//         // Fallback to plain text if markdown parsing fails
//         container.innerHTML = `
//             <div class="prose prose-indigo max-w-none">
//                 <p>${cleanText.replace(/\n/g, '</p><p>')}</p>
//             </div>
//         `;
//     }
// }
function renderStreamingContent(streamedMessage, container) {
    // Clean minor broken word issues
    const cleaned = streamedMessage
        .replace(/\s+([.,;:!?])/g, '$1')
        .replace(/([.,;:!?])([A-Za-z])/g, '$1 $2')
        .replace(/\s{2,}/g, ' ');

    // Convert markdown → HTML
    container.innerHTML = marked.parse(cleaned);

    // Auto-scroll
    container.scrollTop = container.scrollHeight;
}

function cleanStreamedText(text) {
    return text
        // Merge broken words with spaces in middle of letters
        .replace(/(\w)\s+(\w)/g, (match, p1, p2) => {
            // Merge only if both are lowercase or both uppercase (likely a broken word)
            if ((/[a-z]/.test(p1) && /[a-z]/.test(p2)) || (/[A-Z]/.test(p1) && /[A-Z]/.test(p2))) {
                return p1 + p2;
            }
            return p1 + ' ' + p2;
        })
        // Fix spacing around punctuation
        .replace(/\s+([.,;:!?])/g, '$1')
        .replace(/([.,;:!?])([A-Za-z])/g, '$1 $2')
        // Remove multiple spaces
        .replace(/\s{2,}/g, ' ')
        // Normalize line breaks (keep bullet or numbered list breaks)
        .replace(/([^\n])\n([^\n])/g, '$1 $2')
        .trim();
}

const requestFeedbackBtn = document.getElementById('requestFeedbackBtn');
const feedbackResultsDiv = document.getElementById('feedbackResults');
const feedbackContentDiv = document.getElementById('feedbackContent');
const streamStatusSpan = document.getElementById('streamStatus');
const noThesesForFeedbackDiv = document.getElementById('noThesesForFeedback');

let currentFeedbackThesisId = null; // Keep track of the thesis being processed

requestFeedbackBtn.addEventListener('click', async function () {
    const thesisId = thesisSelect.value;
    const modelID = document.getElementById('modelID').value.trim() || "meta-llama/Meta-Llama-3.1-8B-Instruct"; // Default model

    if (!thesisId) {
        alert('Please select a thesis.');
        return;
    }

    // Show results section, hide no thesis message
    feedbackResultsDiv.classList.remove('hidden');
    noThesesForFeedbackDiv.classList.add('hidden');

    // Reset content and status
    feedbackContentDiv.innerHTML = '<p class="text-gray-500">Initializing feedback generation...</p>';
    streamStatusSpan.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Connecting...';
    streamStatusSpan.classList.remove('bg-green-100', 'text-green-800', 'bg-red-100', 'text-red-800');
    streamStatusSpan.classList.add('bg-yellow-100', 'text-yellow-800');

    // Disable button during request
    requestFeedbackBtn.disabled = true;
    requestFeedbackBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Requesting...';

    currentFeedbackThesisId = thesisId; // Set the ID for this request

    try {
        // Prepare form data
        const data = new URLSearchParams();
        data.append('custom_instructions', 'Please review this thesis and provide comprehensive feedback.');
        data.append('predefined_questions[0]', 'What are the strengths?');
        data.append('predefined_questions[1]', 'What areas need improvement?');
        data.append('predefined_questions[2]', 'How well does the methodology align?');
        data.append('predefined_questions[3]', 'Are there reference formatting issues?');
        data.append('predefined_questions[4]', 'How well is the theoretical foundation presented?');

        const url = `${API_BASE_URL}/request-ai-feedback?thesis_id=${encodeURIComponent(thesisId)}`;
        const headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': `Bearer ${authToken}`
        };

        const response = await fetch(url, {
            method: 'POST',
            headers,
            body: data.toString()
        });

        if (!response.ok || !response.body) {
            throw new Error(`API request failed with status ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let accumulatedContent = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                break;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.trim() === '') continue;
                
                // Handle Server-Sent Events format
                if (line.startsWith('data: ')) {
                    const data = line.substring(6); // Remove 'data: ' prefix
                    if (data.trim() === '') continue;
                    
                    try {
                        // Parse the JSON data
                        const jsonData = JSON.parse(data);
                        
                        if (jsonData.type === 'content') {
                            accumulatedContent += jsonData.content;
                            // Convert accumulated markdown to HTML
                            const htmlContent = marked.parse(accumulatedContent);
                            // Sanitize HTML
                            const sanitizedHtml = DOMPurify ? DOMPurify.sanitize(htmlContent) : htmlContent;
                            feedbackContainer.innerHTML = sanitizedHtml;
                            feedbackContainer.scrollTop = feedbackContainer.scrollHeight;
                        } else if (jsonData.type === 'progress') {
                            streamStatusSpan.innerHTML = `<i class="fas fa-spinner fa-spin mr-1"></i>${jsonData.content}`;
                        } else if (jsonData.type === 'error') {
                            throw new Error(jsonData.content);
                        } else if (jsonData.type === 'complete') {
                            // Stream completed
                            break;
                        }
                    } catch (e) {
                        if (e.message && e.message !== 'Unexpected end of JSON input') {
                            throw e; // Re-throw actual errors
                        }
                        // Ignore JSON parsing errors for incomplete chunks
                    }
                } else {
                    // Handle plain text (fallback)
                    accumulatedContent += line;
                    const htmlContent = marked.parse(accumulatedContent);
                    const sanitizedHtml = DOMPurify ? DOMPurify.sanitize(htmlContent) : htmlContent;
                    feedbackContainer.innerHTML = sanitizedHtml;
                    feedbackContainer.scrollTop = feedbackContainer.scrollHeight;
                }
            }
        }

        // Stream finished successfully
        streamStatusSpan.innerHTML = '<i class="fas fa-check-circle mr-1"></i>Complete';
        streamStatusSpan.classList.remove('bg-yellow-100', 'text-yellow-800');
        streamStatusSpan.classList.add('bg-green-100', 'text-green-800');

        // Save feedback
        const saveData = new URLSearchParams();
        saveData.append('feedback_content', accumulatedContent);
        await axios.post(`${API_BASE_URL}/save-ai-feedback?thesis_id=${thesisId}`, saveData, {
            headers: { 
                'Content-Type': 'application/x-www-form-urlencoded', 
                'Authorization': `Bearer ${authToken}` 
            }
        });

    } catch (error) {
        console.error("AI Feedback Streaming Error:", error);
        streamStatusSpan.innerHTML = `<i class="fas fa-exclamation-circle mr-1"></i>Error: ${error.message || 'Unknown error'}`;
        streamStatusSpan.classList.remove('bg-yellow-100', 'text-yellow-800');
        streamStatusSpan.classList.add('bg-red-100', 'text-red-800');
        feedbackContentDiv.innerHTML = `<p class="text-red-600">Failed to generate feedback: ${error.message}</p>`;
    } finally {
        // Re-enable button
        requestFeedbackBtn.disabled = false;
        requestFeedbackBtn.innerHTML = '<i class="fas fa-robot mr-2" aria-hidden="true"></i> Request AI Feedback';
        currentFeedbackThesisId = null; // Clear the ID
    }
});

// --- Helper function (if needed for updating list status) ---
// function updateThesisStatusInList(thesisId, statusText) {
//     const statusCell = document.querySelector(`#myThesesSection tr[data-thesis-id="${thesisId}"] .status-cell`); // Adjust selector
//     if (statusCell) {
//         statusCell.textContent = statusText; // Or update innerHTML if using badges etc.
//     }
// }

// --- Basic HTML escaping function (fallback if DOMPurify isn't used) ---
// function escapeHtml(unsafe) {
//     return unsafe
//         .replace(/&/g, "&amp;")
//         .replace(/</g, "<")
//         .replace(/>/g, ">")
//         .replace(/"/g, "&quot;")
//         .replace(/'/g, "&#039;");
// }

// --- Ensure the feedback section is reset when switching theses or re-requesting ---
function resetFeedbackDisplay() {
    if (feedbackResultsDiv) feedbackResultsDiv.classList.add('hidden');
    if (feedbackContentDiv) feedbackContentDiv.innerHTML = '';
    if (streamStatusSpan) {
        streamStatusSpan.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Generating...';
        streamStatusSpan.className = 'px-3 py-1 bg-white bg-opacity-20 text-white text-xs font-medium rounded-full'; // Reset to initial class
    }
    // Re-enable button if it was disabled by a previous error
    if (requestFeedbackBtn) {
        requestFeedbackBtn.disabled = false;
        requestFeedbackBtn.innerHTML = '<i class="fas fa-robot mr-2" aria-hidden="true"></i> Request AI Feedback';
    }
    currentFeedbackThesisId = null;
}

// You might call resetFeedbackDisplay() when:
// - The user selects a different thesis from the dropdown
// - The 'Request New Feedback' button is clicked
// - The AI Feedback section is shown/hidden

// Example: Reset on thesis selection change (if feedback hasn't started or completed for the *new* selection)
// thesisSelect.addEventListener('change', function() {
//     if (this.value !== currentFeedbackThesisId) {
//         resetFeedbackDisplay();
//     }
// });

// Example: Reset for 'Request New Feedback' button (assuming it exists and calls the main request function)
// document.getElementById('requestNewFeedbackBtn')?.addEventListener('click', resetFeedbackDisplay); // Use optional chaining
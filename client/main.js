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
    
    // AI Feedback checkbox controls
    document.getElementById('selectAllBtn').addEventListener('click', selectAllAIFeedbackOptions);
    document.getElementById('deselectAllBtn').addEventListener('click', deselectAllAIFeedbackOptions);
    
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
    content.classList.toggle('ml-64');
    content.classList.toggle('ml-16');
}

// Check authentication status
function checkAuthStatus() {
    const token = localStorage.getItem('authToken');
    if (token) {
        authToken = token;
        fetchCurrentUser();
    } else {
        // Show login section
        document.getElementById('loginSection').classList.remove('hidden');
        document.getElementById('dashboardSection').classList.add('hidden');
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

        const response = await axios.post(`${API_BASE_URL}/auth/token`, params, {
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
        const response = await axios.get(`${API_BASE_URL}/auth/me`, {
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
    try {
    // Load theses count
    const thesesResponse = await axios.get(`${API_BASE_URL}/thesis/my-theses`, {
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
            try {
        const supervisorResponse = await axios.get(`${API_BASE_URL}/users/users`, {
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
            } catch (error) {
                console.error('Failed to load supervisor info:', error);
                // Don't show error to user, just leave supervisor info empty
            }
        }
    } catch (error) {
        console.error('Failed to load student dashboard:', error);
        // Handle error gracefully without breaking the dashboard
    }
}

// Load supervisor dashboard data
async function loadSupervisorDashboard() {
    // Load assigned students count
    const studentsResponse = await axios.get(`${API_BASE_URL}/users/students`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    document.getElementById('studentCount').textContent = studentsResponse.data.length;
    
    // Load theses to review
    const thesesResponse = await axios.get(`${API_BASE_URL}/thesis/my-theses`, {
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
    const usersResponse = await axios.get(`${API_BASE_URL}/users/users`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    document.getElementById('totalUsers').textContent = usersResponse.data.length;
    
    // Count supervisors
    const supervisorCount = usersResponse.data.filter(u => u.role === 'supervisor').length;
    document.getElementById('supervisorCount').textContent = supervisorCount;
    
    // Load all theses count
    const thesesResponse = await axios.get(`${API_BASE_URL}/thesis/all`, {
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
        
        const response = await axios.post(`${API_BASE_URL}/thesis/upload`, formData, {
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
        const response = await axios.get(`${API_BASE_URL}/thesis/my-theses`, {
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
        // First get thesis info
        const response = await axios.get(`${API_BASE_URL}/thesis/my-theses`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const thesis = response.data.find(t => t.id === thesisId);
        if (!thesis) {
            throw new Error('Thesis not found');
        }
        
        document.getElementById('thesisModalTitle').textContent = thesis.filename;
        
        // Set basic info
        const basicInfo = document.getElementById('thesisBasicInfo');
        basicInfo.innerHTML = `
            <p><strong>Student:</strong> ${thesis.student_name || 'N/A'}</p>
            <p><strong>Upload Date:</strong> ${new Date(thesis.upload_date).toLocaleDateString()}</p>
            <p><strong>Status:</strong> <span class="${getStatusClass(thesis.status)}">${thesis.status.replace(/_/g, ' ')}</span></p>
        `;
        
        // Set AI feedback if available
        const aiFeedback = document.getElementById('thesisAIFeedback');
        if (thesis.ai_feedback_id) {
            aiFeedback.innerHTML = '<p>AI feedback available. Check the AI Feedback section for details.</p>';
        } else {
            aiFeedback.innerHTML = '<p>No AI feedback available yet.</p>';
        }
        
        // Set supervisor feedback if available
        const supervisorFeedback = document.getElementById('thesisSupervisorFeedback');
        if (thesis.supervisor_feedback_id) {
            supervisorFeedback.innerHTML = '<p>Supervisor feedback available. Check the Supervisor Feedback section for details.</p>';
        } else {
            supervisorFeedback.innerHTML = '<p>No supervisor feedback available yet.</p>';
        }
        
        // Set document preview
        const docPreview = document.getElementById('thesisDocumentPreview');
        docPreview.innerHTML = `
            <div class="mt-2 flex items-center">
                <i class="fas fa-file-word text-4xl text-blue-500 mr-3"></i>
                <div>
                    <p class="text-sm font-medium">${thesis.filename}</p>
                    <p class="text-xs text-gray-500">Uploaded on ${new Date(thesis.upload_date).toLocaleDateString()}</p>
                </div>
            </div>
        `;
        
        currentThesisId = thesisId;
        showViewThesisModal();
    } catch (error) {
        console.error('Failed to load thesis:', error);
        alert('Failed to load thesis details. Please try again.');
    }
    
    hideLoading();
}

// Delete thesis
async function deleteThesis(thesisId) {
    if (!confirm('Are you sure you want to delete this thesis? This action cannot be undone.')) return;
    
    showLoading();
    
    try {
        await axios.delete(`${API_BASE_URL}/thesis/${thesisId}`, {
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
        const response = await axios.get(`${API_BASE_URL}/thesis/my-theses`, {
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
        
        // Load AI feedback options
        await loadAIFeedbackOptions();
        
    } catch (error) {
        console.error('Failed to load AI feedback:', error);
    }
    
    hideLoading();
}

// Load AI feedback options from server
async function loadAIFeedbackOptions() {
    try {
        const response = await axios.get(`${API_BASE_URL}/ai/feedback-options`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const checkboxesContainer = document.getElementById('aiFeedbackCheckboxes');
        checkboxesContainer.innerHTML = '';
        
        response.data.options.forEach(option => {
            if (option.enabled) {
                const checkboxDiv = document.createElement('div');
                checkboxDiv.className = 'flex items-start';
                checkboxDiv.innerHTML = `
                    <div class="flex items-center h-5">
                        <input type="checkbox" 
                               id="ai_option_${option.id}" 
                               class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                               ${option.default ? 'checked' : ''}>
                    </div>
                    <div class="ml-3">
                        <label for="ai_option_${option.id}" class="text-sm font-medium text-gray-700">
                            ${option.label}
                        </label>
                        <p class="text-xs text-gray-500">${option.description}</p>
                    </div>
                `;
                checkboxesContainer.appendChild(checkboxDiv);
            }
        });
        
    } catch (error) {
        console.error('Failed to load AI feedback options:', error);
        // Fallback to default options
        const checkboxesContainer = document.getElementById('aiFeedbackCheckboxes');
        checkboxesContainer.innerHTML = `
            <div class="flex items-center">
                <input type="checkbox" id="ai_option_formatting_style" class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded" checked>
                <label for="ai_option_formatting_style" class="ml-2 block text-sm text-gray-700">Formatting style</label>
            </div>
            <div class="flex items-center">
                <input type="checkbox" id="ai_option_purpose_objectives" class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded" checked>
                <label for="ai_option_purpose_objectives" class="ml-2 block text-sm text-gray-700">Purpose and objectives</label>
            </div>
            <div class="flex items-center">
                <input type="checkbox" id="ai_option_theoretical_foundation" class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded" checked>
                <label for="ai_option_theoretical_foundation" class="ml-2 block text-sm text-gray-700">Theoretical foundation</label>
            </div>
            <div class="flex items-center">
                <input type="checkbox" id="ai_option_professional_connection" class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded" checked>
                <label for="ai_option_professional_connection" class="ml-2 block text-sm text-gray-700">Connection of subject to professional field and expertise</label>
            </div>
            <div class="flex items-center">
                <input type="checkbox" id="ai_option_development_task" class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded" checked>
                <label for="ai_option_development_task" class="ml-2 block text-sm text-gray-700">Development/research task and its definition</label>
            </div>
        `;
    }
}

// Select all AI feedback options
function selectAllAIFeedbackOptions() {
    const checkboxes = document.querySelectorAll('#aiFeedbackCheckboxes input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
    });
}

// Deselect all AI feedback options
function deselectAllAIFeedbackOptions() {
    const checkboxes = document.querySelectorAll('#aiFeedbackCheckboxes input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
}

// Request AI feedback
async function requestAIFeedback() {
    const thesisId = document.getElementById('thesisSelect').value;
    if (!thesisId) {
        alert('Please select a thesis first');
        return;
    }

    const selectedOption = document.getElementById('thesisSelect').selectedOptions[0];
    const thesisTitle = selectedOption.textContent;
    const customInstructions = "Please review this thesis and provide comprehensive feedback.";
    
    // Collect selected feedback options
    const selectedOptions = [];
    const checkboxes = document.querySelectorAll('#aiFeedbackCheckboxes input[type="checkbox"]:checked');
    checkboxes.forEach(checkbox => {
        const optionId = checkbox.id.replace('ai_option_', '');
        selectedOptions.push(optionId);
    });
    
    if (selectedOptions.length === 0) {
        alert('Please select at least one feedback option');
        return;
    }

    // Reset any previous feedback display
    resetFeedbackDisplay();

    // Show results section
    document.getElementById('feedbackResults').classList.remove('hidden');
    document.getElementById('feedbackThesisTitle').textContent = thesisTitle;
    document.getElementById('feedbackThesisDate').textContent = `Uploaded on ${new Date().toLocaleDateString()}`;
    document.getElementById('feedbackThesisStatus').textContent = 'AI Reviewed';

    const feedbackContainer = document.getElementById('feedbackContent');
    const statusBadge = document.getElementById('streamStatus');
    const streamStatusBelow = document.getElementById('streamStatusBelow');
    const streamProgress = document.getElementById('streamProgress');
    const requestFeedbackBtn = document.getElementById('requestFeedbackBtn');
    const stopStreamingBtn = document.getElementById('stopStreamingBtn');
    
    // Check if feedbackContainer exists
    if (!feedbackContainer) {
        console.error('feedbackContent element not found');
        alert('Error: Feedback container not found. Please refresh the page and try again.');
        return;
    }
    
    // Disable request button and show stop button
    requestFeedbackBtn.disabled = true;
    requestFeedbackBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Requesting...';
    stopStreamingBtn.classList.remove('hidden');
    statusBadge.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Generating...';
    feedbackContainer.innerHTML = '';
    
    // Show status below feedback content
    streamStatusBelow.classList.remove('hidden');
    streamProgress.textContent = 'Starting analysis...';

    // Create AbortController for request cancellation
    const abortController = new AbortController();
    let isStreamingStopped = false;

    // Add event listener for stop button
    const stopStreaming = () => {
        console.log('Stopping AI feedback streaming...');
        isStreamingStopped = true;
        abortController.abort(); // Abort the fetch request
        statusBadge.innerHTML = '<i class="fas fa-stop-circle mr-1"></i>Stopped';
        statusBadge.classList.remove('bg-white', 'bg-opacity-20');
        statusBadge.classList.add('bg-yellow-500', 'bg-opacity-20');
        streamStatusBelow.classList.add('hidden');
        stopStreamingBtn.classList.add('hidden');
        requestFeedbackBtn.disabled = false;
        requestFeedbackBtn.innerHTML = '<i class="fas fa-robot mr-2" aria-hidden="true"></i> Request AI Feedback';
    };
    
    stopStreamingBtn.onclick = stopStreaming;
    scrollToBottom();

    try {
        const data = new URLSearchParams();
        data.append('custom_instructions', customInstructions);
        data.append('selected_options', JSON.stringify(selectedOptions));
        
        // Add each selected option as a predefined question
        selectedOptions.forEach((option, i) => {
            const questionMap = {
                'strengths': 'What are the strengths and positive aspects of this thesis?',
                'improvements': 'What areas need improvement in this thesis?',
                'methodology': 'How well is the research methodology implemented?',
                'references': 'Are the references properly formatted according to Harvard style?',
                'theoretical_framework': 'How strong is the theoretical foundation and literature review?',
                'structure': 'How well is the thesis structured and organized?',
                'writing_quality': 'How is the overall writing quality and clarity?',
                'practical_relevance': 'What is the practical relevance and real-world impact?',
                'objectives': 'How clear and feasible are the research objectives?',
                'conclusions': 'How strong are the conclusions and recommendations?'
            };
            
            const question = questionMap[option] || `Please evaluate the ${option.replace('_', ' ')} of this thesis.`;
            data.append(`predefined_questions[${i}]`, question);
        });

        const url = `${API_BASE_URL}/ai/feedback`;
        const headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': `Bearer ${authToken}`
        };

        // Add thesis_id to the form data
        data.append('thesis_id', thesisId);

        const response = await fetch(url, { 
            method: 'POST', 
            headers, 
            body: data.toString(),
            signal: abortController.signal
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        if (!response.body) {
            throw new Error('ReadableStream not supported');
        }

        // Get reader from response body
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let accumulatedContent = '';
        let hasStartedStreaming = false;

        statusBadge.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Streaming content...';
        streamProgress.textContent = 'Streaming content...';

        // Read chunks and parse Server-Sent Events
        while (true) {
            // Check if streaming was stopped
            if (isStreamingStopped) {
                console.log('Streaming stopped by user');
                break;
            }
            
            const { done, value } = await reader.read();
            
            if (done) {
                statusBadge.innerHTML = '<i class="fas fa-check-circle mr-1"></i>Complete';
                statusBadge.classList.remove('bg-white', 'bg-opacity-20');
                statusBadge.classList.add('bg-green-500', 'bg-opacity-20');
                streamStatusBelow.classList.add('hidden');
                stopStreamingBtn.classList.add('hidden');
                break;
            }
            
            // Decode chunk and add to buffer
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            // Process each line
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
                            
                            // Highlight code blocks
                            feedbackContainer.querySelectorAll('pre code').forEach((block) => {
                                hljs.highlightElement(block);
                            });
                            
                            // Scroll to bottom on first content load
                            if (!hasStartedStreaming) {
                                setTimeout(() => {
                            feedbackContainer.scrollTop = feedbackContainer.scrollHeight;
                                }, 100);
                                hasStartedStreaming = true;
                            }
                        } else if (jsonData.type === 'progress') {
                            statusBadge.innerHTML = `<i class="fas fa-spinner fa-spin mr-1"></i>${jsonData.content}`;
                            streamProgress.textContent = jsonData.content;
                        } else if (jsonData.type === 'status') {
                            streamProgress.textContent = jsonData.content;
                        } else if (jsonData.type === 'section') {
                            // Add section header to the content
                            accumulatedContent += `\n\n# ${jsonData.content}\n\n`;
                            const htmlContent = marked.parse(accumulatedContent);
                            const sanitizedHtml = DOMPurify ? DOMPurify.sanitize(htmlContent) : htmlContent;
                            feedbackContainer.innerHTML = sanitizedHtml;
                            
                            // Highlight code blocks
                            feedbackContainer.querySelectorAll('pre code').forEach((block) => {
                                hljs.highlightElement(block);
                            });
                        } else if (jsonData.type === 'error') {
                            throw new Error(jsonData.content);
                        } else if (jsonData.type === 'complete') {
                            // Stream completed
                            streamStatusBelow.classList.add('hidden');
                            stopStreamingBtn.classList.add('hidden');
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
                    
                    // Highlight code blocks
                    feedbackContainer.querySelectorAll('pre code').forEach((block) => {
                        hljs.highlightElement(block);
                    });
                    
                    // Scroll to bottom on first content load
                    if (!hasStartedStreaming) {
                        setTimeout(() => {
                    feedbackContainer.scrollTop = feedbackContainer.scrollHeight;
                        }, 100);
                        hasStartedStreaming = true;
                    }
                }
            }
        }

        // Save feedback
        const saveData = new URLSearchParams();
        saveData.append('feedback_content', accumulatedContent);
        // Add thesis_id to the form data
        saveData.append('thesis_id', thesisId);
        
        await axios.post(`${API_BASE_URL}/ai/save-feedback`, saveData, {
            headers: { 
                'Content-Type': 'application/x-www-form-urlencoded', 
                'Authorization': `Bearer ${authToken}` 
            }
        });

        // Generate table of contents
        generateTableOfContents(accumulatedContent);

    } catch (error) {
        console.error('Failed to generate feedback:', error);
        
        // Handle AbortError separately (user stopped streaming)
        if (error.name === 'AbortError' || isStreamingStopped) {
            console.log('Request was aborted by user');
            return; // Don't show error message for user-initiated stops
        }
        
        // feedbackContainer.innerHTML = `<p class="text-red-600">Failed to generate feedback: ${error.message}</p>`;
        statusBadge.innerHTML = '<i class="fas fa-exclamation-triangle mr-1"></i>Error';
        statusBadge.classList.remove('bg-white', 'bg-opacity-20');
        statusBadge.classList.add('bg-red-500', 'bg-opacity-20');
        streamStatusBelow.classList.add('hidden');
    } finally {
        // Re-enable button and hide stop button
        requestFeedbackBtn.disabled = false;
        requestFeedbackBtn.innerHTML = '<i class="fas fa-robot mr-2" aria-hidden="true"></i> Request AI Feedback';
        stopStreamingBtn.classList.add('hidden');
        // Remove event listener
        stopStreamingBtn.onclick = null;
    }
}

// Generate table of contents from feedback content
function generateTableOfContents(content) {
    // Parse the content to find headings and sections
    const lines = content.split('\n');
    const toc = [];
    let currentSection = '';
    let currentSubsection = '';
    
    lines.forEach((line, index) => {
        const trimmedLine = line.trim();
        
        // Check for main headings (## or ###)
        if (trimmedLine.startsWith('##') && !trimmedLine.startsWith('###')) {
            const heading = trimmedLine.replace(/^#+\s*/, '').trim();
            if (heading && !heading.toLowerCase().includes('table of contents')) {
                currentSection = heading;
                toc.push({
                    type: 'section',
                    title: heading,
                    level: 2,
                    lineNumber: index + 1
                });
            }
        }
        // Check for subsections (###)
        else if (trimmedLine.startsWith('###')) {
            const heading = trimmedLine.replace(/^#+\s*/, '').trim();
            if (heading) {
                currentSubsection = heading;
                toc.push({
                    type: 'subsection',
                    title: heading,
                    level: 3,
                    lineNumber: index + 1,
                    parent: currentSection
                });
            }
        }
        // Check for numbered lists that might be sections
        else if (/^\d+\.\s+[A-Z]/.test(trimmedLine)) {
            const heading = trimmedLine.replace(/^\d+\.\s+/, '').trim();
            if (heading && heading.length > 10) { // Only consider substantial headings
                toc.push({
                    type: 'numbered',
                    title: heading,
                    level: 2,
                    lineNumber: index + 1
                });
            }
        }
    });
    
    // Display the table of contents
    displayTableOfContents(toc);
}

// Display table of contents in the UI
function displayTableOfContents(toc) {
    const tocContainer = document.getElementById('feedbackTableOfContents');
    if (!tocContainer) {
        // Create TOC container if it doesn't exist
        const feedbackResults = document.getElementById('feedbackResults');
        const tocSection = document.createElement('div');
        tocSection.className = 'mb-6';
        tocSection.innerHTML = `
            <div class="bg-white rounded-lg shadow-lg border border-gray-200">
                <div class="bg-gradient-to-r from-purple-500 to-pink-600 px-6 py-4 rounded-t-lg">
                    <div class="flex justify-between items-center">
                        <div class="flex items-center">
                            <i class="fas fa-list text-white text-xl mr-3"></i>
                            <div>
                                <h3 class="text-lg font-semibold text-white">Table of Contents</h3>
                                <p class="text-purple-100 text-sm">Quick navigation for feedback sections</p>
                            </div>
                        </div>
                        <button onclick="toggleTOC()" class="text-white hover:text-purple-200">
                            <i class="fas fa-chevron-down" id="tocToggleIcon"></i>
                        </button>
                    </div>
                </div>
                <div id="feedbackTableOfContents" class="p-6">
                    <!-- TOC content will be added here -->
                </div>
            </div>
        `;
        
        // Insert TOC before the feedback content
        const feedbackContent = feedbackResults.querySelector('.bg-white.rounded.shadow-lg');
        feedbackResults.insertBefore(tocSection, feedbackContent);
    }
    
    if (toc.length === 0) {
        tocContainer.innerHTML = '<p class="text-gray-500 text-center py-4">No sections found in the feedback content.</p>';
        return;
    }
    
    let tocHTML = '<div class="space-y-2">';
    
    toc.forEach((item, index) => {
        const indentClass = item.level === 3 ? 'ml-4' : '';
        const iconClass = item.level === 2 ? 'fas fa-bookmark' : 'fas fa-angle-right';
        const colorClass = item.level === 2 ? 'text-purple-600' : 'text-gray-600';
        
        tocHTML += `
            <div class="flex items-center ${indentClass}">
                <i class="${iconClass} ${colorClass} mr-2 text-sm"></i>
                <button onclick="scrollToSection(${item.lineNumber})" 
                        class="text-left hover:text-purple-600 hover:underline transition-colors duration-200 ${colorClass}">
                    ${item.title}
                </button>
            </div>
        `;
    });
    
    tocHTML += '</div>';
    tocContainer.innerHTML = tocHTML;
}

// Toggle table of contents visibility
function toggleTOC() {
    const tocContainer = document.getElementById('feedbackTableOfContents');
    const toggleIcon = document.getElementById('tocToggleIcon');
    
    if (tocContainer.classList.contains('hidden')) {
        tocContainer.classList.remove('hidden');
        toggleIcon.classList.remove('fa-chevron-down');
        toggleIcon.classList.add('fa-chevron-up');
    } else {
        tocContainer.classList.add('hidden');
        toggleIcon.classList.remove('fa-chevron-up');
        toggleIcon.classList.add('fa-chevron-down');
    }
}

// Scroll to specific section in feedback content
function scrollToSection(lineNumber) {
    const feedbackContainer = document.getElementById('feedbackContent');
    
    // Check if feedbackContainer exists
    if (!feedbackContainer) {
        console.error('feedbackContent element not found');
        return;
    }
    
    const lines = feedbackContainer.textContent.split('\n');
    
    // Find the approximate position of the line
    let currentPosition = 0;
    for (let i = 0; i < Math.min(lineNumber - 1, lines.length); i++) {
        currentPosition += lines[i].length + 1; // +1 for newline
    }
    
    // Create a temporary marker element
    const marker = document.createElement('div');
    marker.id = 'scroll-marker';
    marker.style.height = '1px';
    marker.style.marginTop = '-50px'; // Offset for better visibility
    
    // Insert marker at the position
    const textNode = feedbackContainer.firstChild;
    if (textNode) {
        feedbackContainer.insertBefore(marker, textNode);
        
        // Scroll to marker
        marker.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Remove marker after scrolling
        setTimeout(() => {
            if (marker.parentNode) {
                marker.parentNode.removeChild(marker);
            }
        }, 1000);
    }
}

function scrollToBottom() {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
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
        const response = await axios.get(`${API_BASE_URL}/users/supervisor-feedback`, {
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
        const response = await axios.get(`${API_BASE_URL}/users/students`, {
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
        const response = await axios.get(`${API_BASE_URL}/thesis/to-review`, {
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
        const response = await axios.get(`${API_BASE_URL}/thesis/${thesisId}`, {
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
        await axios.post(`${API_BASE_URL}/users/submit-supervisor-feedback`, {
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
        const response = await axios.get(`${API_BASE_URL}/users/users`, {
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

        const response = await axios.post(`${API_BASE_URL}/auth/register`, params, {
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

// Edit user
async function editUser(username) {
    showLoading();
    
    try {
        // Get user details
        const response = await axios.get(`${API_BASE_URL}/users/users/${username}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const user = response.data;
        
        // Populate the edit form
        document.getElementById('editUsername').value = user.username;
        document.getElementById('editEmail').value = user.email;
        document.getElementById('editFullName').value = user.full_name;
        document.getElementById('editRole').value = user.role;
        
        // Handle supervisor field visibility
        const editSupervisorField = document.getElementById('editSupervisorField');
        const editSupervisor = document.getElementById('editSupervisor');
        
        if (user.role === 'student') {
            editSupervisorField.classList.remove('hidden');
            
            // Load supervisors for dropdown
            const supervisorsResponse = await axios.get(`${API_BASE_URL}/users/supervisors`, {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            
            editSupervisor.innerHTML = '<option value="">-- Select a supervisor --</option>';
            supervisorsResponse.data.forEach(supervisor => {
                const option = document.createElement('option');
                option.value = supervisor.username;
                option.textContent = supervisor.full_name;
                if (user.supervisor_id === supervisor.id) {
                    option.selected = true;
                }
                editSupervisor.appendChild(option);
            });
        } else {
            editSupervisorField.classList.add('hidden');
        }
        
        // Show the modal
        document.getElementById('editUserModal').classList.remove('hidden');
        
        // Add event listener for role change
        document.getElementById('editRole').addEventListener('change', function() {
            if (this.value === 'student') {
                editSupervisorField.classList.remove('hidden');
                // Reload supervisors
                loadSupervisorsForEdit();
            } else {
                editSupervisorField.classList.add('hidden');
            }
        });
        
        // Add event listener for confirm button
        document.getElementById('confirmEditUser').onclick = () => updateUser(username);
        
    } catch (error) {
        console.error('Failed to load user details:', error);
        alert(`Failed to load user details: ${error.response?.data?.detail || error.message}`);
    }
    
    hideLoading();
}

// Load supervisors for edit modal
async function loadSupervisorsForEdit() {
    try {
        const supervisorsResponse = await axios.get(`${API_BASE_URL}/users/supervisors`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const editSupervisor = document.getElementById('editSupervisor');
        editSupervisor.innerHTML = '<option value="">-- Select a supervisor --</option>';
        
        supervisorsResponse.data.forEach(supervisor => {
            const option = document.createElement('option');
            option.value = supervisor.username;
            option.textContent = supervisor.full_name;
            editSupervisor.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load supervisors:', error);
    }
}

// Update user
async function updateUser(username) {
    showLoading();
    
    try {
        const formData = new FormData();
        formData.append('email', document.getElementById('editEmail').value);
        formData.append('full_name', document.getElementById('editFullName').value);
        formData.append('role', document.getElementById('editRole').value);
        
        const editSupervisor = document.getElementById('editSupervisor');
        if (document.getElementById('editRole').value === 'student' && editSupervisor.value) {
            formData.append('supervisor_username', editSupervisor.value);
        }
        
        const response = await axios.put(`${API_BASE_URL}/users/users/${username}`, formData, {
            headers: { 
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });
        
        alert(`User ${username} updated successfully`);
        
        // Hide modal and refresh users list
        hideEditUserModal();
        loadAllUsers();
        
    } catch (error) {
        console.error('Failed to update user:', error);
        alert(`Failed to update user: ${error.response?.data?.detail || error.message}`);
    }
    
    hideLoading();
}

// Show edit user modal
function showEditUserModal() {
    document.getElementById('editUserModal').classList.remove('hidden');
}

// Hide edit user modal
function hideEditUserModal() {
    document.getElementById('editUserModal').classList.add('hidden');
}

// Delete user
async function deleteUser(username) {
    if (!confirm(`Are you sure you want to delete user ${username}? This action cannot be undone.`)) return;
    
    showLoading();
    
    try {
        const response = await axios.delete(`${API_BASE_URL}/users/users/${username}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        alert(`User ${username} deleted successfully`);
        
        // Refresh the users list
        loadAllUsers();
    } catch (error) {
        console.error('Failed to delete user:', error);
        alert(`Failed to delete user: ${error.response?.data?.detail || error.message}`);
    }
    
    hideLoading();
}

// Load assign supervisors section (admin)
async function loadAssignSupervisors() {
    showLoading();
    
    try {
        // Load current assignments
        const assignmentsResponse = await axios.get(`${API_BASE_URL}/users/supervisor-assignments`, {
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
        const studentsResponse = await axios.get(`${API_BASE_URL}/users/students`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        console.log("studentsResponse:", studentsResponse);
        
        const supervisorsResponse = await axios.get(`${API_BASE_URL}/users/supervisors`, {
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
        await axios.post(`${API_BASE_URL}/users/assign-supervisor`, params, {
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
        const response = await axios.get(`${API_BASE_URL}/thesis/all`, {
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

// Download thesis
async function downloadThesis() {
    if (!currentThesisId) {
        alert('No thesis selected for download.');
        return;
    }
    
    showLoading();
    
    try {
        const response = await axios.get(`${API_BASE_URL}/thesis/download/${currentThesisId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` },
            responseType: 'blob'
        });
        
        // Create a download link
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', response.headers['content-disposition']?.split('filename=')[1] || 'thesis.pdf');
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
        
        hideViewThesisModal();
    } catch (error) {
        console.error('Failed to download thesis:', error);
        alert('Failed to download thesis. Please try again.');
    }
    
    hideLoading();
}

// Preview thesis
async function previewThesis() {
    if (!currentThesisId) {
        alert('No thesis selected for preview.');
        return;
    }
    
    try {
        // Get thesis info to determine file type
        const response = await axios.get(`${API_BASE_URL}/my-theses`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const thesis = response.data.find(t => t.id === currentThesisId);
        if (!thesis) {
            throw new Error('Thesis not found');
        }
        
        // Show preview modal first
        showThesisPreviewModal();
        
        // Set modal title and file info
        document.getElementById('previewModalTitle').textContent = `Preview: ${thesis.filename}`;
        document.getElementById('previewFileType').textContent = thesis.filename.split('.').pop().toUpperCase();
        
        // Show loading state
        document.getElementById('previewLoading').classList.remove('hidden');
        document.getElementById('pdfPreview').classList.add('hidden');
        document.getElementById('textPreview').classList.add('hidden');
        document.getElementById('previewError').classList.add('hidden');
        document.getElementById('imagePreview').classList.add('hidden');
        
        // Get preview images from server
        try {
            const imagesResponse = await axios.get(`${API_BASE_URL}/thesis/preview-images/${currentThesisId}`, {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            
            const images = imagesResponse.data.images;
            
            if (images && images.length > 0) {
                // Display images
                const imageContainer = document.getElementById('imagePreviewContainer');
                imageContainer.innerHTML = '';
                
                images.forEach((imageData, index) => {
                    const imageDiv = document.createElement('div');
                    imageDiv.className = 'mb-4';
                    imageDiv.innerHTML = `
                        <div class="flex items-center justify-between mb-2">
                            <h4 class="text-sm font-medium text-gray-700">Page ${imageData.page}</h4>
                            <span class="text-xs text-gray-500">${imageData.width} × ${imageData.height}</span>
                        </div>
                        <div class="border border-gray-200 rounded-lg overflow-hidden">
                            <img src="${imageData.image}" 
                                 alt="Page ${imageData.page}" 
                                 class="w-full h-auto max-h-96 object-contain"
                                 style="max-width: 100%;">
                        </div>
                    `;
                    imageContainer.appendChild(imageDiv);
                });
                
                document.getElementById('imagePreview').classList.remove('hidden');
                document.getElementById('previewLoading').classList.add('hidden');
                
                // Store text content if available (for DOC/DOCX)
                if (images[0].text_content) {
                    window.currentPreviewText = images[0].text_content;
                }
                
            } else {
                throw new Error('No preview images generated');
            }
            
        } catch (error) {
            console.error('Failed to load preview images:', error);
            
            // Fallback to old preview method for PDF
            const fileExtension = thesis.filename.split('.').pop().toLowerCase();
            
            if (fileExtension === 'pdf') {
                try {
                    const previewUrl = `${API_BASE_URL}/thesis/download/${currentThesisId}`;
                    const headers = { 'Authorization': `Bearer ${authToken}` };
                    
                    const pdfResponse = await fetch(previewUrl, { headers });
                    if (!pdfResponse.ok) {
                        throw new Error(`Failed to fetch PDF: ${pdfResponse.status}`);
                    }
                    
                    const blob = await pdfResponse.blob();
                    const url = window.URL.createObjectURL(blob);
                    
                    document.getElementById('pdfViewer').src = url;
                    document.getElementById('pdfPreview').classList.remove('hidden');
                    document.getElementById('previewLoading').classList.add('hidden');
                    
                } catch (pdfError) {
                    throw new Error('Failed to load PDF preview');
                }
            } else {
                document.getElementById('previewErrorMessage').textContent = 'Failed to generate preview. Please download the file to view it.';
                document.getElementById('previewError').classList.remove('hidden');
                document.getElementById('previewLoading').classList.add('hidden');
            }
        }
        
    } catch (error) {
        console.error('Failed to preview thesis:', error);
        // Ensure modal is shown even if there's an error
        showThesisPreviewModal();
        document.getElementById('previewModalTitle').textContent = 'Preview Error';
        document.getElementById('previewErrorMessage').textContent = 'Failed to load preview. Please try again.';
        document.getElementById('previewError').classList.remove('hidden');
        document.getElementById('previewLoading').classList.add('hidden');
    }
}

// Show thesis preview modal
function showThesisPreviewModal() {
    document.getElementById('thesisPreviewModal').classList.remove('hidden');
}

// Hide thesis preview modal
function hideThesisPreviewModal() {
    document.getElementById('thesisPreviewModal').classList.add('hidden');
    // Clean up iframe src to prevent memory leaks
    document.getElementById('pdfViewer').src = '';
}

// Copy preview text to clipboard
function copyPreviewText() {
    if (window.currentPreviewText) {
        navigator.clipboard.writeText(window.currentPreviewText).then(() => {
            // Show success message
            const button = event.target.closest('button');
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-check mr-1"></i> Copied!';
            button.classList.remove('bg-blue-600', 'hover:bg-blue-700');
            button.classList.add('bg-green-600', 'hover:bg-green-700');
            
            setTimeout(() => {
                button.innerHTML = originalText;
                button.classList.remove('bg-green-600', 'hover:bg-green-700');
                button.classList.add('bg-blue-600', 'hover:bg-blue-700');
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy text:', err);
            alert('Failed to copy text to clipboard');
        });
    }
}

// Download preview text
function downloadPreviewText() {
    if (window.currentPreviewText) {
        const blob = new Blob([window.currentPreviewText], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'thesis_content.txt');
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    }
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
    // Hide results section
    document.getElementById('feedbackResults').classList.add('hidden');
    
    // Reset thesis select
    document.getElementById('thesisSelect').value = '';
    
    // Clear feedback content
    document.getElementById('feedbackContent').innerHTML = '';
    
    // Reset status
    document.getElementById('streamStatus').innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Generating...';
    document.getElementById('streamStatus').classList.remove('bg-green-500', 'bg-red-500', 'bg-opacity-20');
    document.getElementById('streamStatus').classList.add('bg-white', 'bg-opacity-20');
    
    // Hide stream status below
    document.getElementById('streamStatusBelow').classList.add('hidden');
    
    // Remove table of contents if it exists
    const tocSection = document.querySelector('.bg-gradient-to-r.from-purple-500.to-pink-600');
    if (tocSection) {
        tocSection.closest('.mb-6').remove();
    }
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

// Initialize Marked.js and Highlight.js
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Marked.js
    marked.setOptions({
        breaks: true,
        gfm: true,
        highlight: function(code, lang) {
            const language = hljs.getLanguage(lang) ? lang : 'plaintext';
            return hljs.highlight(code, { language }).value;
        }
    });
});
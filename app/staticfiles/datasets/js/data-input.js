// Data Input JavaScript for ISR Field
// This file handles the interactive map and data entry functionality

// Global variables
var map;
var markers = [];
var currentPoint = null;
var uploadedFiles = [];
var typologyData = null;
var allFields = [];

// Initialize the data input functionality
function initializeDataInput(typologyDataParam, allFieldsParam) {
    typologyData = typologyDataParam;
    allFields = allFieldsParam;
    
    initializeMap();
    setupEventListeners();
    initializeResponsiveLayout();
}

// Function to create usage code dropdown
function createUsageCodeDropdown(fieldId, currentValue) {
    if (!typologyData || !typologyData.entries) {
        return `<input type="text" class="form-control form-control-sm" id="${fieldId}" placeholder="${window.translations?.selectUsageCode || 'Select usage code...'}" value="${currentValue || ''}">`;
    }
    
    var options = '<option value="">' + (window.translations?.selectUsageCode || 'Select usage code...') + '</option>';
    
    // Sort entries by code
    var sortedEntries = typologyData.entries.sort(function(a, b) {
        return a.code - b.code;
    });
    
    // Group by category
    var categories = {};
    sortedEntries.forEach(function(entry) {
        if (!categories[entry.category]) {
            categories[entry.category] = [];
        }
        categories[entry.category].push(entry);
    });
    
    // Sort categories by their lowest code value
    var sortedCategories = Object.keys(categories).sort(function(a, b) {
        var minCodeA = Math.min(...categories[a].map(entry => entry.code));
        var minCodeB = Math.min(...categories[b].map(entry => entry.code));
        return minCodeA - minCodeB;
    });
    
    // Add options grouped by category
    sortedCategories.forEach(function(category) {
        options += `<optgroup label="${category}">`;
        categories[category].forEach(function(entry) {
            var selected = (entry.code == currentValue) ? 'selected' : '';
            options += `<option value="${entry.code}" ${selected}>${entry.code} - ${entry.name}</option>`;
        });
        options += '</optgroup>';
    });
    
    return `<select class="form-control form-control-sm" id="${fieldId}">${options}</select>`;
}

// Function to create custom field input based on field type
function createCustomFieldInput(field) {
    let html = '';
    const fieldId = 'new-' + field.field_name;
    
    switch (field.field_type) {
        case 'text':
            // Check if this is a usage code field
            if (field.field_name.startsWith('usage_code')) {
                html = createUsageCodeDropdown(fieldId, '');
            } else {
                html = '<input type="text" class="form-control form-control-sm" id="' + fieldId + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label.toLowerCase() + '">';
            }
            break;
            
        case 'integer':
            html = '<input type="number" class="form-control form-control-sm" id="' + fieldId + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label.toLowerCase() + '">';
            break;
            
        case 'decimal':
            html = '<input type="number" step="0.01" class="form-control form-control-sm" id="' + fieldId + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label.toLowerCase() + '">';
            break;
            
        case 'boolean':
            html = '<select class="form-control form-control-sm" id="' + fieldId + '">';
            html += '<option value="">' + (window.translations?.selectOption || 'Select option') + '</option>';
            html += '<option value="true">' + (window.translations?.yes || 'Yes') + '</option>';
            html += '<option value="false">' + (window.translations?.no || 'No') + '</option>';
            html += '</select>';
            break;
            
        case 'date':
            html = '<input type="date" class="form-control form-control-sm" id="' + fieldId + '">';
            break;
            
        case 'choice':
            html = '<select class="form-control form-control-sm" id="' + fieldId + '">';
            html += '<option value="">' + (window.translations?.selectOption || 'Select option') + '</option>';
            
            // Check if field has typology data
            if (field.typology_choices && field.typology_choices.length > 0) {
                // Use typology choices (array of objects with value and label)
                field.typology_choices.forEach(function(choice) {
                    html += '<option value="' + choice.value + '">' + choice.label + '</option>';
                });
            } else if (field.choices) {
                // Use manual choices (comma-separated string)
                const choices = field.choices.split(',').map(choice => choice.trim());
                choices.forEach(function(choice) {
                    html += '<option value="' + choice + '">' + choice + '</option>';
                });
            }
            html += '</select>';
            break;
            
        default:
            html = '<input type="text" class="form-control form-control-sm" id="' + fieldId + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label.toLowerCase() + '">';
    }
    
    return html;
}

// Initialize map
function initializeMap() {
    map = L.map('map', {
        zoomControl: false,
        scrollWheelZoom: false,
        doubleClickZoom: false,
        boxZoom: false,
        keyboard: false,
        dragging: true,
        touchZoom: true
    }).setView([48.2082, 16.3738], 11); // Vienna coordinates

    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);


    // Load map data
    loadMapData();
}

// Load map data via AJAX
function loadMapData() {
    var url = window.location.origin + '/datasets/' + getDatasetId() + '/map-data/';
    
    fetch(url, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        console.log('Map data loaded:', data);
        // The response contains map_data property
        if (data.map_data) {
            addMarkersToMap(data.map_data);
        } else {
            console.error('No map_data property in response:', data);
            addMarkersToMap([]);
        }
    })
    .catch(error => {
        console.error('Error loading map data:', error);
        // Show error message to user
        var errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger';
        errorDiv.innerHTML = 'Error loading map data. Please refresh the page.';
        document.getElementById('map').appendChild(errorDiv);
    });
}

// Get dataset ID from URL
function getDatasetId() {
    var path = window.location.pathname;
    var matches = path.match(/\/datasets\/(\d+)\//);
    return matches ? matches[1] : null;
}

// Add markers to map
function addMarkersToMap(mapData) {
    // Clear existing markers
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];

    if (!mapData) {
        console.log('No map data provided');
        return;
    }

    if (!Array.isArray(mapData)) {
        console.error('Map data is not an array:', mapData);
        return;
    }

    if (mapData.length === 0) {
        console.log('No map data to display');
        return;
    }

    mapData.forEach(function(point) {
        var marker = L.circleMarker([point.lat, point.lng], {
            radius: 8,
            fillColor: '#0047BB',
            color: '#001A70',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        });

        marker.pointData = point;

        marker.on('click', function() {
            selectPoint(point);
        });

        marker.addTo(map);
        markers.push(marker);
    });

    // Focus on all points
    focusOnAllPoints();
}

// Focus on all points
function focusOnAllPoints() {
    if (markers.length === 0) return;

    var group = new L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.1));
}


// Select a point and show its details
function selectPoint(point) {
    currentPoint = point;
    
    // Update visual selection
    markers.forEach(marker => {
        // Check both pointData and geometryData for compatibility
        var markerId = null;
        if (marker.pointData && marker.pointData.id) {
            markerId = marker.pointData.id;
        } else if (marker.geometryData && marker.geometryData.id) {
            markerId = marker.geometryData.id;
        }
        
        if (markerId === point.id) {
            marker.setStyle({
                fillColor: '#FFB81C',
                color: '#FFB81C'
            });
        } else {
            marker.setStyle({
                fillColor: '#0047BB',
                color: '#001A70'
            });
        }
    });

    // Show geometry details
    showGeometryDetails(point);
}

// Show geometry details
function showGeometryDetails(point) {
    var detailsDiv = document.getElementById('geometryDetails');
    var entriesList = document.getElementById('entriesList');
    
    if (!detailsDiv || !entriesList) return;

    // Update details
    document.getElementById('geometryId').textContent = point.id_kurz;
    document.getElementById('geometryAddress').textContent = point.address;
    document.getElementById('entriesCount').textContent = point.entries_count;

    // Show details section
    detailsDiv.classList.add('active');

    // Generate entries table
    generateEntriesTable(point);
    
    // Adjust column layout
    if (typeof adjustColumnLayout === 'function') {
        adjustColumnLayout();
    }
}

// Generate entries table
function generateEntriesTable(point) {
    var entriesList = document.getElementById('entriesList');
    if (!entriesList) return;

    var entriesHtml = '<div class="table-responsive">';
    entriesHtml += '<table class="table table-sm table-bordered">';
    entriesHtml += '<thead class="table-light">';
    entriesHtml += '<tr>';
    entriesHtml += '<th>Field</th>';
    
    // Show entries based on allowMultipleEntries setting
    var entriesToShow;
    if (window.allowMultipleEntries) {
        // Show up to 3 most recent entries when multiple entries are allowed
        entriesToShow = Math.min(3, point.entries.length);
    } else {
        // Show only 1 entry when multiple entries are not allowed
        entriesToShow = Math.min(1, point.entries.length);
    }
    
    for (var i = 0; i < entriesToShow; i++) {
        entriesHtml += `<th>Entry ${i + 1}</th>`;
    }
    entriesHtml += '<th>New Entry</th>';
    entriesHtml += '</tr>';
    entriesHtml += '</thead>';
    entriesHtml += '<tbody>';
    
    // Sort entries by year (newest first)
    var sortedEntries = point.entries.sort(function(a, b) {
        return (b.year || 0) - (a.year || 0);
    });
    
    // Entry name row
    entriesHtml += '<tr>';
    entriesHtml += '<td><strong>Entry Name</strong></td>';
    for (var i = 0; i < entriesToShow; i++) {
        entriesHtml += `<td>${sortedEntries[i].name || '-'}</td>`;
    }
    entriesHtml += '<td><input type="text" class="form-control form-control-sm" id="new-entry-name" placeholder="Enter entry name" value="' + point.id_kurz + '"></td>';
    entriesHtml += '</tr>';
    
    // Dynamic fields - render all enabled fields
    if (window.allFields && window.allFields.length > 0) {
        const sortedFields = window.allFields.sort((a, b) => a.order - b.order);
        
        sortedFields.forEach(function(field) {
            if (field.enabled) {
                entriesHtml += '<tr>';
                entriesHtml += '<td><strong>' + field.label;
                if (field.required) {
                    entriesHtml += ' <span class="text-danger">*</span>';
                }
                entriesHtml += '</strong></td>';
                
                // Show existing values for each entry
                for (var i = 0; i < entriesToShow; i++) {
                    var value = sortedEntries[i][field.field_name] || '-';
                    entriesHtml += `<td>${value}</td>`;
                }
                
                // Create input for new entry
                entriesHtml += '<td>' + createCustomFieldInput(field) + '</td>';
                entriesHtml += '</tr>';
            }
        });
    } else {
        // Show message when no fields are configured
        entriesHtml += '<tr>';
        entriesHtml += '<td colspan="' + (entriesToShow + 2) + '" class="text-center text-muted">';
        entriesHtml += '<em>No fields configured for this dataset. Please add fields in the dataset configuration.</em>';
        entriesHtml += '</td>';
        entriesHtml += '</tr>';
    }
    
    // Actions row
    entriesHtml += '<tr>';
    entriesHtml += '<td><strong>' + (window.translations?.actions || 'Actions') + '</strong></td>';
    for (var i = 0; i < entriesToShow; i++) {
        entriesHtml += `<td>
            <a href="/entries/${sortedEntries[i].id}/edit/" class="btn btn-outline-secondary btn-sm">${window.translations?.edit || 'Edit'}</a>
        </td>`;
    }
    entriesHtml += '<td>';
    // Only show create button if multiple entries are allowed or no entries exist
    if (window.allowMultipleEntries || !point.entries || point.entries.length === 0) {
        entriesHtml += '<button type="button" class="btn btn-primary btn-sm" onclick="createEntry()">' + (window.translations?.createEntry || 'Create Entry') + '</button>';
    } else {
        entriesHtml += '<span class="text-muted">Only one entry allowed</span>';
    }
    entriesHtml += '</td>';
    entriesHtml += '</tr>';
    
    entriesHtml += '</tbody>';
    entriesHtml += '</table>';
    entriesHtml += '</div>';
    
    // File upload section
    entriesHtml += '<div class="mt-3">';
    entriesHtml += '<label for="photo-upload-new" class="form-label">' + (window.translations?.uploadPhotos || 'Upload Photos') + '</label>';
    entriesHtml += '<div class="input-group">';
    entriesHtml += '<input type="file" class="form-control" id="photo-upload-new" multiple accept="image/*">';
    entriesHtml += '<button class="btn btn-outline-secondary" type="button" disabled>' + (window.translations?.noFilesSelected || 'No files selected') + '</button>';
    entriesHtml += '</div>';
    entriesHtml += '</div>';
    
    entriesList.innerHTML = entriesHtml;
    
    // Copy values from latest entry to new entry fields
    if (currentPoint && currentPoint.entries && currentPoint.entries.length > 0) {
        var sortedEntries = currentPoint.entries.sort(function(a, b) {
            return b.year - a.year;
        });
        var latestEntry = sortedEntries[0];
        
        // Copy values to the new entry fields
        document.getElementById('new-entry-name').value = sortedEntries[0].name || '';
        
        // Populate dynamic fields
        if (allFields && allFields.length > 0) {
            allFields.forEach(function(field) {
                if (field.enabled) {
                    var fieldElement = document.getElementById('new-' + field.field_name);
                    if (fieldElement) {
                        var value = sortedEntries[0][field.field_name] || '';
                        
                        // Handle different field types
                        if (fieldElement.tagName === 'SELECT') {
                            fieldElement.value = value;
                        } else if (fieldElement.type === 'checkbox') {
                            fieldElement.checked = value === 'true' || value === true;
                        } else {
                            fieldElement.value = value;
                        }
                    }
                }
            });
        }
    }
}

// Create new entry
function createEntry() {
    if (!currentPoint) {
        alert('Please select a geometry point first.');
        return;
    }
    
    // Check if multiple entries are allowed
    if (!window.allowMultipleEntries && currentPoint.entries && currentPoint.entries.length > 0) {
        alert('Multiple entries are not allowed for this dataset. Please edit the existing entry instead.');
        return;
    }

    // Collect form data
    var formData = {};
    
    // Add all enabled fields
    if (allFields && allFields.length > 0) {
        allFields.forEach(function(field) {
            if (field.enabled) {
                var fieldElement = document.getElementById('new-' + field.field_name);
                if (fieldElement) {
                    formData[field.field_name] = fieldElement.value;
                }
            }
        });
    }
    
    // Add name field
    formData.name = document.getElementById('new-entry-name').value;
    
    console.log('Form data being sent:', formData);
    console.log('Uploaded files:', uploadedFiles);
    
    // Validate required fields
    if (allFields && allFields.length > 0) {
        for (var i = 0; i < allFields.length; i++) {
            var field = allFields[i];
            if (field.enabled && field.required) {
                var fieldElement = document.getElementById('new-' + field.field_name);
                
                if (!fieldElement || !fieldElement.value) {
                    alert(field.label + ' is a required field.');
                    return;
                }
            }
        }
    }
    
    // Create FormData for file upload
    var formDataObj = new FormData();
    formDataObj.append('geometry_id', currentPoint.id);
    formDataObj.append('name', formData.name);
    
    // Add all field data
    Object.keys(formData).forEach(function(key) {
        if (key !== 'name') {
            formDataObj.append(key, formData[key]);
        }
    });
    
    // Add uploaded files
    uploadedFiles.forEach(function(file, index) {
        formDataObj.append('files', file);
    });
    
    // Add CSRF token
    var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    formDataObj.append('csrfmiddlewaretoken', csrfToken);
    
    // Send request
    fetch(window.location.origin + '/entries/create/' + currentPoint.id + '/', {
        method: 'POST',
        body: formDataObj,
        credentials: 'same-origin'
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        } else {
            throw new Error('Network response was not ok');
        }
    })
    .then(data => {
        console.log('Entry created successfully:', data);
        alert('Entry created successfully!');
        
        // Clear form
        document.getElementById('new-entry-name').value = '';
        if (allFields && allFields.length > 0) {
            allFields.forEach(function(field) {
                if (field.enabled) {
                    var fieldElement = document.getElementById('new-' + field.field_name);
                    if (fieldElement) {
                        if (fieldElement.tagName === 'SELECT') {
                            fieldElement.selectedIndex = 0;
                        } else if (fieldElement.type === 'checkbox') {
                            fieldElement.checked = false;
                        } else {
                            fieldElement.value = '';
                        }
                    }
                }
            });
        }
        
        // Clear uploaded files
        uploadedFiles = [];
        document.getElementById('photo-upload-new').value = '';
        var button = document.querySelector('#photo-upload-new').nextElementSibling;
        button.textContent = 'No files selected';
        button.className = 'btn btn-outline-secondary';
        
        // Reload map data to show new entry
        loadMapData();
    })
    .catch(error => {
        console.error('Error creating entry:', error);
        alert('Error creating entry: ' + error.message);
    });
}

// Setup event listeners
function setupEventListeners() {
    // File upload functionality
    document.addEventListener('change', function(e) {
        if (e.target && (e.target.id === 'photo-upload-new' || e.target.id === 'photo-upload-first')) {
            var files = e.target.files;
            if (files.length > 0) {
                // Store the files for later upload
                for (var i = 0; i < files.length; i++) {
                    uploadedFiles.push(files[i]);
                }
                
                // Update button text to show files selected
                var button = e.target.nextElementSibling;
                button.textContent = 'Photo Selected (' + files.length + ')';
                button.className = 'btn btn-success btn-sm';
                
                // Show preview if it's an image
                if (files[0].type.startsWith('image/')) {
                    var reader = new FileReader();
                    reader.onload = function(e) {
                        // Create a small preview
                        var preview = document.createElement('div');
                        preview.className = 'mt-2';
                        preview.innerHTML = '<img src="' + e.target.result + '" style="max-width: 100px; max-height: 100px; border-radius: 4px;">';
                        button.parentNode.appendChild(preview);
                    };
                    reader.readAsDataURL(files[0]);
                }
            }
        }
    });
    
    // Map control buttons
    document.addEventListener('click', function(e) {
        if (e.target && e.target.id === 'focusAllBtn') {
            focusOnAllPoints();
        } else if (e.target && e.target.id === 'myLocationBtn') {
            zoomToMyLocation();
        } else if (e.target && e.target.id === 'zoomInBtn') {
            if (map) {
                map.zoomIn();
            }
        } else if (e.target && e.target.id === 'zoomOutBtn') {
            if (map) {
                map.zoomOut();
            }
        }
    });
}

// Clear selection and hide geometry details
function clearSelection() {
    currentPoint = null;
    
    // Reset marker styles
    markers.forEach(marker => {
        marker.setStyle({
            fillColor: '#0047BB',
            color: '#001A70'
        });
    });
    
    // Hide geometry details
    var detailsDiv = document.getElementById('geometryDetails');
    if (detailsDiv) {
        detailsDiv.classList.remove('active');
        
        // Reset details content
        document.getElementById('geometryId').textContent = '-';
        document.getElementById('geometryAddress').textContent = '-';
        document.getElementById('entriesCount').textContent = '-';
        document.getElementById('entriesList').innerHTML = '';
        
        // Adjust column layout
        if (typeof adjustColumnLayout === 'function') {
            adjustColumnLayout();
        }
    }
}

// Function to adjust column layout based on content
function adjustColumnLayout() {
    var mapColumn = document.getElementById('mapColumn');
    var detailsColumn = document.getElementById('detailsColumn');
    var geometryDetails = document.getElementById('geometryDetails');
    
    if (!mapColumn || !detailsColumn || !geometryDetails) return;
    
    // Check if geometry details section has meaningful content
    var hasContent = geometryDetails.classList.contains('active') && 
                    (document.getElementById('geometryId').textContent !== '-' || 
                     document.getElementById('geometryAddress').textContent !== '-' ||
                     document.getElementById('entriesCount').textContent !== '-');
    
    if (hasContent) {
        // Show both columns with normal layout
        mapColumn.className = 'col-md-8';
        detailsColumn.className = 'col-md-4';
    } else {
        // Hide details column and make map full width
        mapColumn.className = 'col-md-12';
        detailsColumn.className = 'col-md-4 d-none';
    }
}

// Initialize responsive layout functionality
function initializeResponsiveLayout() {
    // Set up observer to watch for changes in geometry details
    var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                adjustColumnLayout();
            }
        });
    });
    
    // Start observing the geometry details element
    var geometryDetails = document.getElementById('geometryDetails');
    if (geometryDetails) {
        observer.observe(geometryDetails, { attributes: true });
    }
    
    // Initial layout adjustment
    adjustColumnLayout();
}

// Focus on all points on the map
function focusOnAllPoints() {
    if (!map || markers.length === 0) {
        console.log('No map or markers available');
        return;
    }
    
    var group = new L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.1));
}

// Zoom to user's current location
function zoomToMyLocation() {
    if (!navigator.geolocation) {
        alert(window.translations?.geolocationNotSupported || 'Geolocation is not supported by this browser.');
        return;
    }
    
    navigator.geolocation.getCurrentPosition(
        function(position) {
            var lat = position.coords.latitude;
            var lng = position.coords.longitude;
            
            map.setView([lat, lng], 15);
            
            // Add a marker for current location
            L.marker([lat, lng], {
                icon: L.divIcon({
                    className: 'current-location-marker',
                    html: '<i class="bi bi-geo-fill" style="color: #FF6B6B; font-size: 20px;"></i>',
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                })
            }).addTo(map);
        },
        function(error) {
            var errorMessage = window.translations?.geolocationError || 'Error getting your location: ';
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    errorMessage += 'Permission denied';
                    break;
                case error.POSITION_UNAVAILABLE:
                    errorMessage += 'Position unavailable';
                    break;
                case error.TIMEOUT:
                    errorMessage += 'Request timeout';
                    break;
                default:
                    errorMessage += 'Unknown error';
                    break;
            }
            alert(errorMessage);
        }
    );
}

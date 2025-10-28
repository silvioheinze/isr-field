// Global variables
var map;
var currentPoint = null;
var allFields = [];
var uploadedFiles = [];
var typologyData = null;
var markers = [];

// Initialize the data input functionality
function initializeDataInput(typologyDataParam, fieldsData) {
    allFields = fieldsData || [];
    typologyData = typologyDataParam;
    
    // Initialize the map
    initializeMap();
    
    // Setup event listeners
    setupEventListeners();
    
    // Initialize file upload
    initializeFileUpload();
    
    // Initialize responsive layout
    if (typeof initializeResponsiveLayout === 'function') {
        initializeResponsiveLayout();
    }
}

// Initialize the map
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
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Load map data
    loadMapData();
}

// Load map data via AJAX
function loadMapData() {
    var url = window.location.origin + '/datasets/' + getDatasetId() + '/map-data/';
    console.log('Loading map data from:', url);
    
    fetch(url, {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        }
    })
    .then(response => {
        console.log('Response status:', response.status);
        if (!response.ok) {
            throw new Error('Network response was not ok: ' + response.status);
        }
        return response.json();
    })
    .then(data => {
        console.log('Map data received:', data);
        if (data.map_data) {
            console.log('Number of map points:', data.map_data.length);
            addMarkersToMap(data.map_data);
        } else {
            console.error('No map data received');
        }
    })
    .catch(error => {
        console.error('Error loading map data:', error);
    });
}

// Add markers to the map
function addMarkersToMap(mapData) {
    console.log('addMarkersToMap called with:', mapData);
    
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
    
    console.log('Adding', mapData.length, 'markers to map');

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

// Focus on all points on the map
function focusOnAllPoints() {
    if (!map || markers.length === 0) {
        console.log('No map or markers available');
        return;
    }
    
    var group = new L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.1));
}

// Select a point and show its details
function selectPoint(point) {
    currentPoint = point;
    
    // Update visual selection
    markers.forEach(marker => {
        if (marker.pointData.id === point.id) {
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
    currentPoint = point;
    
    // Update geometry info (no longer needed)
    
    // Show details section
    var detailsDiv = document.getElementById('geometryDetails');
    detailsDiv.classList.add('active');
    
    // Generate entries table
    generateEntriesTable(point);
    
    // Load uploaded files for this geometry
    loadUploadedFiles();
    
    // Adjust column layout
    if (typeof adjustColumnLayout === 'function') {
        adjustColumnLayout();
    }
}

// Generate entries table
function generateEntriesTable(point) {
    var entriesList = document.getElementById('entriesList');
    if (!entriesList) return;

    var entriesHtml = '';
    
    // Sort entries by year (newest first)
    var sortedEntries = point.entries.sort(function(a, b) {
        return (b.year || 0) - (a.year || 0);
    });
    
    // Show entries based on allowMultipleEntries setting
    var entriesToShow;
    if (window.allowMultipleEntries) {
        // Show up to 3 most recent entries when multiple entries are allowed
        entriesToShow = Math.min(3, point.entries.length);
    } else {
        // Show only 1 entry when multiple entries are not allowed
        entriesToShow = Math.min(1, point.entries.length);
    }
    
    // Create forms for each entry
    for (var entryIndex = 0; entryIndex < entriesToShow; entryIndex++) {
        var entry = sortedEntries[entryIndex];
        if (!entry) continue;
        
        entriesHtml += '<div class="card mb-3">';
        entriesHtml += '<div class="card-header d-flex justify-content-between align-items-center">';
        entriesHtml += '<h6 class="mb-0">' + (entry.name || 'Unnamed Entry') + ' (' + (entry.year || 'No Year') + ')</h6>';
        entriesHtml += '<small class="text-muted">Entry ' + (entryIndex + 1) + '</small>';
        entriesHtml += '</div>';
        entriesHtml += '<div class="card-body">';
        
        // Create form for this entry
        entriesHtml += '<form class="entry-form" data-entry-id="' + entry.id + '">';
        
        // Dynamic fields - render all configured fields from window.allFields
        if (window.allFields && window.allFields.length > 0) {
            // Sort fields by order
            var sortedFields = window.allFields.sort(function(a, b) {
                return (a.order || 0) - (b.order || 0);
            });
            
            // Check if there are any enabled fields
            var hasEnabledFields = sortedFields.some(function(field) {
                return field.enabled;
            });
            
            if (hasEnabledFields) {
                sortedFields.forEach(function(field) {
                    if (field.enabled) {
                    var value = '';
                    if (entry[field.field_name] !== undefined) {
                        value = entry[field.field_name];
                    }
                    
                    entriesHtml += '<div class="mb-3">';
                    entriesHtml += '<label for="field_' + field.field_name + '_' + entryIndex + '" class="form-label">';
                    entriesHtml += field.label;
                    if (field.required) {
                        entriesHtml += ' <span class="text-danger">*</span>';
                    }
                    entriesHtml += '</label>';
                    
                    // Create input based on field type and settings
                    var inputHtml = createFormFieldInput(field, value, entryIndex);
                    entriesHtml += inputHtml;
                    
                    // Add help text if available
                    if (field.help_text) {
                        entriesHtml += '<div class="form-text">' + field.help_text + '</div>';
                    }
                    
                    entriesHtml += '</div>';
                    }
                });
            } else {
                entriesHtml += '<div class="alert alert-info">';
                entriesHtml += '<i class="bi bi-info-circle"></i> No fields configured for this dataset.';
                entriesHtml += '</div>';
            }
        } else {
            entriesHtml += '<div class="alert alert-info">';
            entriesHtml += '<i class="bi bi-info-circle"></i> No fields configured for this dataset.';
            entriesHtml += '</div>';
        }
        
        entriesHtml += '</form>';
        entriesHtml += '</div>';
        entriesHtml += '</div>';
    }
    
    // Add new entry form if multiple entries are allowed or no entries exist
    if (window.allowMultipleEntries || !point.entries || point.entries.length === 0) {
        entriesHtml += '<div class="card mb-3 new-entry-form">';
        entriesHtml += '<div class="card-header">';
        entriesHtml += '<h6 class="mb-0">' + (window.translations?.createEntry || 'Create New Entry') + '</h6>';
        entriesHtml += '</div>';
        entriesHtml += '<div class="card-body">';
        
        // Entry name field
        entriesHtml += '<div class="mb-3">';
        entriesHtml += '<label for="new-entry-name" class="form-label">Entry Name <span class="text-danger">*</span></label>';
        entriesHtml += '<input type="text" class="form-control" id="new-entry-name" placeholder="Enter entry name" value="' + point.id_kurz + '">';
        entriesHtml += '</div>';
        
        // Dynamic fields for new entry
        if (window.allFields && window.allFields.length > 0) {
            // Sort fields by order
            var sortedFields = window.allFields.sort(function(a, b) {
                return (a.order || 0) - (b.order || 0);
            });
            
            // Check if there are any enabled fields
            var hasEnabledFields = sortedFields.some(function(field) {
                return field.enabled;
            });
            
            if (hasEnabledFields) {
                sortedFields.forEach(function(field) {
                    if (field.enabled) {
                    entriesHtml += '<div class="mb-3">';
                    entriesHtml += '<label for="field_' + field.field_name + '" class="form-label">';
                    entriesHtml += field.label;
                    if (field.required) {
                        entriesHtml += ' <span class="text-danger">*</span>';
                    }
                    entriesHtml += '</label>';
                    
                    // Create input based on field type and settings
                    var inputHtml = createFormFieldInput(field, '', -1); // -1 indicates new entry
                    entriesHtml += inputHtml;
                    
                    // Add help text if available
                    if (field.help_text) {
                        entriesHtml += '<div class="form-text">' + field.help_text + '</div>';
                    }
                    
                    entriesHtml += '</div>';
                    }
                });
            } else {
                entriesHtml += '<div class="alert alert-info">';
                entriesHtml += '<i class="bi bi-info-circle"></i> No fields configured for this dataset.';
                entriesHtml += '</div>';
            }
        } else {
            entriesHtml += '<div class="alert alert-info">';
            entriesHtml += '<i class="bi bi-info-circle"></i> No fields configured for this dataset.';
            entriesHtml += '</div>';
        }
        
        entriesHtml += '</div>';
        entriesHtml += '</div>';
    }
    
    // Add action buttons
    entriesHtml += '<div class="mt-3 d-flex gap-2">';
    if (window.allowMultipleEntries || !point.entries || point.entries.length === 0) {
        entriesHtml += '<button type="button" class="btn btn-primary" onclick="createEntry()">';
        entriesHtml += '<i class="bi bi-plus-circle"></i> ' + (window.translations?.createEntry || 'Create Entry');
        entriesHtml += '</button>';
    }
    if (point.entries && point.entries.length > 0) {
        entriesHtml += '<button type="button" class="btn btn-success" onclick="saveEntries()">';
        entriesHtml += '<i class="bi bi-save"></i> ' + (window.translations?.saveEntries || 'Save Changes');
        entriesHtml += '</button>';
    }
    entriesHtml += '</div>';
    
    entriesList.innerHTML = entriesHtml;
}

// Create form field input based on field configuration
function createFormFieldInput(field, value, entryIndex) {
    var inputHtml = '';
    var fieldId = 'field_' + field.field_name;
    var fieldName = 'fields[' + field.field_name + ']';
    var fieldValue = value || '';
    
    // Add entry index to field name and ID for existing entries
    if (entryIndex >= 0) {
        fieldId += '_' + entryIndex;
        fieldName = 'fields[' + field.field_name + '][' + entryIndex + ']';
    }
    
    switch (field.field_type) {
        case 'text':
            inputHtml = '<input type="text" class="form-control" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (field.placeholder || 'Enter ' + field.label) + '"';
            if (field.required) inputHtml += ' required';
            if (field.max_length) inputHtml += ' maxlength="' + field.max_length + '"';
            inputHtml += '>';
            break;
            
        case 'textarea':
            inputHtml = '<textarea class="form-control" id="' + fieldId + '" name="' + fieldName + '" placeholder="' + (field.placeholder || 'Enter ' + field.label) + '"';
            if (field.required) inputHtml += ' required';
            if (field.max_length) inputHtml += ' maxlength="' + field.max_length + '"';
            if (field.rows) inputHtml += ' rows="' + field.rows + '"';
            inputHtml += '>' + fieldValue + '</textarea>';
            break;
            
        case 'integer':
            inputHtml = '<input type="number" class="form-control" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (field.placeholder || 'Enter ' + field.label) + '"';
            if (field.required) inputHtml += ' required';
            if (field.min_value !== undefined) inputHtml += ' min="' + field.min_value + '"';
            if (field.max_value !== undefined) inputHtml += ' max="' + field.max_value + '"';
            inputHtml += '>';
            break;
            
        case 'float':
            inputHtml = '<input type="number" step="0.01" class="form-control" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (field.placeholder || 'Enter ' + field.label) + '"';
            if (field.required) inputHtml += ' required';
            if (field.min_value !== undefined) inputHtml += ' min="' + field.min_value + '"';
            if (field.max_value !== undefined) inputHtml += ' max="' + field.max_value + '"';
            inputHtml += '>';
            break;
            
        case 'boolean':
            inputHtml = '<select class="form-select" id="' + fieldId + '" name="' + fieldName + '"';
            if (field.required) inputHtml += ' required';
            inputHtml += '>';
            inputHtml += '<option value="">' + (field.placeholder || 'Select option') + '</option>';
            inputHtml += '<option value="true"' + (fieldValue === 'true' || fieldValue === true ? ' selected' : '') + '>' + (field.true_label || 'Yes') + '</option>';
            inputHtml += '<option value="false"' + (fieldValue === 'false' || fieldValue === false ? ' selected' : '') + '>' + (field.false_label || 'No') + '</option>';
            inputHtml += '</select>';
            break;
            
        case 'choice':
            inputHtml = '<select class="form-select" id="' + fieldId + '" name="' + fieldName + '"';
            if (field.required) inputHtml += ' required';
            inputHtml += '>';
            inputHtml += '<option value="">' + (field.placeholder || 'Select option') + '</option>';
            
            if (field.typology_choices && field.typology_choices.length > 0) {
                field.typology_choices.forEach(function(choice) {
                    var selected = (fieldValue === choice) ? ' selected' : '';
                    inputHtml += '<option value="' + choice + '"' + selected + '>' + choice + '</option>';
                });
            } else if (field.choices) {
                var choices = field.choices.split(',').map(function(choice) { return choice.trim(); });
                choices.forEach(function(choice) {
                    var selected = (fieldValue === choice) ? ' selected' : '';
                    inputHtml += '<option value="' + choice + '"' + selected + '>' + choice + '</option>';
                });
            }
            inputHtml += '</select>';
            break;
            
        case 'date':
            inputHtml = '<input type="date" class="form-control" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '"';
            if (field.required) inputHtml += ' required';
            if (field.min_date) inputHtml += ' min="' + field.min_date + '"';
            if (field.max_date) inputHtml += ' max="' + field.max_date + '"';
            inputHtml += '>';
            break;
            
        case 'datetime':
            inputHtml = '<input type="datetime-local" class="form-control" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '"';
            if (field.required) inputHtml += ' required';
            if (field.min_date) inputHtml += ' min="' + field.min_date + '"';
            if (field.max_date) inputHtml += ' max="' + field.max_date + '"';
            inputHtml += '>';
            break;
            
        case 'time':
            inputHtml = '<input type="time" class="form-control" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '"';
            if (field.required) inputHtml += ' required';
            inputHtml += '>';
            break;
            
        case 'email':
            inputHtml = '<input type="email" class="form-control" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (field.placeholder || 'Enter email address') + '"';
            if (field.required) inputHtml += ' required';
            inputHtml += '>';
            break;
            
        case 'url':
            inputHtml = '<input type="url" class="form-control" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (field.placeholder || 'Enter URL') + '"';
            if (field.required) inputHtml += ' required';
            inputHtml += '>';
            break;
            
        case 'phone':
            inputHtml = '<input type="tel" class="form-control" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (field.placeholder || 'Enter phone number') + '"';
            if (field.required) inputHtml += ' required';
            inputHtml += '>';
            break;
            
        default:
            inputHtml = '<input type="text" class="form-control" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (field.placeholder || 'Enter ' + field.label) + '"';
            if (field.required) inputHtml += ' required';
            inputHtml += '>';
    }
    
    return inputHtml;
}

// Create custom field input
function createCustomFieldInput(field) {
    var inputHtml = '';
    var fieldId = 'field_' + field.field_name;
    var fieldName = 'fields[' + field.field_name + ']';
    var fieldValue = '';
    
    switch (field.field_type) {
        case 'text':
            inputHtml = '<input type="text" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label + '">';
            break;
        case 'integer':
            inputHtml = '<input type="number" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label + '">';
            break;
        case 'float':
            inputHtml = '<input type="number" step="0.01" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label + '">';
            break;
        case 'boolean':
            inputHtml = '<select class="form-select form-select-sm" id="' + fieldId + '" name="' + fieldName + '">';
            inputHtml += '<option value="">' + (window.translations?.selectOption || 'Select option') + '</option>';
            inputHtml += '<option value="true">' + (window.translations?.yes || 'Yes') + '</option>';
            inputHtml += '<option value="false">' + (window.translations?.no || 'No') + '</option>';
            inputHtml += '</select>';
            break;
        case 'choice':
            if (field.typology_choices && field.typology_choices.length > 0) {
                inputHtml = '<select class="form-select form-select-sm" id="' + fieldId + '" name="' + fieldName + '">';
                inputHtml += '<option value="">' + (window.translations?.selectOption || 'Select option') + '</option>';
                field.typology_choices.forEach(function(choice) {
                    inputHtml += '<option value="' + choice + '">' + choice + '</option>';
                });
                inputHtml += '</select>';
            } else if (field.choices) {
                var choices = field.choices.split(',').map(function(choice) { return choice.trim(); });
                inputHtml = '<select class="form-select form-select-sm" id="' + fieldId + '" name="' + fieldName + '">';
                inputHtml += '<option value="">' + (window.translations?.selectOption || 'Select option') + '</option>';
                choices.forEach(function(choice) {
                    inputHtml += '<option value="' + choice + '">' + choice + '</option>';
                });
                inputHtml += '</select>';
            } else {
                inputHtml = '<input type="text" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label + '">';
            }
            break;
        case 'date':
            inputHtml = '<input type="date" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '">';
            break;
        default:
            inputHtml = '<input type="text" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label + '">';
    }
    
    return inputHtml;
}

// Create editable field input for existing entries
function createEditableFieldInput(field, value, entryIndex) {
    var inputHtml = '';
    var fieldId = 'field_' + field.field_name + '_' + entryIndex;
    var fieldName = 'fields[' + field.field_name + '][' + entryIndex + ']';
    var fieldValue = value || '';
    
    switch (field.field_type) {
        case 'text':
            inputHtml = '<input type="text" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label + '">';
            break;
        case 'integer':
            inputHtml = '<input type="number" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label + '">';
            break;
        case 'float':
            inputHtml = '<input type="number" step="0.01" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label + '">';
            break;
        case 'boolean':
            inputHtml = '<select class="form-select form-select-sm" id="' + fieldId + '" name="' + fieldName + '">';
            inputHtml += '<option value="">' + (window.translations?.selectOption || 'Select option') + '</option>';
            inputHtml += '<option value="true"' + (fieldValue === 'true' || fieldValue === true ? ' selected' : '') + '>' + (window.translations?.yes || 'Yes') + '</option>';
            inputHtml += '<option value="false"' + (fieldValue === 'false' || fieldValue === false ? ' selected' : '') + '>' + (window.translations?.no || 'No') + '</option>';
            inputHtml += '</select>';
            break;
        case 'choice':
            if (field.typology_choices && field.typology_choices.length > 0) {
                inputHtml = '<select class="form-select form-select-sm" id="' + fieldId + '" name="' + fieldName + '">';
                inputHtml += '<option value="">' + (window.translations?.selectOption || 'Select option') + '</option>';
                field.typology_choices.forEach(function(choice) {
                    var selected = (fieldValue === choice) ? ' selected' : '';
                    inputHtml += '<option value="' + choice + '"' + selected + '>' + choice + '</option>';
                });
                inputHtml += '</select>';
            } else if (field.choices) {
                var choices = field.choices.split(',').map(function(choice) { return choice.trim(); });
                inputHtml = '<select class="form-select form-select-sm" id="' + fieldId + '" name="' + fieldName + '">';
                inputHtml += '<option value="">' + (window.translations?.selectOption || 'Select option') + '</option>';
                choices.forEach(function(choice) {
                    var selected = (fieldValue === choice) ? ' selected' : '';
                    inputHtml += '<option value="' + choice + '"' + selected + '>' + choice + '</option>';
                });
                inputHtml += '</select>';
            } else {
                inputHtml = '<input type="text" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label + '">';
            }
            break;
        case 'date':
            inputHtml = '<input type="date" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '">';
            break;
        default:
            inputHtml = '<input type="text" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label + '">';
    }
    
    return inputHtml;
}

// Create entry
function createEntry() {
    if (!currentPoint) {
        alert('Please select a geometry point first.');
        return;
    }
    
    if (!window.allowMultipleEntries && currentPoint.entries && currentPoint.entries.length > 0) {
        alert('Multiple entries are not allowed for this dataset. Please edit the existing entry instead.');
        return;
    }
    
    var entryName = document.getElementById('new-entry-name').value;
    if (!entryName) {
        alert('Please enter an entry name.');
        return;
    }
    
    var formData = new FormData();
    formData.append('name', entryName);
    formData.append('geometry_id', currentPoint.id);
    formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
    
    // Add field values
    if (window.allFields && window.allFields.length > 0) {
        window.allFields.forEach(function(field) {
            if (field.enabled) {
                var fieldElement = document.getElementById('field_' + field.field_name);
                if (fieldElement) {
                    formData.append('fields[' + field.field_name + ']', fieldElement.value);
                }
            }
        });
    }
    
    fetch(window.location.origin + '/entries/create/', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Clear form
            document.getElementById('new-entry-name').value = '';
            if (window.allFields && window.allFields.length > 0) {
                window.allFields.forEach(function(field) {
                    if (field.enabled) {
                        var fieldElement = document.getElementById('field_' + field.field_name);
                        if (fieldElement) {
                            if (fieldElement.tagName === 'SELECT') {
                                fieldElement.selectedIndex = 0;
                            } else {
                                fieldElement.value = '';
                            }
                        }
                    }
                });
            }
            
            // Reset file upload button
            var button = document.querySelector('#photo-upload-new').nextElementSibling;
            button.textContent = 'No files selected';
            button.className = 'btn btn-outline-secondary';
            
            // Reload map data to show new entry
            loadMapData();
        } else {
            alert('Error creating entry: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error creating entry:', error);
        alert('Error creating entry: ' + error.message);
    });
}

// Save entries
function saveEntries() {
    if (!currentPoint) {
        alert('Please select a geometry point first.');
        return;
    }
    
    if (!currentPoint.entries || currentPoint.entries.length === 0) {
        alert('No entries to save.');
        return;
    }
    
    var formData = new FormData();
    formData.append('geometry_id', currentPoint.id);
    formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
    
    // Add field values for each entry
    if (window.allFields && window.allFields.length > 0) {
        for (var i = 0; i < currentPoint.entries.length; i++) {
            var entry = currentPoint.entries[i];
            formData.append('entries[' + i + '][id]', entry.id);
            
            window.allFields.forEach(function(field) {
                if (field.enabled) {
                    var fieldElement = document.getElementById('field_' + field.field_name + '_' + i);
                    if (fieldElement) {
                        formData.append('entries[' + i + '][fields][' + field.field_name + ']', fieldElement.value);
                    }
                }
            });
        }
    }
    
    // Show loading state
    var saveBtn = document.querySelector('button[onclick="saveEntries()"]');
    var originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Saving...';
    saveBtn.disabled = true;
    
    fetch(window.location.origin + '/entries/save/', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Entries saved successfully!');
            // Reload map data to show updated entries
            loadMapData();
        } else {
            alert('Error saving entries: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error saving entries:', error);
        alert('Error saving entries: ' + error.message);
    })
    .finally(() => {
        // Reset button state
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    });
}

// Setup event listeners
function setupEventListeners() {
    // File upload functionality
    document.addEventListener('change', function(e) {
        if (e.target.type === 'file') {
            var files = e.target.files;
            var button = e.target.nextElementSibling;
            if (files.length > 0) {
                button.textContent = files.length + ' file(s) selected';
                button.className = 'btn btn-success';
            } else {
                button.textContent = 'No files selected';
                button.className = 'btn btn-outline-secondary';
            }
        }
    });
    
    // Map control buttons
    document.getElementById('focusAllBtn').addEventListener('click', focusOnAllPoints);
    document.getElementById('myLocationBtn').addEventListener('click', zoomToMyLocation);
    document.getElementById('zoomInBtn').addEventListener('click', function() {
        map.zoomIn();
    });
    document.getElementById('zoomOutBtn').addEventListener('click', function() {
        map.zoomOut();
    });
}

// Focus on all points
function focusOnAllPoints() {
    if (!map || markers.length === 0) {
        console.log('No map or markers available');
        return;
    }
    
    var group = new L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.1));
}

// Zoom to my location
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

// Clear selection
function clearSelection() {
    currentPoint = null;
    var detailsDiv = document.getElementById('geometryDetails');
    detailsDiv.classList.remove('active');
    
    // Clear geometry info
    document.getElementById('geometryId').textContent = '-';
    document.getElementById('geometryAddress').textContent = '-';
    document.getElementById('entriesCount').textContent = '-';
    
    // Clear entries list
    document.getElementById('entriesList').innerHTML = '';
    
    // Adjust column layout
    if (typeof adjustColumnLayout === 'function') {
        adjustColumnLayout();
    }
}

// Get dataset ID from URL
function getDatasetId() {
    var path = window.location.pathname;
    var matches = path.match(/\/datasets\/(\d+)\//);
    return matches ? matches[1] : null;
}

// Adjust column layout based on content
function adjustColumnLayout() {
    var mapColumn = document.getElementById('mapColumn');
    var detailsColumn = document.getElementById('detailsColumn');
    var geometryDetails = document.getElementById('geometryDetails');
    
    if (geometryDetails && geometryDetails.classList.contains('active')) {
        // Show both columns when geometry details are visible
        mapColumn.className = 'col-md-8';
        detailsColumn.className = 'col-md-4';
    } else {
        // Show only map column when no geometry is selected
        mapColumn.className = 'col-md-12';
        detailsColumn.className = 'col-md-4 d-none';
    }
}

// Initialize responsive layout
function initializeResponsiveLayout() {
    // Initial layout adjustment
    adjustColumnLayout();
    
    // Listen for window resize
    window.addEventListener('resize', adjustColumnLayout);
}

// File upload functionality
function initializeFileUpload() {
    const fileUploadForm = document.getElementById('fileUploadForm');
    if (!fileUploadForm) return;
    
    fileUploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        uploadFiles();
    });
}

function uploadFiles() {
    if (!currentPoint) {
        alert('Please select a geometry point first.');
        return;
    }
    
    const fileInput = document.getElementById('fileInput');
    const files = fileInput.files;
    
    if (files.length === 0) {
        alert('Please select at least one image to upload.');
        return;
    }
    
    // Validate that all files are images
    for (let i = 0; i < files.length; i++) {
        if (!files[i].type.startsWith('image/')) {
            alert('Please select only image files.');
            return;
        }
    }
    
    const formData = new FormData();
    formData.append('geometry_id', currentPoint.id);
    
    // Add all selected files
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    // Show loading state
    const submitBtn = document.querySelector('#fileUploadForm button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Uploading...';
    submitBtn.disabled = true;
    
    // Get CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch('/datasets/upload-files/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Images uploaded successfully!');
            // Clear form
            fileInput.value = '';
            // Refresh files list
            loadUploadedFiles();
        } else {
            alert('Error uploading images: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        alert('Error uploading images. Please try again.');
    })
    .finally(() => {
        // Reset button state
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

function loadUploadedFiles() {
    if (!currentPoint) return;
    
    const filesList = document.getElementById('filesList');
    if (!filesList) return;
    
    // Get CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch(`/datasets/geometry/${currentPoint.id}/files/`, {
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayUploadedFiles(data.files);
        } else {
            filesList.innerHTML = '<p class="text-muted">Error loading files.</p>';
        }
    })
    .catch(error => {
        console.error('Error loading files:', error);
        filesList.innerHTML = '<p class="text-muted">Error loading files.</p>';
    });
}

function displayUploadedFiles(files) {
    const filesList = document.getElementById('filesList');
    if (!filesList) return;
    
    if (files.length === 0) {
        filesList.innerHTML = '<p class="text-muted">No files uploaded yet.</p>';
        return;
    }
    
    let html = '<div class="list-group">';
    files.forEach(file => {
        const fileIcon = getFileIcon(file.file_type);
        const fileSize = formatFileSize(file.file_size);
        const uploadDate = new Date(file.uploaded_at).toLocaleDateString();
        
        html += `
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <i class="${fileIcon} me-2"></i>
                    <strong>${file.original_name}</strong>
                    <small class="text-muted ms-2">(${fileSize})</small>
                    <br><small class="text-muted">Uploaded: ${uploadDate}</small>
                </div>
                <div>
                    <a href="${file.download_url}" class="btn btn-sm btn-outline-primary me-1" title="Download">
                        <i class="bi bi-download"></i>
                    </a>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteFile(${file.id})" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    filesList.innerHTML = html;
}

function getFileIcon(fileType) {
    if (fileType.startsWith('image/')) {
        return 'bi bi-image';
    } else if (fileType === 'application/pdf') {
        return 'bi bi-file-pdf';
    } else if (fileType.includes('word') || fileType.includes('document')) {
        return 'bi bi-file-word';
    } else if (fileType.includes('text')) {
        return 'bi bi-file-text';
    } else {
        return 'bi bi-file';
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function deleteFile(fileId) {
    if (!confirm('Are you sure you want to delete this file?')) {
        return;
    }
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch(`/datasets/files/${fileId}/delete/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('File deleted successfully!');
            loadUploadedFiles(); // Refresh the list
        } else {
            alert('Error deleting file: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Delete error:', error);
        alert('Error deleting file. Please try again.');
    });
}
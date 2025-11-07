// Global variables
var map;
var currentPoint = null;
var allFields = [];
var uploadedFiles = [];
var typologyData = null;
var markers = [];
var addPointMode = false;
var addPointMarker = null;
var lastAddedLatLng = null;

function escapeHtml(value) {
    if (value === null || value === undefined) {
        return '';
    }
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function normalizeFieldChoices(field) {
    var options = [];
    if (field && Array.isArray(field.typology_choices) && field.typology_choices.length > 0) {
        field.typology_choices.forEach(function(choice) {
            if (choice === null || choice === undefined) return;
            if (typeof choice === 'object') {
                var rawValue = choice.value !== undefined ? choice.value : (choice.code !== undefined ? choice.code : '');
                var label = choice.label || choice.name || rawValue;
                if (rawValue !== undefined && rawValue !== null && label !== undefined && label !== null) {
                    options.push({
                        value: String(rawValue),
                        label: String(label)
                    });
                }
            } else {
                options.push({
                    value: String(choice),
                    label: String(choice)
                });
            }
        });
    } else if (field && field.choices) {
        var rawChoices = Array.isArray(field.choices) ? field.choices : field.choices.split(',');
        rawChoices.forEach(function(choice) {
            if (choice === null || choice === undefined) return;
            var trimmed = typeof choice === 'string' ? choice.trim() : choice;
            if (trimmed !== '') {
                options.push({
                    value: String(trimmed),
                    label: String(trimmed)
                });
            }
        });
    }
    return options;
}

// Initialize the data input functionality
function initializeDataInput(typologyDataParam, fieldsData) {
    allFields = fieldsData || [];
    window.allFields = fieldsData || [];
    typologyData = typologyDataParam;

    initializeMap();
    setupEventListeners();
    initializeFileUpload();
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
    }).setView([48.2082, 16.3738], 11);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    map.on('click', function(e) {
        if (addPointMode) addNewPoint(e.latlng);
    });

    loadMapData();
}

// Load map data via AJAX
function loadMapData() {
    var url = window.location.origin + '/datasets/' + getDatasetId() + '/map-data/';
    fetch(url, {
        method: 'GET',
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.map_data) addMarkersToMap(data.map_data);
    })
    .catch(() => {});
}

// Load fields from API when window.allFields is empty
function loadFieldsFromAPI() {
    var pathParts = window.location.pathname.split('/');
    var datasetId = null;
    for (var i = 0; i < pathParts.length; i++) {
        if (pathParts[i] === 'datasets' && i + 1 < pathParts.length) {
            datasetId = pathParts[i + 1];
            break;
        }
    }
    
    if (!datasetId) {
        console.error('Could not determine dataset ID from URL');
        return;
    }
    
    var url = window.location.origin + '/datasets/' + datasetId + '/fields/';
    
    fetch(url, {
        method: 'GET',
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.fields) {
            window.allFields = data.fields;
            allFields = data.fields;
            
            if (currentPoint) {
                showGeometryDetails(currentPoint);
            }
        } else {
            console.error('No fields in API response');
        }
    })
    .catch(error => {
        console.error('Error loading fields from API:', error);
        var entriesList = document.getElementById('entriesList');
        if (entriesList) {
            entriesList.innerHTML = '<div class="alert alert-info"><i class="bi bi-info-circle"></i> No fields configured for this dataset.</div>';
        }
    });
}

// Load detailed data for a specific geometry point
function loadGeometryDetails(geometryId) {
    var url = window.location.origin + '/datasets/geometry/' + geometryId + '/details/';
    return fetch(url, {
        method: 'GET',
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.geometry) return data.geometry;
        throw new Error('Failed to load geometry details');
    });
}

// Add markers to the map
function addMarkersToMap(mapData) {
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
    if (!Array.isArray(mapData) || mapData.length === 0) return;

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
        marker.on('click', function() { selectPoint(point); });
        marker.addTo(map);
        markers.push(marker);
    });

    focusOnAllPoints();

    // Auto-select newly added marker if we have a cached location
    if (lastAddedLatLng && markers.length > 0) {
        var nearest = null;
        var bestDist = Infinity;
        markers.forEach(function(m) {
            var mp = m.pointData || m.geometryData;
            if (!mp) return;
            var dLat = (mp.lat - lastAddedLatLng.lat);
            var dLng = (mp.lng - lastAddedLatLng.lng);
            var dist = dLat * dLat + dLng * dLng;
            if (dist < bestDist) { bestDist = dist; nearest = m; }
        });
        if (nearest) selectPoint(nearest.pointData || nearest.geometryData);
        lastAddedLatLng = null;
    }
}

// Focus on all points on the map
function focusOnAllPoints() {
    if (!map || markers.length === 0) return;
    var group = new L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.1));
}

// Select a point and show its details
function selectPoint(point) {
    currentPoint = point;
    markers.forEach(marker => {
        var markerId = null;
        if (marker.pointData && marker.pointData.id) markerId = marker.pointData.id;
        else if (marker.geometryData && marker.geometryData.id) markerId = marker.geometryData.id;
        if (markerId === point.id) {
            marker.setStyle({ fillColor: '#FFB81C', color: '#FFB81C' });
        } else {
            marker.setStyle({ fillColor: '#0047BB', color: '#001A70' });
        }
    });

    loadGeometryDetails(point.id)
        .then(detailedPoint => { showGeometryDetails(detailedPoint); })
        .catch(() => { showGeometryDetails(point); });
}

// Show geometry details
function showGeometryDetails(point) {
    currentPoint = point;
    // Reset selected entry when switching to a new geometry
    selectedEntryId = null;

    if (!window.allFields || window.allFields.length === 0) {
        try {
            var allFieldsElement = document.getElementById('allFields');
            if (allFieldsElement && allFieldsElement.textContent) {
                window.allFields = JSON.parse(allFieldsElement.textContent);
                allFields = window.allFields;
            } else {
                window.allFields = [];
                allFields = [];
            }
        } catch (e) {
            window.allFields = [];
            allFields = [];
        }
    }

    if (!window.allFields || window.allFields.length === 0) {
        loadFieldsFromAPI();
        return;
    }

    var detailsDiv = document.getElementById('geometryDetails');
    detailsDiv.classList.add('active');
    generateEntriesTable(point);
    loadUploadedFiles();
    if (typeof adjustColumnLayout === 'function') adjustColumnLayout();
}

// Global variable to track selected entry
var selectedEntryId = null;

// Generate entries table
function generateEntriesTable(point) {
    var entriesList = document.getElementById('entriesList');
    if (!entriesList) return;

    var entriesHtml = '';
    console.log('generateEntriesTable called with point:', point);
    console.log('window.allFields:', window.allFields);
    
    // Sort entries by year (newest first)
    var sortedEntries = (point.entries || []).sort(function(a, b) {
        return (b.year || 0) - (a.year || 0);
    });
    
    // Entry Selection Dropdown - only show if multiple entries are allowed and there are entries
    if (window.allowMultipleEntries && sortedEntries.length > 0) {
        entriesHtml += '<div class="card mb-3">';
        entriesHtml += '<div class="card-header bg-light fw-semibold">';
        entriesHtml += '<i class="bi bi-list-ul me-2"></i>';
        entriesHtml += 'Select an entry to edit or create a new one. Total entries: ' + sortedEntries.length;
        entriesHtml += '</div>';
        entriesHtml += '<div class="card-body">';
        entriesHtml += '<div class="mb-3">';
        entriesHtml += '<select class="form-select" id="entrySelector" onchange="selectEntryFromDropdown(this.value)">';
        
        // Determine initial selection
        var hasInitialSelection = false;
        if (sortedEntries.length > 0 && selectedEntryId === null) {
            // Auto-select first entry if entries exist and nothing is selected
            selectedEntryId = sortedEntries[0].id;
            hasInitialSelection = true;
        }
        
        // Add option for creating new entry
        var isNewSelected = selectedEntryId === 'new';
        entriesHtml += '<option value="new"' + (isNewSelected ? ' selected' : '') + '>';
        entriesHtml += '➕ Create New Entry';
        entriesHtml += '</option>';
        
        // Add options for existing entries
        sortedEntries.forEach(function(entry, index) {
            var isSelected = false;
            if (selectedEntryId !== null && selectedEntryId !== 'new') {
                var entryIdNum = typeof selectedEntryId === 'string' ? parseInt(selectedEntryId) : selectedEntryId;
                isSelected = entry.id === entryIdNum || entry.id === selectedEntryId;
            } else if (index === 0 && hasInitialSelection) {
                isSelected = true;
            }
            
            var entryName = entry.name || 'Unnamed Entry';
            var entryYear = entry.year ? ' (' + entry.year + ')' : '';
            var entryUser = entry.user ? ' - ' + entry.user : '';
            
            entriesHtml += '<option value="' + entry.id + '"' + (isSelected ? ' selected' : '') + '>';
            entriesHtml += escapeHtml(entryName) + escapeHtml(entryYear) + escapeHtml(entryUser);
            entriesHtml += '</option>';
        });
        
        entriesHtml += '</select>';
        entriesHtml += '</div>';
        entriesHtml += '</div>';
        entriesHtml += '</div>';
    }
    
    // Entry Detail Form Section - Show selected entry or new entry form
    var selectedEntry = null;
    var selectedEntryIndex = -1;
    var showNewEntryForm = false;
    
    // If multiple entries are not allowed, automatically select the first (and only) entry if it exists
    if (!window.allowMultipleEntries && sortedEntries.length > 0) {
        selectedEntry = sortedEntries[0];
        selectedEntryIndex = 0;
        selectedEntryId = sortedEntries[0].id;
    }
    // Check if we should show new entry form
    // Show new entry form if "new" is selected, or if no entries exist
    else if (selectedEntryId === 'new' || (selectedEntryId === null && sortedEntries.length === 0)) {
        showNewEntryForm = true;
    } else {
        // Find the selected entry
        sortedEntries.forEach(function(entry, index) {
            var entryIdNum = typeof selectedEntryId === 'string' ? parseInt(selectedEntryId) : selectedEntryId;
            if (entry.id === entryIdNum || entry.id === selectedEntryId) {
                selectedEntry = entry;
                selectedEntryIndex = index;
            }
        });
    }
    
    // Show selected entry form
    if (selectedEntry) {
        var entry = selectedEntry;
        var entryIndex = selectedEntryIndex;
        
        entriesHtml += '<div class="card mb-3 border-info">';
        entriesHtml += '<div class="card-header bg-info bg-opacity-10 d-flex justify-content-between align-items-center">';
        entriesHtml += '<h6 class="mb-0 fw-semibold"><i class="bi bi-pencil-square me-2"></i>' + (entry.name || 'Unnamed Entry') + '</h6>';
        entriesHtml += '<small class="text-muted">Editing Entry</small>';
        entriesHtml += '</div>';
        entriesHtml += '<div class="card-body">';
        
        // Create form for this entry
        entriesHtml += '<form class="entry-form" data-entry-id="' + entry.id + '">';
        
        // Dynamic fields - render all configured fields from window.allFields or allFields
        var fieldsToUse = window.allFields || allFields || [];
        
        if (fieldsToUse && fieldsToUse.length > 0) {
            // Sort fields by order
            var sortedFields = fieldsToUse.sort(function(a, b) {
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
    
    // Show new entry form if selected
    if (showNewEntryForm) {
        entriesHtml += '<div class="card mb-3 new-entry-form border-success">';
        entriesHtml += '<div class="card-header bg-success bg-opacity-10 fw-semibold">';
        entriesHtml += '<i class="bi bi-plus-circle me-2"></i>' + (window.translations?.createEntry || 'Create New Entry');
        entriesHtml += '</div>';
        entriesHtml += '<div class="card-body">';
        
        // Entry name field
        entriesHtml += '<div class="mb-3">';
        entriesHtml += '<label for="new-entry-name" class="form-label">Entry Name <span class="text-danger">*</span></label>';
        entriesHtml += '<input type="text" class="form-control" id="new-entry-name" placeholder="Enter entry name" value="' + point.id_kurz + '">';
        entriesHtml += '</div>';
        
        // Dynamic fields for new entry
        var fieldsToUse = window.allFields || allFields || [];
        
        if (fieldsToUse && fieldsToUse.length > 0) {
            // Sort fields by order
            var sortedFields = fieldsToUse.sort(function(a, b) {
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
    entriesHtml += '<div class="mt-3 d-flex gap-2 flex-wrap">';
    if (showNewEntryForm) {
        entriesHtml += '<button type="button" class="btn btn-primary" onclick="createEntry()">';
        entriesHtml += '<i class="bi bi-plus-circle"></i> ' + (window.translations?.createEntry || 'Create Entry');
        entriesHtml += '</button>';
    }
    if (selectedEntry) {
        entriesHtml += '<button type="button" class="btn btn-success" onclick="saveEntries()">';
        entriesHtml += '<i class="bi bi-save"></i> ' + (window.translations?.saveEntries || 'Save Changes');
        entriesHtml += '</button>';
        if (window.allowMultipleEntries) {
            entriesHtml += '<button type="button" class="btn btn-outline-secondary" id="copyEntryBtn" onclick="copyToNewEntry(' + selectedEntry.id + ', ' + selectedEntryIndex + ', this)">';
            entriesHtml += '<i class="bi bi-files"></i> Copy to new Entry</button>';
        }
        entriesHtml += '<a href="/entries/' + selectedEntry.id + '/" class="btn btn-outline-info" target="_blank">';
        entriesHtml += '<i class="bi bi-eye"></i> View Details</a>';
    }
    entriesHtml += '</div>';
    
    entriesList.innerHTML = entriesHtml;
}

// Select an entry from the dropdown
function selectEntryFromDropdown(value) {
    if (value === 'new') {
        selectedEntryId = 'new'; // Use 'new' string to distinguish from null
    } else {
        selectedEntryId = value ? parseInt(value) : null;
    }
    // Regenerate the entries table to show the selected entry
    if (currentPoint) {
        generateEntriesTable(currentPoint);
    }
}

// Legacy function for backward compatibility (if needed)
function selectEntry(entryId, entryIndex) {
    selectedEntryId = entryId ? parseInt(entryId) : null;
    // Update the dropdown to reflect the selection
    var selector = document.getElementById('entrySelector');
    if (selector) {
        selector.value = entryId || 'new';
    }
    // Regenerate the entries table to show the selected entry
    if (currentPoint) {
        generateEntriesTable(currentPoint);
    }
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
            var options = normalizeFieldChoices(field);
            var fieldValueStr = fieldValue !== undefined && fieldValue !== null ? String(fieldValue) : '';
            inputHtml = '<select class="form-select" id="' + fieldId + '" name="' + fieldName + '"';
            if (field.required) inputHtml += ' required';
            inputHtml += '>';
            inputHtml += '<option value="">' + escapeHtml(field.placeholder || 'Select option') + '</option>';

            options.forEach(function(option) {
                var optionValue = option.value !== undefined ? option.value : '';
                var optionLabel = option.label !== undefined ? option.label : optionValue;
                var selected = fieldValueStr !== '' && fieldValueStr === String(optionValue) ? ' selected' : '';
                inputHtml += '<option value="' + escapeHtml(optionValue) + '"' + selected + '>' + escapeHtml(optionLabel) + '</option>';
            });

            inputHtml += '</select>';
            break;
            
        case 'date':
            // Only set value if it's a valid date format (YYYY-MM-DD)
            var dateValue = '';
            if (fieldValue && typeof fieldValue === 'string' && fieldValue.match(/^\d{4}-\d{2}-\d{2}$/)) {
                dateValue = fieldValue;
            } else if (fieldValue && typeof fieldValue === 'string' && fieldValue.length > 0) {
                // Try to parse date if it's in a different format
                try {
                    var date = new Date(fieldValue);
                    if (!isNaN(date.getTime())) {
                        dateValue = date.toISOString().split('T')[0];
                    }
                } catch (e) {
                    // Invalid date, leave empty
                    dateValue = '';
                }
            }
            inputHtml = '<input type="date" class="form-control" id="' + fieldId + '" name="' + fieldName + '" value="' + dateValue + '"';
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
            var customOptions = normalizeFieldChoices(field);
            if (customOptions.length > 0) {
                inputHtml = '<select class="form-select form-select-sm" id="' + fieldId + '" name="' + fieldName + '">';
                inputHtml += '<option value="">' + escapeHtml(window.translations?.selectOption || 'Select option') + '</option>';
                customOptions.forEach(function(option) {
                    var optionValue = option.value !== undefined ? option.value : '';
                    var optionLabel = option.label !== undefined ? option.label : optionValue;
                    inputHtml += '<option value="' + escapeHtml(optionValue) + '">' + escapeHtml(optionLabel) + '</option>';
                });
                inputHtml += '</select>';
            } else {
                inputHtml = '<input type="text" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label + '">';
            }
            break;
        case 'date':
            // Only set value if it's a valid date format (YYYY-MM-DD)
            var dateValue = '';
            if (fieldValue && typeof fieldValue === 'string' && fieldValue.match(/^\d{4}-\d{2}-\d{2}$/)) {
                dateValue = fieldValue;
            } else if (fieldValue && typeof fieldValue === 'string' && fieldValue.length > 0) {
                // Try to parse date if it's in a different format
                try {
                    var date = new Date(fieldValue);
                    if (!isNaN(date.getTime())) {
                        dateValue = date.toISOString().split('T')[0];
                    }
                } catch (e) {
                    // Invalid date, leave empty
                    dateValue = '';
                }
            }
            inputHtml = '<input type="date" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + dateValue + '">';
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
            var editableOptions = normalizeFieldChoices(field);
            var editableValue = fieldValue !== undefined && fieldValue !== null ? String(fieldValue) : '';
            if (editableOptions.length > 0) {
                inputHtml = '<select class="form-select form-select-sm" id="' + fieldId + '" name="' + fieldName + '">';
                inputHtml += '<option value="">' + escapeHtml(window.translations?.selectOption || 'Select option') + '</option>';
                editableOptions.forEach(function(option) {
                    var optionValue = option.value !== undefined ? option.value : '';
                    var optionLabel = option.label !== undefined ? option.label : optionValue;
                    var selected = editableValue !== '' && editableValue === String(optionValue) ? ' selected' : '';
                    inputHtml += '<option value="' + escapeHtml(optionValue) + '"' + selected + '>' + escapeHtml(optionLabel) + '</option>';
                });
                inputHtml += '</select>';
            } else {
                inputHtml = '<input type="text" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + fieldValue + '" placeholder="' + (window.translations?.enterField || 'Enter') + ' ' + field.label + '">';
            }
            break;
        case 'date':
            // Only set value if it's a valid date format (YYYY-MM-DD)
            var dateValue = '';
            if (fieldValue && typeof fieldValue === 'string' && fieldValue.match(/^\d{4}-\d{2}-\d{2}$/)) {
                dateValue = fieldValue;
            } else if (fieldValue && typeof fieldValue === 'string' && fieldValue.length > 0) {
                // Try to parse date if it's in a different format
                try {
                    var date = new Date(fieldValue);
                    if (!isNaN(date.getTime())) {
                        dateValue = date.toISOString().split('T')[0];
                    }
                } catch (e) {
                    // Invalid date, leave empty
                    dateValue = '';
                }
            }
            inputHtml = '<input type="date" class="form-control form-control-sm" id="' + fieldId + '" name="' + fieldName + '" value="' + dateValue + '">';
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
                    // Skip empty date fields to avoid browser validation errors
                    if (field.field_type === 'date' && !fieldElement.value) {
                        return; // Skip empty date fields
                    }
                    // Send field name directly (not wrapped in fields[])
                    formData.append(field.field_name, fieldElement.value);
                }
            }
        });
    }
    
    fetch(window.location.origin + '/geometries/' + currentPoint.id + '/entries/create/', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
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

// Copy entry to new entry
function copyToNewEntry(entryId, entryIndex, buttonElement) {
    if (!currentPoint) {
        alert('Please select a geometry point first.');
        return;
    }
    
    if (!window.allowMultipleEntries && currentPoint.entries && currentPoint.entries.length > 0) {
        alert('Multiple entries are not allowed for this dataset.');
        return;
    }
    
    // Get the entry name (use current entry name with "Copy" suffix)
    var currentEntryName = '';
    if (currentPoint.entries && currentPoint.entries[entryIndex]) {
        currentEntryName = currentPoint.entries[entryIndex].name || currentPoint.id_kurz || 'Entry';
    } else {
        currentEntryName = currentPoint.id_kurz || 'Entry';
    }
    var newEntryName = currentEntryName + ' (Copy)';
    
    var formData = new FormData();
    formData.append('name', newEntryName);
    formData.append('geometry_id', currentPoint.id);
    formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
    
    // Copy field values from the current entry's form (excluding images)
    if (window.allFields && window.allFields.length > 0) {
        window.allFields.forEach(function(field) {
            if (field.enabled) {
                // Get field value from the current entry's form
                var fieldElement = document.getElementById('field_' + field.field_name + '_' + entryIndex);
                if (fieldElement) {
                    var fieldValue = fieldElement.value;
                    // Skip empty date fields to avoid browser validation errors
                    if (field.field_type === 'date' && !fieldValue) {
                        return; // Skip empty date fields
                    }
                    // Send field name directly (not wrapped in fields[])
                    formData.append(field.field_name, fieldValue);
                }
            }
        });
    }
    
    // Show loading state
    var copyBtn = buttonElement || document.getElementById('copyEntryBtn');
    var originalText = copyBtn.innerHTML;
    copyBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Copying...';
    copyBtn.disabled = true;
    
    fetch(window.location.origin + '/geometries/' + currentPoint.id + '/entries/create/', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reload map data to show new entry
            loadMapData();
            
            // After reloading, select the new entry
            if (data.entry_id) {
                // Wait a bit for the data to load, then select the new entry
                setTimeout(function() {
                    selectedEntryId = data.entry_id;
                    // Reload geometry details to get the new entry
                    loadGeometryDetails(currentPoint.id)
                        .then(function(detailedPoint) {
                            showGeometryDetails(detailedPoint);
                            // Select the new entry in the dropdown
                            var selector = document.getElementById('entrySelector');
                            if (selector) {
                                selector.value = data.entry_id;
                            }
                        })
                        .catch(function() {
                            // Fallback: just reload the current point
                            if (currentPoint) {
                                generateEntriesTable(currentPoint);
                            }
                        });
                }, 500);
            }
        } else {
            alert('Error copying entry: ' + (data.error || 'Unknown error'));
            copyBtn.innerHTML = originalText;
            copyBtn.disabled = false;
        }
    })
    .catch(error => {
        console.error('Error copying entry:', error);
        alert('Error copying entry: ' + error.message);
        copyBtn.innerHTML = originalText;
        copyBtn.disabled = false;
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
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
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

    setTimeout(function() {
        var addPointBtn = document.getElementById('addPointBtn');
        if (addPointBtn) {
            addPointBtn.replaceWith(addPointBtn.cloneNode(true));
            addPointBtn = document.getElementById('addPointBtn');
            addPointBtn.addEventListener('click', function(e) {
                e.preventDefault();
                toggleAddPointMode();
            });
        }

        var focusAllBtn = document.getElementById('focusAllBtn');
        if (focusAllBtn) focusAllBtn.addEventListener('click', focusOnAllPoints);
        var myLocationBtn = document.getElementById('myLocationBtn');
        if (myLocationBtn) myLocationBtn.addEventListener('click', zoomToMyLocation);
        var zoomInBtn = document.getElementById('zoomInBtn');
        if (zoomInBtn) zoomInBtn.addEventListener('click', function() { map.zoomIn(); });
        var zoomOutBtn = document.getElementById('zoomOutBtn');
        if (zoomOutBtn) zoomOutBtn.addEventListener('click', function() { map.zoomOut(); });
    }, 100);
}

// Focus on all points
function focusOnAllPoints() {
    if (!map || markers.length === 0) return;
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
    if (detailsDiv) {
        detailsDiv.classList.remove('active');
    }
    
    // Reset all markers to default blue style
    markers.forEach(marker => {
        marker.setStyle({ fillColor: '#0047BB', color: '#001A70' });
    });
    
    // Clear geometry info (only if elements exist)
    var geometryId = document.getElementById('geometryId');
    if (geometryId) geometryId.textContent = '-';
    var geometryAddress = document.getElementById('geometryAddress');
    if (geometryAddress) geometryAddress.textContent = '-';
    var entriesCount = document.getElementById('entriesCount');
    if (entriesCount) entriesCount.textContent = '-';
    
    // Clear entries list
    var entriesList = document.getElementById('entriesList');
    if (entriesList) {
        entriesList.innerHTML = '';
    }
    
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
    // Keep map column full width; geometry details is an overlay on md+ and flows below on small screens
    if (mapColumn) {
        mapColumn.className = 'col-12';
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
        headers: { 'X-CSRFToken': csrfToken }
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
    
    fetch('/datasets/geometry/' + currentPoint.id + '/files/', {
        headers: { 'X-CSRFToken': csrfToken }
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
        const uploadDate = file.uploaded_at ? new Date(file.uploaded_at).toLocaleDateString() : 'Unknown';
        
        html += '<div class="list-group-item d-flex justify-content-between align-items-center">' +
            '<div>' +
                '<i class="' + fileIcon + ' me-2"></i>' +
                '<strong>' + (file.original_name || 'Unknown') + '</strong>' +
                '<small class="text-muted ms-2">(' + fileSize + ')</small>' +
                '<br><small class="text-muted">Uploaded: ' + uploadDate + '</small>' +
            '</div>' +
            '<div>' +
                '<a href="' + (file.download_url || '#') + '" class="btn btn-sm btn-outline-primary me-1" title="Download">' +
                    '<i class="bi bi-download"></i>' +
                '</a>' +
                '<button class="btn btn-sm btn-outline-danger" onclick="deleteFile(' + (file.id || 0) + ')" title="Delete">' +
                    '<i class="bi bi-trash"></i>' +
                '</button>' +
            '</div>' +
        '</div>';
    });
    html += '</div>';
    
    filesList.innerHTML = html;
}

function getFileIcon(fileType) {
    if (!fileType) return 'bi bi-file';
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
    if (!bytes || bytes === 0) return '0 Bytes';
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
    
    fetch('/datasets/files/' + fileId + '/delete/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' }
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

// Toggle add point mode
function toggleAddPointMode() {
    addPointMode = !addPointMode;
    var button = document.getElementById('addPointBtn');
    if (!button) return;

    if (addPointMode) {
        button.classList.remove('btn-primary');
        button.classList.add('btn-success');
        button.innerHTML = '<i class="bi bi-check-circle"></i> Click on Map';
        button.title = 'Click on the map to add a new point, or click this button to cancel';
        if (map && map.getContainer()) map.getContainer().style.cursor = 'crosshair';
    } else {
        button.classList.remove('btn-success');
        button.classList.add('btn-primary');
        button.innerHTML = '<i class="bi bi-plus-circle"></i> Add Point';
        button.title = 'Add New Point';
        if (map && map.getContainer()) map.getContainer().style.cursor = '';
        if (addPointMarker) { map.removeLayer(addPointMarker); addPointMarker = null; }
    }
}

// Add new point to the map
function addNewPoint(latlng) {
    if (addPointMarker) { map.removeLayer(addPointMarker); }
    addPointMarker = L.marker(latlng, {
        icon: L.divIcon({
            className: 'custom-marker add-point-marker',
            html: '<div style="background-color: #28a745; color: white; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold;">+</div>',
            iconSize: [20, 20], iconAnchor: [10, 10]
        })
    }).addTo(map);
    if (confirm('Add new point at this location?\n\nLatitude: ' + latlng.lat.toFixed(6) + '\nLongitude: ' + latlng.lng.toFixed(6))) {
        createNewGeometry(latlng);
    } else {
        map.removeLayer(addPointMarker); addPointMarker = null;
    }
}

// Create new geometry via AJAX
function createNewGeometry(latlng) {
    var datasetId = getDatasetId();
    var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    var newId = 'NEW_' + Date.now();
    var geometryData = { id_kurz: newId, address: 'New Point', geometry: { type: 'Point', coordinates: [latlng.lng, latlng.lat] } };
    
    fetch('/datasets/' + datasetId + '/geometries/create/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        body: JSON.stringify(geometryData)
    })
    .then(async (response) => {
        const contentType = response.headers ? (response.headers.get && response.headers.get('content-type')) || '' : '';
        if (!response.ok) {
            const text = await (response.text ? response.text() : Promise.resolve(''));
            throw new Error('HTTP ' + response.status + (text ? (' - ' + text.substring(0, 200)) : ''));
        }
        if (contentType && contentType.indexOf('application/json') !== -1) return response.json();
        return { success: true, fallback: true };
    })
    .then(data => {
        if (addPointMarker) { try { map.removeLayer(addPointMarker); } catch(e) {} addPointMarker = null; }

        if (data && data.success && !data.fallback) {
            var newMarker = L.circleMarker([latlng.lat, latlng.lng], {
                radius: 8, fillColor: '#0047BB', color: '#001A70', weight: 2, opacity: 1, fillOpacity: 0.8
            }).addTo(map);
            newMarker.geometryData = { id: data.geometry_id, id_kurz: data.id_kurz, address: data.address, lat: latlng.lat, lng: latlng.lng, entries: [] };
            markers.push(newMarker);
            newMarker.on('click', function() { selectPoint(newMarker.geometryData); });
            toggleAddPointMode();
            selectPoint(newMarker.geometryData);
        } else {
            lastAddedLatLng = { lat: latlng.lat, lng: latlng.lng };
            toggleAddPointMode();
            loadMapData();
        }
    })
    .catch(() => {
        lastAddedLatLng = { lat: latlng.lat, lng: latlng.lng };
        toggleAddPointMode();
        loadMapData();
    });
}
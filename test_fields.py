import json

# Sample field data from the response
fields_json = '''[{"id": 35, "name": "Anzahl Wohnungen", "label": "Anzahl Wohnungen", "field_type": "integer", "field_name": "Anzahl Wohnungen", "required": false, "enabled": true, "help_text": "", "choices": "", "order": 0, "typology_choices": []}, {"id": 36, "name": "Bauperiode", "label": "Bauperiode", "field_type": "text", "field_name": "BAUPERIODE", "required": false, "enabled": true, "help_text": "", "choices": "", "order": 1, "typology_choices": []}]'''

# Parse the JSON
fields_data = json.loads(fields_json)

print(f'Parsed {len(fields_data)} fields')
print('Field details:')
for field in fields_data:
    print(f'  - {field["field_name"]}: {field["label"]} (enabled: {field["enabled"]})')

# Test the JavaScript logic
print('\nTesting JavaScript logic:')
print(f'window.allFields exists: {fields_data is not None}')
print(f'window.allFields.length > 0: {len(fields_data) > 0}')

# Check if there are any enabled fields
has_enabled_fields = any(field['enabled'] for field in fields_data)
print(f'Has enabled fields: {has_enabled_fields}')

# Count enabled fields
enabled_count = sum(1 for field in fields_data if field['enabled'])
print(f'Enabled fields count: {enabled_count}')

#!/usr/bin/env python
"""Test the candidate Sankey API endpoint."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'polstats_project.settings')
django.setup()

from django.test import RequestFactory
from polstats_project.disclosures.views import api_candidate_sankey

# Create a mock request
factory = RequestFactory()
request = factory.get('/api/candidates/Herbert,%20Gary%20R./sankey/')

# Call the view
response = api_candidate_sankey(request, 'Herbert, Gary R.')

# Print the response
print("Status:", response.status_code)
print("\nContent:")
import json
data = json.loads(response.content)
print(json.dumps(data, indent=2))
print(f"\nTotal nodes: {len(data['nodes'])}")
print(f"Total links: {len(data['links'])}")

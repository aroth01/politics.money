from django.urls import path
from . import views

app_name = 'disclosures'

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('reports/', views.reports_list, name='reports_list'),
    path('reports/<str:report_id>/', views.report_detail, name='report_detail'),
    path('contributors/', views.contributors_list, name='contributors_list'),
    path('contributors/<path:contributor_name>/', views.contributor_detail, name='contributor_detail'),
    path('expenditures/', views.expenditures_list, name='expenditures_list'),
    path('pacs/', views.pacs_list, name='pacs_list'),
    path('pacs/<path:organization_name>/', views.pac_detail, name='pac_detail'),
    path('out-of-state/', views.out_of_state, name='out_of_state'),
    path('search/', views.global_search, name='search'),

    # API endpoints for charts
    path('api/reports/<str:report_id>/timeline/', views.api_report_timeline, name='api_report_timeline'),
    path('api/reports/<str:report_id>/top-contributors/', views.api_report_top_contributors, name='api_report_top_contributors'),
    path('api/reports/<str:report_id>/top-expenditures/', views.api_report_top_expenditures, name='api_report_top_expenditures'),
    path('api/global/timeline/', views.api_global_timeline, name='api_global_timeline'),
    path('api/contributors/<path:contributor_name>/timeline/', views.api_contributor_timeline, name='api_contributor_timeline'),
    path('api/pacs/<path:organization_name>/sankey/', views.api_pac_sankey, name='api_pac_sankey'),
    path('api/out-of-state/map/', views.api_out_of_state_map, name='api_out_of_state_map'),
]

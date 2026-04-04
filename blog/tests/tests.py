"""
Tests split into focused files per domain.
Django discovers them automatically via test*.py pattern.

- test_sprint_behavior.py          → SprintAssignmentTests
- test_project_membership_behavior.py → ProjectMembershipTests
- test_ticket_tag_behavior.py      → TicketTagTests
- test_ticket_creation_and_links_behavior.py → TicketCreationRulesTests, TicketLinkTests
- test_api_view_set_behavior.py    → API viewset tests
- test_demo_data_command_behavior.py → Management command tests
- test_model_validation_behavior.py → Model validation tests
- test_rich_text_behavior.py       → Rich text sanitization tests
- test_ticket_and_tag_http_behavior.py → HTTP endpoint tests
- test_ticket_view_configuration_behavior.py → View config tests
"""

{% if author_name %}Author Name: **{{ author_name }}** {% if author_github_username %}({{ author_github_username }}){% endif %}{% endif %}
{% if redmine_link %}Original Redmine Issue: [{{ redmine_issue_num }}]({{redmine_link}}){% endif %}
{% if affected_version %}Affected QGIS version: {{ affected_version }}{% endif %}
{% if category %}Redmine category:{{ category }}{% endif %}
{% if redmine_assignee %}Assignee: {{ redmine_assignee }}{% endif %}

---
{{ description }}

{% if attachments|length > 0 -%}
---
{% for attachment in attachments %}
- [{{ attachment.filename }}]({{ attachment.content_url }}) ({{ attachment.author.name }})
{%- endfor %}
{%- endif %}

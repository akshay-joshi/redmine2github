{% if author_name %}Author Name: **{{ author_name }}** {% if author_github_username %}({{ author_github_username }}){% endif %}{% endif %}

{% if description %}
---
{{ description }}
{%- endif %}

{% if details|length > 0 -%}
---
{% for detail in details %}
- {% if detail.name %} {{ detail.name }} {% if detail.action %} {{ detail.action }} {% if detail.old_value %} {{ detail.old_value }} {% endif %} {% if detail.new_value %} {{ detail.new_value }} {% endif %}{% endif %}{% endif %}
{%- endfor %}
{%- endif %}

{% if attachments|length > 0 -%}
---
{% for attachment in attachments %}
- [{{ attachment.filename }}]({{ attachment.content_url }}) ({{ attachment.author.name }}){% if attachment.description %} - {{ attachment.description }}{% endif %}
{%- endfor %}
{%- endif %}

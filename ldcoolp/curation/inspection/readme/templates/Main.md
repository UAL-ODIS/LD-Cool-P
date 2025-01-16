---------------------------------------------
# {{ figshare_dict.title }}

Preferred citation (DataCite format):

{% if qualtrics_dict.cite == 'nan' %}
{% for cite_text in figshare_dict.preferred_citation %}
  {{ cite_text }}
{% endfor %}
{% else %}
{% for cite_text in qualtrics_dict.cite %}
  {{ cite_text }}
{% endfor %}
{% endif %}


Corresponding Author:
  {{ qualtrics_dict.corr_author_fullname }}, {{ qualtrics_dict.corr_author_affil }}, {{ qualtrics_dict.corr_author_email }}


License:
  {{ figshare_dict.license }}


DOI:
  https://doi.org/{{ figshare_dict.doi }}



---------------------------------------------
## Summary

{{ figshare_dict.description }}
{% if qualtrics_dict.summary != 'nan' %}

{{ qualtrics_dict.summary }}
{% endif %}
{% if ( (qualtrics_dict.files != 'nan') or
        (qualtrics_dict.materials != 'nan') or
        (qualtrics_dict.contrib != 'nan') or
        (qualtrics_dict.notes != 'nan') or
        (figshare_dict.references != []) ) %}



{% endif %}
{% if figshare_dict.funders != [] %}
---------------------------------------------
## Funding Information

{% import 'funders_macro.jinja' as funds %}
{% for funder in figshare_dict.funders -%}
{% if funder.is_user_defined == 0 -%}
{{ funds.funders_(funder) }}
{% else %}
- {{ funder.title }}
{% endif %}
{%- endfor %}



{% endif %}
{% if qualtrics_dict.files != 'nan' %}
---------------------------------------------
## Files and Folders

{{ qualtrics_dict.files }}
{% if ( (qualtrics_dict.materials != 'nan') or
        (qualtrics_dict.contrib != 'nan') or
        (qualtrics_dict.notes != 'nan') or
        (figshare_dict.references != []) ) %}



{% endif %}
{% endif %}
{% if qualtrics_dict.materials != 'nan' %}
---------------------------------------------
## Materials and Methods

{{ qualtrics_dict.materials }}
{% if ( (qualtrics_dict.contrib != 'nan') or
        (qualtrics_dict.notes != 'nan') or
        (figshare_dict.references != []) ) %}



{% endif %}
{% endif %}
{% if qualtrics_dict.contrib != 'nan' %}
---------------------------------------------
## Contributor Roles

The roles are defined by the CRediT taxonomy http://credit.niso.org/

{% for contrib in qualtrics_dict.contrib %}
  - {{ contrib }}
{% endfor -%}
{% if ( (qualtrics_dict.notes != 'nan') or
        (figshare_dict.references != []) ) %}



{% endif %}
{% endif %}
{% if qualtrics_dict.notes != 'nan' or figshare_dict.related_materials != [] %}
---------------------------------------------
## Additional Notes

{% endif %}
{% if qualtrics_dict.notes != 'nan' %}
{{ qualtrics_dict.notes }}

{% endif %}
{% if figshare_dict.related_materials != [] %}
Related Materials:
{% for material in figshare_dict.related_materials %}
  - {{ material.relation }}: {{ material.title }} ({{ material.link }}) 
{% endfor -%}
{% endif %}

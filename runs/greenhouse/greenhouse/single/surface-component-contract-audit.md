# Surface Component Contract Audit

- Passed: **False**
- Sections parsed: 5 / 7
- Host surfaces: 16
- Child recipes: 83
- Nested child coverage: 0.86
- Explicit colors preserved: 10 / 12

## Validity Gates

- `parse_all_section_yaml`: False
- `raw_schema_uses_closed_kind_enum`: False
- `raw_schema_uses_kind_specific_role_fields`: False
- `raw_schema_omits_none_placeholders`: False
- `raw_schema_omits_default_visible`: False
- `raw_schema_uses_clean_implementation_values`: False
- `unknown_roles_explain_why`: True
- `extract_at_least_one_host_per_section`: True
- `extract_nested_children_for_90_percent`: False
- `extract_nonempty_child_recipes`: True

## Ambiguities

- parse_errors: block 2: while parsing a block collection
  in "<unicode string>", line 117, column 5:
        - logo_wordmark
        ^
expected <block end>, but found '?'
  in "<unicode string>", line 122, column 5:
        note: >
        ^
- parse_errors: block 3: while parsing a flow mapping
  in "<unicode string>", line 206, column 7:
        - { id: canvas_mint, role: section ... 
          ^
expected ',' or '}', but got '['
  in "<unicode string>", line 206, column 96:
     ... : "#CDEBDD", path: tree.children[1].style.background_color, conf ... 
                                         ^
- raw_kind_violations: section_01.tree.layers[0].kind=background_layer
- raw_kind_violations: section_01.tree.children[0].kind=text_block
- raw_kind_violations: section_01.tree.children[0].children[0].kind=link
- raw_kind_violations: section_01.tree.children[1].kind=icon_button
- raw_kind_violations: section_04.tree.children[0].kind=image_fragment
- raw_kind_violations: section_04.tree.children[1].kind=image_fragment
- raw_kind_violations: section_04.tree.children[2].kind=spacer
- raw_kind_violations: section_05.tree.children[0].kind=group
- raw_kind_violations: section_05.tree.children[0].children[0].kind=panel
- raw_kind_violations: section_05.tree.children[0].children[0].children[2].kind=button
- raw_kind_violations: section_05.tree.children[0].children[0].children[3].kind=link
- raw_kind_violations: section_05.tree.children[0].children[0].children[4].kind=badge
- raw_kind_violations: section_05.tree.children[0].children[0].children[5].kind=badge
- raw_kind_violations: section_05.tree.children[0].children[0].children[6].kind=card
- raw_kind_violations: section_05.tree.children[0].children[0].children[7].kind=card
- raw_kind_violations: section_05.tree.children[0].children[0].children[8].kind=image
- raw_kind_violations: section_05.tree.children[0].children[0].children[9].kind=image
- raw_kind_violations: section_05.tree.children[0].children[1].kind=panel
- raw_kind_violations: section_05.tree.children[0].children[1].children[1].kind=link
- raw_kind_violations: section_05.tree.children[1].kind=group
- missing_role_field: section_01.tree.section_role
- missing_role_field: section_04.tree.section_role
- missing_role_field: section_05.tree.section_role
- missing_role_field: section_05.tree.children[0].children[0].children[0].text_role
- missing_role_field: section_05.tree.children[0].children[0].children[0].text_scale
- missing_role_field: section_05.tree.children[0].children[0].children[1].text_role
- missing_role_field: section_05.tree.children[0].children[0].children[1].text_scale
- missing_role_field: section_05.tree.children[0].children[1].children[0].text_role
- missing_role_field: section_05.tree.children[0].children[1].children[0].text_scale
- missing_role_field: section_05.tree.children[1].items[0].children[1].text_role
- missing_role_field: section_05.tree.children[1].items[0].children[1].text_scale
- missing_role_field: section_05.tree.children[1].items[0].children[2].text_role
- missing_role_field: section_05.tree.children[1].items[0].children[2].text_scale
- missing_role_field: section_06.tree.section_role
- missing_role_field: section_06.tree.children[0].children[0].text_role
- missing_role_field: section_06.tree.children[0].children[0].text_scale
- missing_role_field: section_07.tree.section_role
- missing_role_field: section_07.tree.children[1].children[0].children[1].text_role
- missing_role_field: section_07.tree.children[1].children[0].children[1].text_scale
- missing_role_field: section_07.tree.children[1].children[0].children[2].text_role
- none_placeholder_paths: section_05.tree.children[1].items[0].style.border
- none_placeholder_paths: section_05.tree.children[1].items[0].style.shadow
- none_placeholder_paths: section_07.tree.children[1].children[0].style.border
- none_placeholder_paths: section_07.tree.children[1].children[0].style.shadow
- none_placeholder_paths: section_08.tree.children[0].children[0].style.transform
- none_placeholder_paths: section_08.tree.children[0].children[1].style.border
- none_placeholder_paths: section_08.tree.children[0].children[1].style.shadow
- none_placeholder_paths: section_09.tree.children[0].children[0].children[0].style.case
- none_placeholder_paths: section_09.tree.children[0].children[0].children[1].items.representative_child.style.underline
- none_placeholder_paths: section_09.tree.children[1].children[2].children[1].style.shadow
- default_visibility_paths: section_01.tree.visibility
- default_visibility_paths: section_01.tree.children[0].visibility
- default_visibility_paths: section_01.tree.children[0].children[0].visibility
- default_visibility_paths: section_04.tree.visibility
- default_visibility_paths: section_04.tree.children[0].visibility
- default_visibility_paths: section_04.tree.children[1].visibility
- default_visibility_paths: section_04.tree.children[2].visibility
- default_visibility_paths: section_05.tree.visibility
- default_visibility_paths: section_05.tree.children[0].visibility
- default_visibility_paths: section_05.tree.children[1].visibility
- default_visibility_paths: section_06.tree.visibility
- default_visibility_paths: section_07.tree.visibility
- default_visibility_paths: section_07.tree.children[0].visibility
- default_visibility_paths: section_07.tree.children[1].visibility
- default_visibility_paths: section_07.tree.children[1].children[0].visibility
- default_visibility_paths: section_07.tree.children[1].children[0].children[0].visibility
- default_visibility_paths: section_08.tree.visibility
- default_visibility_paths: section_09.tree.visibility
- uncertain_implementation_values: section_01.tree.position.sticky
- uncertain_implementation_values: section_04.tree.size.note
- uncertain_implementation_values: section_05.tree.children[0].note
- uncertain_implementation_values: section_08.tree.size.note

"""
Exports the Excel taxonomy into modules/detection/taxonomy_data.py
"""
import json
import os
import openpyxl

excel_path = "PII_PHI_Entity_Policy_Taxonomy_Corrected.xlsx"
out_path = os.path.join("modules", "detection", "taxonomy_data.py")

wb = openpyxl.load_workbook(excel_path)

# 1. Entity Canonicalization
c_ws = wb["Entity_Canonicalization"]
canonical_map = {}
for r in list(c_ws.iter_rows(values_only=True))[1:]:
    raw, canonical, category, aliases = r[0], r[1], r[2], r[3]
    if raw and canonical:
        canonical_map[raw.strip().upper()] = canonical.strip().upper()
    if canonical:
        canonical_map[canonical.strip().upper()] = canonical.strip().upper()
    if aliases and canonical:
        for alias in str(aliases).split(";"):
            alias = alias.strip()
            if alias:
                canonical_map[alias.upper()] = canonical.strip().upper()

# 2. Master Entity Policy
m_ws = wb["Master_Entity_Policy"]
doc_policies = {}
global_policy = {}
drop_entities = set()

for r in list(m_ws.iter_rows(values_only=True))[1:]:
    doc_type = r[0].strip() if r[0] else "General"
    entity = r[2].strip() if r[2] else ""
    canonical = r[3].strip().upper() if r[3] else entity.upper()
    category = r[4].strip() if r[4] else ""
    data_type = r[5].strip() if r[5] else ""
    priority = r[6].strip() if r[6] else "NICE_TO_HAVE"
    risk = r[7].strip() if r[7] else "MEDIUM"
    threat = r[8].strip() if r[8] else ""
    regulation = r[9].strip() if r[9] else ""

    if not canonical:
        continue

    if doc_type not in doc_policies:
        doc_policies[doc_type] = {}

    doc_policies[doc_type][canonical] = {
        "priority": priority,
        "risk_level": risk,
        "category": category,
        "data_type": data_type,
        "threat": threat,
        "regulation": regulation,
    }

    if priority == "DROP":
        drop_entities.add(canonical)

    if canonical not in global_policy or priority == "MUST_HAVE":
        global_policy[canonical] = {
            "priority": priority,
            "risk_level": risk,
            "category": category,
            "data_type": data_type,
        }

# 3. Drop_Entities sheet
d_ws = wb["Drop_Entities"]
for r in list(d_ws.iter_rows(values_only=True))[1:]:
    canonical = r[2].strip().upper() if r[2] else (r[1].strip().upper() if r[1] else "")
    if canonical:
        drop_entities.add(canonical)

code = f'''"""
Auto-generated from PII_PHI_Entity_Policy_Taxonomy_Corrected.xlsx
Defines document-type specific entity policies (MUST_HAVE, NICE_TO_HAVE, DROP),
canonical entity mapping, risk levels, and drop rules.
"""

CANONICAL_ENTITY_MAPPING = {repr(canonical_map)}

DOCUMENT_POLICIES = {repr(doc_policies)}

GLOBAL_POLICY = {repr(global_policy)}

DROP_ENTITIES = {repr(sorted(list(drop_entities)))}
'''

with open(out_path, "w", encoding="utf-8") as f:
    f.write(code)

print(f"Exported taxonomy data successfully to {out_path}")

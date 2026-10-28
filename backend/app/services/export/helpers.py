"""
Shared helpers for export services
"""
from typing import Dict, Any, Optional


def resolve_question_display_name(
    question_data: Dict[str, Any],
    index: int,
    used_names: Dict[str, int]
) -> str:
    """
    Determine a unique display_name for a question block in OpenEdX / Library OLX.

    Rules:
    1. If `name` (or `display_name`) is provided in `question_data` and is non-empty after trimming,
       use it as the base name.
    2. Otherwise, fall back to "Cau-NN" where NN is the 2-digit 1-based index (e.g. Cau-01, Cau-02, ...).
    3. If the base name has already been used within this export batch (`used_names`), append
       a suffix `_{count}` (e.g. `Cau-01_1`, `Cau-01_2`) without raising errors.
    4. The name is never extracted from choices or answer contents.
    
    Args:
        question_data: Dictionary containing question fields.
        index: 0-based question sequence index in the export batch.
        used_names: Mutable dictionary tracking occurrence counts of each base name.

    Returns:
        The final resolved display_name string.
    """
    raw_name = question_data.get("name")
    if raw_name is None:
        raw_name = question_data.get("display_name")

    if isinstance(raw_name, str) and raw_name.strip():
        base_name = raw_name.strip()
    else:
        base_name = f"Cau-{index + 1:02d}"

    # Handle duplicates in the same export batch
    if base_name not in used_names:
        used_names[base_name] = 1
        return base_name

    # Name is duplicate: generate suffix _1, _2, etc.
    count = used_names[base_name]
    used_names[base_name] = count + 1
    suffixed_name = f"{base_name}_{count}"
    
    # In the unlikely event suffixed_name was already claimed by an explicit name
    while suffixed_name in used_names:
        count += 1
        used_names[base_name] = count + 1
        suffixed_name = f"{base_name}_{count}"

    used_names[suffixed_name] = 1
    return suffixed_name

import re
from typing import List, Dict, Any, Tuple


def get_token_lexical_tags(text: str) -> List[str]:
    """Extracts boolean linguistic and structural tags for a token."""
    tags = []
    if text.isupper() and len(text) > 1:
        tags.append("IS_UPPER")
    elif text.istitle():
        tags.append("IS_TITLE")

    if text.isdigit():
        tags.append("IS_DIGIT")
    elif any(c.isdigit() for c in text):
        tags.append("HAS_DIGIT")

    if "-" in text or "/" in text:
        tags.append("HAS_SEPARATOR")

    if re.match(r"^\d{1,3}(,\d{3})*(\.\d{2})?$", text) or re.match(r"^\d+\.\d{2}$", text):
        tags.append("IS_CURRENCY_AMOUNT")

    # Character length categorization
    length = len(text)
    if length <= 2:
        tags.append("LEN_SHORT")
    elif length <= 6:
        tags.append("LEN_MED")
    elif length <= 15:
        tags.append("LEN_LONG")
    else:
        tags.append("LEN_XLONG")

    return tags


def get_spatial_bins(bbox: Dict[str, float]) -> List[str]:
    """Quantizes normalized bounding box coordinates [0, 1] into discrete spatial bins."""
    x1 = bbox.get("x1", 0.0)
    y1 = bbox.get("y1", 0.0)

    # 10 vertical bands (y_0 = top header, y_9 = bottom footer)
    y_band = min(9, max(0, int(y1 * 10)))
    # 5 horizontal columns (x_0 = left, x_4 = right)
    x_col = min(4, max(0, int(x1 * 5)))

    return [f"Y_BAND_{y_band}", f"X_COL_{x_col}"]


def extract_token_features(tokens: List[Dict[str, Any]]) -> List[str]:
    """
    Transforms a sequence of document tokens into enriched textual feature strings
    incorporating lexical properties, spatial positioning, and neighborhood context.
    """
    n = len(tokens)
    enriched_strings: List[str] = []

    for i, token in enumerate(tokens):
        raw_text = token.get("text", "")
        clean_text = raw_text.strip().lower()
        bbox = token.get("bbox", {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 0.0})

        # Neighbors
        prev_w = tokens[i - 1].get("text", "").lower() if i > 0 else "START"
        next_w = tokens[i + 1].get("text", "").lower() if i < n - 1 else "END"

        lex_tags = get_token_lexical_tags(raw_text)
        spatial_tags = get_spatial_bins(bbox)

        # Assemble composite token representation
        parts = [clean_text]
        parts.extend(lex_tags)
        parts.extend(spatial_tags)
        parts.append(f"PREV_{prev_w}")
        parts.append(f"NEXT_{next_w}")

        enriched_strings.append(" ".join(parts))

    return enriched_strings


def prepare_dataset_for_training(documents: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """
    Flattens a list of documents into parallel lists of (feature_string, label).
    """
    X_features = []
    y_labels = []

    for doc in documents:
        tokens = doc.get("tokens", [])
        if not tokens:
            continue
        feat_strings = extract_token_features(tokens)
        for i, token in enumerate(tokens):
            X_features.append(feat_strings[i])
            y_labels.append(token.get("label", "O"))

    return X_features, y_labels

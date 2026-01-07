def _calculate_exact_match_score(query_length):
    return query_length * 10


def _calculate_substring_match_score(query_lower, text_lower, query_length, occurrence_count):
    if text_lower.startswith(query_lower):
        base_score = query_length * 8
    elif text_lower.endswith(query_lower):
        base_score = query_length * 7
    else:
        base_score = query_length * 6

    occurrence_bonus = (occurrence_count - 1) * query_length * 0.5
    length_ratio = query_length / len(text_lower)
    length_penalty = (1 - length_ratio) ** 2 * query_length * 0.2

    return base_score + occurrence_bonus - length_penalty


def _find_partial_matches(query_lower, text_lower):
    match_count = 0
    text_index = 0
    positions = []

    for char in query_lower:
        found_index = text_lower.find(char, text_index)
        if found_index != -1:
            match_count += 1
            positions.append(found_index)
            text_index = found_index + 1

    return match_count, positions


def _calculate_partial_match_score(match_count, positions, query_length):
    if match_count == 0:
        return 0

    if len(positions) > 1:
        span = positions[-1] - positions[0] + 1
        compactness = query_length / span if span > 0 else 0
        position_bonus = compactness * 2
    else:
        position_bonus = 1

    return match_count + position_bonus


def calculate_text_similarity_score(query, text):
    if not query or not text:
        return 0

    query_lower = query.lower()
    text_lower = text.lower()

    if query_lower == text_lower:
        return _calculate_exact_match_score(len(query))

    occurrence_count = text_lower.count(query_lower)
    if occurrence_count > 0:
        return _calculate_substring_match_score(query_lower, text_lower, len(query), occurrence_count)

    match_count, positions = _find_partial_matches(query_lower, text_lower)
    return _calculate_partial_match_score(match_count, positions, len(query))


def calculate_search_score(query, title, description):
    if not query:
        return 0.0

    query_length = len(query)

    title_matches = calculate_text_similarity_score(query, title)
    title_score = (title_matches / query_length) * 100 * 2

    desc_matches = calculate_text_similarity_score(query, description)
    desc_score = (desc_matches / query_length) * 100

    total_score = title_score + desc_score

    return round(total_score, 2)

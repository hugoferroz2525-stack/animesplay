def metadata_numbers(rows, episodes, offset, edition=None):
    """Return the metadata number for each source row, preserving the display number."""
    raw = [int(entry['num']) if entry['num'].isdigit() else None for entry,_ in rows]
    local = [number for _,number in rows]
    if edition is not None:
        return [edition[n-1] if n and 0<n<=len(edition) else None for n in local]
    if not episodes:
        return local
    first = min(episodes)
    numbers = [n for n in raw if n is not None]
    if first > 1:
        if numbers and min(numbers) < first:
            return [first+n-1 if n else None for n in local]
        return raw
    if (offset and numbers and min(numbers)>offset and max(numbers)>max(episodes)
            and all(n-offset in episodes for n in numbers)):
        return [n-offset if n else None for n in raw]
    return local


def flat_season_ranges(seasons, numbers, *, allow_gaps=False):
    """Map a flat, unambiguous sequence to contiguous TMDB seasons."""
    whole = [number for number in numbers
             if number is not None and number == int(number) and number > 0]
    if not whole or min(whole) != 1 or len(set(whole)) != len(whole) or (not allow_gaps and len(whole) != max(whole)):
        return []
    ordered = sorted((season for season in seasons if season.get('season_number', 0) > 0),
                     key=lambda season: season['season_number'])
    ranges, end = [], 0
    for expected, season in enumerate(ordered, 1):
        count = season.get('episode_count')
        if season['season_number'] != expected or type(count) is not int or count <= 0:
            break
        ranges.append((end, end + count, expected))
        end += count
    if len(ranges) > 1 and max(whole) > ranges[0][1]:
        return ranges
    return []


def flat_season_position(ranges, number):
    if number is not None:
        for start, end, season in ranges:
            if start < number <= end:
                return season, number - start
    return -1, number

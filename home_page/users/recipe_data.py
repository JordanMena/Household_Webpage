"""Recipe import contract and plain-text editor conversions."""
import json
import re
from urllib.parse import urlsplit, urlunsplit


EXAMPLE = {
    'schema_version': 1,
    'name': 'Lemon pasta',
    'description': '',
    'servings': '4',
    'prep_time_minutes': 10,
    'cook_time_minutes': 15,
    'ingredient_groups': [
        {'name': 'Pasta', 'ingredients': ['400 g spaghetti', 'Salt, to taste']},
        {'name': 'Sauce', 'ingredients': ['1 lemon', '2 tbsp olive oil']},
    ],
    'directions': ['Cook the pasta in salted water.', 'Toss with the sauce.'],
    'notes': '',
    'source': '',
    'url': '',
    'tags': ['pasta'],
}

IMPORT_PROMPT = '''Extract ONE recipe from the website URL or recipe text I provide below.
Return only a JSON object matching this example (schema_version must be 1):
%s
Use the actual recipe, not the example content. Preserve all ingredient quantities,
units, preparation details, ingredient groups, and ordered cooking steps. Do not
invent missing details or convert units. Use an empty string for missing optional
text, null for missing times, and [] for missing tags. Times are whole minutes
between 0 and 10080. Servings is text (e.g. "4–6" or "12 muffins", max 80 characters).
Use one unnamed ingredient group when the recipe has no groups. Group names are
max 120 characters. Ingredient strings must be single lines and must not start
with ##. Each directions entry is one step (no numbering or blank lines within it).
Name is required (max 160 characters); source is optional (max 160 characters).
Tags are short names (max 20 characters each); do not include | in tag names.
Preserve the original source name and HTTP(S) recipe URL when available.
Mention ambiguities or missing information in notes. If you cannot access the
website, ask me to paste the recipe text instead of guessing. Do not include photos.

Recipe URL or text:
''' % json.dumps(EXAMPLE, indent=2)


def parse_ingredients(value):
    groups = []
    current = {'name': '', 'ingredients': []}
    for line in value.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == '##' or line.startswith('## '):
            if current['name'] or current['ingredients']:
                groups.append(current)
            current = {'name': line[3:].strip(), 'ingredients': []}
        else:
            current['ingredients'].append(line)
    if current['name'] or current['ingredients']:
        groups.append(current)
    if not groups or any(not group['ingredients'] for group in groups):
        raise ValueError('Add at least one ingredient to each group.')
    if any(len(group['name']) > 120 for group in groups):
        raise ValueError('Ingredient group names must be 120 characters or fewer.')
    return groups


def ingredients_text(groups):
    return '\n\n'.join('\n'.join(
        (['## ' + group['name']] if group['name'] or index else []) + group['ingredients']
    ) for index, group in enumerate(groups))


def parse_steps(value):
    return [step.strip() for step in re.split(r'\n\s*\n', value.strip()) if step.strip()]


def normalized_url(value):
    try:
        parts = urlsplit((value or '').strip())
    except ValueError:
        return (value or '').strip()
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/'), parts.query, ''))


def decode_import(raw):
    """Validate structure before putting values through the shared recipe form."""
    if len(raw) > 100000:
        raise ValueError('Recipe JSON must be under 100,000 characters.')
    raw = raw.strip()
    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*\n', '', raw, count=1, flags=re.I)
        raw = re.sub(r'\n?```\s*$', '', raw, count=1)
    try:
        data = json.loads(raw)
    except (ValueError, RecursionError) as error:
        raise ValueError('Invalid JSON. Check quotes, commas, and brackets, then try again.') from error
    if not isinstance(data, dict):
        raise ValueError('Paste one recipe JSON object, not a list of recipes.')
    if type(data.get('schema_version')) is not int or data['schema_version'] != 1:
        raise ValueError('schema_version must be 1. Use Copy LLM instructions for the format.')
    unknown = set(data) - set(EXAMPLE) - {'ingredients'}
    if unknown:
        raise ValueError('Unrecognized fields: ' + ', '.join(sorted(unknown)))
    result = {}
    for key in ('name', 'description', 'servings', 'notes', 'source', 'url'):
        value = data.get(key, '')
        if not isinstance(value, str):
            raise ValueError(f'{key} must be text.')
        result[key] = value.strip()
    for key in ('prep_time_minutes', 'cook_time_minutes'):
        value = data.get(key)
        if value is not None and type(value) is not int:
            raise ValueError(f'{key} must be whole minutes or null.')
        result[key] = '' if value is None else str(value)
    groups = data.get('ingredient_groups')
    if 'ingredients' in data:
        if groups is not None:
            raise ValueError('Use ingredient_groups or ingredients, not both.')
        groups = [{'name': '', 'ingredients': data['ingredients']}]
    if not isinstance(groups, list) or not groups:
        raise ValueError('ingredient_groups must be a nonempty list of groups.')
    for group in groups:
        if not isinstance(group, dict) or set(group) != {'name', 'ingredients'}:
            raise ValueError('Each ingredient group needs name and ingredients fields.')
        if not isinstance(group['name'], str) or '\n' in group['name'] or '\r' in group['name']:
            raise ValueError('Ingredient group names must be single-line text.')
        items = group['ingredients']
        if not isinstance(items, list) or not items or any(
            not isinstance(item, str) or not item.strip() or '\n' in item or '\r' in item
            or item.strip().startswith('##') for item in items
        ):
            raise ValueError('Each group needs nonempty, single-line ingredient strings (without ## prefixes).')
    result['ingredients'] = ingredients_text(groups)
    steps = data.get('directions')
    if not isinstance(steps, list) or not steps or any(
        not isinstance(step, str) or not step.strip() or len(parse_steps(step)) != 1 for step in steps
    ):
        raise ValueError('directions must be a nonempty list of steps, without blank lines within a step.')
    result['directions'] = '\n\n'.join(step.strip() for step in steps)
    tags = data.get('tags', [])
    if not isinstance(tags, list) or any(not isinstance(tag, str) or '|' in tag or not tag.strip() for tag in tags):
        raise ValueError('tags must be a list of nonempty names without | characters.')
    result['tags'] = '|'.join(tags)
    return result

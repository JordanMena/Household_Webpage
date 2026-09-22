# Adding and importing recipes

Open **Recipes → New Recipe** (or `/recipes/new`). Enter a recipe manually, or
choose **Paste recipe JSON** and copy the LLM instructions. Give those instructions
and a recipe URL or the recipe text to your LLM. Paste its response, choose
**Load into form**, review the result, and **Save recipe**. Importing alone does
not write recipes or tags to the database. No LLM API key is needed by the app.

- Ingredients: one ingredient per line. Use `## Sauce` on its own line to start
  a group. A bare `##` starts an unnamed group after a named group.
- Directions: separate steps with a blank line. The preview and saved recipe
  number steps automatically.
- Name and source: up to 160 characters; source is optional.
- Servings/yield: optional text, up to 80 characters (e.g. `4–6` or `12 muffins`).
- Prep and cook times: optional whole minutes, from 0 through 10080 (one week).
- Tags: use the existing panels or **Create a tag**. Imports can create tags too.
  New tags have a 20-character limit; existing longer tags remain usable.
- Photos: optional JPG/PNG upload. Leave empty when editing to keep the photo.
- Duplicate source URLs produce a warning; you can explicitly save anyway.

The versioned JSON example and extraction instructions live in
`home_page/users/recipe_data.py` and are shown in the import panel. The importer
accepts one object, optionally enclosed in Markdown JSON fences. It accepts a
simple `ingredients` string array as an alternative to `ingredient_groups`.
Unknown fields and malformed values are reported rather than silently discarded.
Missing optional text defaults to empty, missing times to null, and tags to `[]`.

## Database upgrade

Back up the configured database before upgrading. Run `python update_db.py`
using the application's Python environment and database configuration, then
restart the app. The migration is repeatable and adds nullable servings, time,
ingredient-group, and direction-step columns. SQLite accepts the increased name
and source lengths without rebuilding the table.

Existing recipes retain their original text and display. Editing converts old
pipe-separated ingredients to lines; existing group headings can be marked with
`##` explicitly. Saving fills structured groups/steps and retains compatibility
text in the old ingredients/directions columns. This avoids guessing whether a
legacy line is an ingredient or a heading.

Run checks with `python -m unittest discover -s test`.

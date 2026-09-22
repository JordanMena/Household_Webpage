import copy
import json
from unittest import TestCase

from sqlalchemy import text
from home_page import create_app, db
from home_page.models import Recipe, Tag
from home_page.users.recipe_data import EXAMPLE, ingredients_text, parse_ingredients
from test.test_freezer import TestConfig
from update_db import update_db


class TestRecipes(TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def import_recipe(self, data, fenced=False):
        raw = json.dumps(data)
        if fenced:
            raw = '```json\n' + raw + '\n```'
        return self.client.post('/recipes/import', data={'recipe_json': raw})

    def test_import_review_save_and_edit_round_trip(self):
        data = copy.deepcopy(EXAMPLE)
        data.update(name='A longer recipe name that previously could not be saved',
                    source='A source name longer than twenty characters',
                    url='https://example.com/pasta', tags=['Pasta', 'pasta', 'weeknight'],
                    prep_time_minutes=0, servings='4–6')
        response = self.import_recipe(data, fenced=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Recipe.query.count(), 0)
        self.assertEqual(Tag.query.count(), 0)
        values = response.get_json()['values']
        self.assertEqual(values['tags'], ['pasta', 'weeknight'])
        values['tags'] = '|'.join(values['tags'])
        response = self.client.post('/recipes/new', data=values)
        recipe = Recipe.query.one()
        self.assertTrue(response.location.endswith(f'/recipe/{recipe.id}'))
        self.assertEqual(recipe.ingredient_groups, data['ingredient_groups'])
        self.assertEqual(recipe.direction_steps, data['directions'])
        self.assertEqual(recipe.prep_time_minutes, 0)
        self.assertEqual(Tag.query.count(), 2)
        detail = self.client.get(response.location)
        self.assertIn(b'<h5>Sauce</h5>', detail.data)
        self.assertIn(b'Prep: 0 min', detail.data)
        edit = self.client.get(f'/recipe/{recipe.id}/update')
        self.assertEqual(edit.status_code, 200)
        self.assertIn(b'value="https://example.com/pasta"', edit.data)
        self.assertIn(b'## Sauce', edit.data)
        response = self.client.post(f'/recipe/{recipe.id}/update', data=values)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(recipe.url, data['url'])

    def test_invalid_import_preserves_database(self):
        cases = [
            {'schema_version': 2}, {'directions': 'not a list'},
            {'ingredient_groups': [{'name': 'Sauce', 'ingredients': []}]},
            {'prep_time_minutes': -1}, {'cook_time_minutes': 1.5},
            {'prep_time_minutes': True}, {'url': 'javascript:alert(1)'},
            {'name': 'x' * 161}, {'source': 'x' * 161},
            {'tags': ['x' * 21]}, {'unexpected': 'value'},
            {'ingredient_groups': [{'name': 'Sauce', 'ingredients': ['## Lost ingredient']}]},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                data = copy.deepcopy(EXAMPLE)
                data.update(changes)
                response = self.import_recipe(data)
                self.assertEqual(response.status_code, 400)
                self.assertTrue(response.get_json()['errors'])
        for raw in ('{bad json', '[]', '{' * 100001):
            self.assertEqual(self.client.post('/recipes/import', data={'recipe_json': raw}).status_code, 400)
        self.assertEqual(Recipe.query.count(), 0)
        self.assertEqual(Tag.query.count(), 0)

    def test_manual_validation_and_new_tags_survive_errors(self):
        values = dict(name='Dinner', ingredients='## Sauce\nTomatoes\n\n## Pasta\nSpaghetti',
                      directions='Boil water.\n\nCook pasta.', source='', url='bad URL',
                      tags='new tag|', prep_time_minutes='-1', recipe_json='{"name": "Original pasted text"}')
        response = self.client.post('/recipes/new', data=values)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'complete http:// or https:// URL', response.data)
        self.assertIn(b'data-tag-name="new tag"', response.data)
        self.assertIn(b'Original pasted text', response.data)
        self.assertEqual(Recipe.query.count(), 0)
        values.update(url='', prep_time_minutes='')
        self.assertEqual(self.client.post('/recipes/new', data=values).status_code, 302)
        self.assertEqual([tag.name for tag in Recipe.query.one().tags], ['new tag'])
        self.assertEqual(Tag.query.count(), 1)

    def test_existing_long_tag_and_photo_survive_edit(self):
        tag = Tag('a legacy tag with a long name')
        recipe = Recipe(name='Existing', ingredients='Food', directions='Cook', image_file='existing.jpg')
        db.session.add_all([tag, recipe])
        db.session.commit()
        response = self.client.post(f'/recipe/{recipe.id}/update', data={
            'name': recipe.name, 'ingredients': 'Food', 'directions': 'Cook', 'tags': tag.name,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(recipe.image_file, 'existing.jpg')
        self.assertEqual([item.name for item in recipe.tags], [tag.name])

    def test_import_reuses_existing_tags_case_insensitively(self):
        db.session.add(Tag('Pasta'))
        db.session.commit()
        values = self.import_recipe(EXAMPLE).get_json()['values']
        values['tags'] = '|'.join(values['tags'])
        self.client.post('/recipes/new', data=values)
        self.assertEqual(Tag.query.count(), 1)
        self.assertEqual(Recipe.query.one().tags[0].name, 'Pasta')

    def test_duplicate_url_warning_and_explicit_save(self):
        db.session.add(Recipe(name='Existing', ingredients='a|b', directions='Mix', url='https://example.com/pasta/'))
        db.session.commit()
        data = copy.deepcopy(EXAMPLE)
        data['url'] = 'https://EXAMPLE.com/pasta#recipe'
        response = self.import_recipe(data)
        self.assertEqual(len(response.get_json()['duplicates']), 1)
        values = response.get_json()['values']
        values['tags'] = '|'.join(values['tags'])
        response = self.client.post('/recipes/new', data=values)
        self.assertIn(b'Save this recipe anyway', response.data)
        self.assertEqual(Recipe.query.count(), 1)
        values['allow_duplicate'] = 'yes'
        self.assertEqual(self.client.post('/recipes/new', data=values).status_code, 302)
        self.assertEqual(Recipe.query.count(), 2)

    def test_legacy_recipe_remains_readable_and_editable(self):
        recipe = Recipe(name='Old recipe', ingredients='Sauce:|1 tomato|Pasta:|100 g pasta',
                        directions='First line\nSecond line', url='https://example.com/old')
        db.session.add(recipe)
        db.session.commit()
        response = self.client.get(f'/recipe/{recipe.id}')
        self.assertIn(b'<li>1 tomato</li>', response.data)
        response = self.client.get(f'/recipe/{recipe.id}/update')
        self.assertIn(b'Sauce:\n1 tomato\nPasta:\n100 g pasta', response.data)
        self.assertIn(b'First line\nSecond line', response.data)

    def test_unnamed_groups_round_trip(self):
        groups = [{'name': 'Sauce', 'ingredients': ['Tomato']}, {'name': '', 'ingredients': ['Pasta']}]
        self.assertEqual(parse_ingredients(ingredients_text(groups)), groups)

    def test_import_and_save_require_csrf(self):
        self.app.config['WTF_CSRF_ENABLED'] = True
        self.assertEqual(self.import_recipe(EXAMPLE).status_code, 400)
        self.client.post('/recipes/new', data={'name': 'Recipe', 'ingredients': 'Food', 'directions': 'Cook'})
        self.assertEqual(Recipe.query.count(), 0)

    def test_additive_migration_preserves_legacy_data_and_is_repeatable(self):
        db.session.remove()
        db.drop_all()
        with db.engine.begin() as connection:
            connection.execute(text('CREATE TABLE recipe (id INTEGER PRIMARY KEY, name VARCHAR(30) NOT NULL, description TEXT, image_file VARCHAR(30), ingredients TEXT NOT NULL, directions TEXT NOT NULL, source VARCHAR(20), url TEXT, notes TEXT)'))
            connection.execute(text("INSERT INTO recipe (id, name, ingredients, directions, url) VALUES (1, 'Legacy', 'a|b', 'Mix', 'https://example.com')"))
        update_db()
        update_db()
        recipe = Recipe.query.get(1)
        self.assertEqual(recipe.ingredients, 'a|b')
        self.assertEqual(recipe.url, 'https://example.com')
        self.assertIsNone(recipe.ingredient_groups)
        self.assertIsNone(recipe.prep_time_minutes)

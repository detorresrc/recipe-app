from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from core.models import (
    Recipe,
    Tag,
    Ingredient
)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer
)

RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """ Create and return a recipe detail URL. """
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    """ Create and return a sample recipe """
    defaults = {
        'title': 'Sample recipe title',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'Sample description',
        'link': 'http://example.com/recipe.pdf'
    }

    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


class PublicRecipeAPITests(TestCase):
    """ Test unauthenticated API requests. """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """ Test auth is required to call API. """
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


def create_user(**params):
    """ Create and return a new user. """
    return get_user_model().objects.create_user(**params)


class PrivateRecipeAPITests(TestCase):
    """ Test authenticated API requests. """

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """ Test retrieving list of recipes. """
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """ Test list of recipes is limited to authenticated user. """
        other_user = create_user(
            email='other@example.com',
            password='testpass123'
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        payload = {
            'title': 'Sample recipe',
            'time_minutes': 30,
            'price': Decimal('5.99')
        }

        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """ Test updating a recipe with patch. """
        original_link = "https://google.com"
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link=original_link
        )

        payload = {'title': 'New recipe title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """ Test full update of the recipe. """
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link='https://google.com',
            description='Sample recipe description'
        )

        payload = {
            'title': 'New recipe title',
            'link': 'https://example.com',
            'description': 'New recipe description',
            'time_minutes': 10,
            'price': Decimal('2.50')
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """ Test that updating user field returns error. """
        new_user = create_user(
            email="other@gmail.com", password="password123321")
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id, 'title': 'New title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        recipe.refresh_from_db()

        self.assertEqual(recipe.user, self.user)
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_delete_recipe(self):
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        exists = Recipe.objects.filter(id=recipe.id).exists()
        self.assertFalse(exists)

    def test_delete_other_users_recipe_error(self):
        """ Test trying to delete another users recipe gives error """
        new_user = create_user(email="other@gmail.com",
                               password="password123123")
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        exists = Recipe.objects.filter(id=recipe.id).exists()
        self.assertTrue(exists)

    def test_create_recipe_with_new_tags(self):
        """ Test creating a recipe with new tags. """
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'tags': [
                {'name': 'Thai'},
                {'name': 'Dinner'}
            ]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(name=tag['name']).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """ Test creating a recipe with existing tags. """
        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'Pongal',
            'time_minutes': 60,
            'price': Decimal('4.50'),
            'tags': [
                {'name': 'Indian'},
                {'name': 'Dinner'}
            ]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipe.count(), 1)
        recipe = recipe[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(name=tag['name']).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """ Test creating tag when updating a recipe. """
        recipe = create_recipe(user=self.user)
        payload = {
            'tags': [
                {'name': 'Lunch'}
            ]
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tags(self):
        """ Test assigning an existing tag when updating a recipe. """
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_Recipe_tags(self):
        """ Test clearing a recipes tags. """
        tag = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """Test creating recipe with new ingredients"""
        payload = {
            'title': 'Cauliflower Tacos',
            'time_minutes': 60,
            'price': Decimal('4.30'),
            'ingredients': [
                {'name': 'Cauliflower'},
                {'name': 'Salt'}
            ]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name']).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredients(self):
        """Test creating a new recipe with existing ingredients."""
        ingredient = Ingredient.objects.create(
            user=self.user, name='Cauliflower')
        payload = {
            'title': 'Cauliflower Tacos',
            'time_minutes': 60,
            'price': Decimal('4.30'),
            'ingredients': [
                {'name': 'Cauliflower'},
                {'name': 'Salt'}
            ]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertIsNotNone(recipes)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]

        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name']).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """Test creating an ingredient when updating a recipe"""
        recipe = create_recipe(user=self.user)

        payload = {
            'ingredients': [
                {'name': 'Limes'}
            ]
        }
        res = self.client.patch(detail_url(recipe.id), payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertIsNotNone(recipes)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 1)
        self.assertEqual(recipe.ingredients.first().name, 'Limes')

    def test_add_existing_ingredient_on_update(self):
        """Test updating ingredient when updating a recipe"""
        ingredient = Ingredient.objects.create(user=self.user, name='Limes')

        recipe = create_recipe(user=self.user)
        payload = {
            'ingredients': [
                {'name': 'Limes'},
                {'name': 'Papaya'}
            ]
        }
        res = self.client.patch(detail_url(recipe.id), payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertIsNotNone(recipes)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)

        self.assertIn(ingredient, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name']).exists()
            self.assertTrue(exists)

    def test_clear_recipe_ingredients_on_update(self):
        """Test clearing ingredients on update"""
        recipe = create_recipe(user=self.user)
        payload = {
            'ingredients': [
                {'name': 'Limes'}
            ]
        }
        res = self.client.patch(detail_url(recipe.id), payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.ingredients.count(), 1)

        payload = {
            'ingredients': []
        }
        res = self.client.patch(detail_url(recipe.id), payload, format='json')
        recipe.refresh_from_db()
        self.assertEqual(recipe.ingredients.count(), 0)

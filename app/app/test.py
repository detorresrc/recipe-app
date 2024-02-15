from django.test import SimpleTestCase

from app import calc


class CalcTest(SimpleTestCase):

    def test_add(self):
        result = calc.add(1, 2)
        self.assertEqual(result, 3)

        result = calc.add(11, 22)
        self.assertEqual(result, 33)

    def test_sub(self):
        result = calc.sub(2, 1)
        self.assertEqual(result, 1)

        result = calc.sub(10, 5)
        self.assertEqual(result, 5)

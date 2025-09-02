import unittest
from ai_code import multiply_numbers, subtract_numbers
from helper import divide_numbers

class TestMathFunctions(unittest.TestCase):

    def test_multiply_numbers(self):
        self.assertEqual(multiply_numbers(3, 4), 12)
        self.assertEqual(multiply_numbers(-1, 5), -5)

    def test_subtract_numbers(self):
        self.assertEqual(subtract_numbers(10, 5), 5)
        self.assertEqual(subtract_numbers(5, 10), -5)

    def test_divide_numbers(self):
        self.assertEqual(divide_numbers(10, 2), 5)
        with self.assertRaises(ValueError):  # Test for zero division
            divide_numbers(10, 0)

if __name__ == '__main__':
    unittest.main()

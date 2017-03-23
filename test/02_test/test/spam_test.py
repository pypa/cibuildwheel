from unittest import TestCase
import spam


class TestSpam(TestCase):
    def test_system(self):
        self.assertEqual(0, spam.system('python -c "exit(0)"'))
        self.assertNotEqual(0, spam.system('python -c "exit(1)"'))

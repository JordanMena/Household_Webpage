from unittest import TestCase
import random
from home_page.users.utils import iter_pages


class TestIter_pages(TestCase):
    def test_iter_pages(self):
        expected = [1, 2, 3, None, 44, 45, 46, None, 98, 99, 100]
        page_list = iter_pages(45, 100, left_edge=3, right_edge=3, left_current=1, right_current=1)
        assert page_list == expected

    def test_iter_pages_short_list(self):
        left = random.randint(1, 10)
        right = random.randint(1, 10)
        # left
        num_pages = random.randint(1, left+right-1)
        current_page = random.randint(1, num_pages)
        page_list = iter_pages(current_page, num_pages, left_edge=left, right_edge=right)
        ans = [i for i in range(1, num_pages+1)]
        print(page_list)
        print(ans)
        assert page_list == ans

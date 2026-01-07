from django.test import TestCase
from webscraper.models import Dataset
from webscraper.tasks import search_datasets
from webscraper.utils.search.scoring import (
    calculate_text_similarity_score,
    calculate_search_score,
)


class TextSimilarityScoreTests(TestCase):
    def test_exact_match_returns_highest_score(self):
        score_exact = calculate_text_similarity_score("machine learning", "machine learning")
        score_case_diff = calculate_text_similarity_score("Machine Learning", "machine learning")
        score_substring = calculate_text_similarity_score("machine", "machine learning")

        self.assertEqual(score_exact, score_case_diff)
        self.assertGreater(score_exact, score_substring)

    def test_substring_match_scores_by_position(self):
        score_start = calculate_text_similarity_score("machine", "machine learning dataset")
        score_end = calculate_text_similarity_score("dataset", "machine learning dataset")

        self.assertGreater(score_start, score_end)

    def test_multiple_occurrences_increase_score(self):
        score_single = calculate_text_similarity_score("data", "data science")
        score_multiple = calculate_text_similarity_score("data", "data science data analysis")
        self.assertGreater(score_multiple, score_single)

    def test_partial_character_matches(self):
        score_partial = calculate_text_similarity_score("ml", "machine learning")
        score_substring = calculate_text_similarity_score("machine", "machine learning")

        self.assertGreater(score_partial, 0)
        self.assertGreater(score_substring, score_partial)

    def test_edge_cases_return_zero(self):
        self.assertEqual(calculate_text_similarity_score("xyz", "machine learning"), 0)
        self.assertEqual(calculate_text_similarity_score("", "machine learning"), 0)
        self.assertEqual(calculate_text_similarity_score("machine", ""), 0)


class SearchScoreTests(TestCase):
    def test_empty_query_returns_zero(self):
        score = calculate_search_score("", "Title", "Description")
        self.assertEqual(score, 0.0)

    def test_title_weighted_higher_than_description(self):
        score_title = calculate_search_score("machine", "machine learning", "other text")
        score_desc = calculate_search_score("machine", "other text", "machine learning")
        self.assertGreater(score_title, score_desc)

    def test_matching_both_fields_scores_highest(self):
        score_title_only = calculate_search_score("machine", "machine learning", "unrelated")
        score_desc_only = calculate_search_score("machine", "unrelated", "machine learning")
        score_both = calculate_search_score("machine", "machine learning", "machine learning")

        self.assertGreater(score_both, score_title_only)
        self.assertGreater(score_both, score_desc_only)

    def test_score_rounded_to_two_decimals(self):
        score = calculate_search_score("test", "test dataset", "test description")
        self.assertIsInstance(score, float)
        self.assertEqual(score, round(score, 2))


class SearchDatabaseTests(TestCase):
    def setUp(self):
        Dataset.objects.create(
            title="Machine Learning Dataset",
            description="A comprehensive dataset for machine learning"
        )
        Dataset.objects.create(
            title="Deep Learning Models",
            description="Collection of deep learning models"
        )
        Dataset.objects.create(
            title="Natural Language Processing",
            description="NLP dataset with machine learning examples"
        )
        Dataset.objects.create(
            title="Computer Vision",
            description="Image dataset for computer vision tasks"
        )

    def test_search_filters_and_returns_matches(self):
        result = search_datasets("machine learning")
        results = result["results"]
        titles = [r["title"] for r in results]

        self.assertGreater(len(results), 0)
        self.assertIn("Machine Learning Dataset", titles)
        self.assertIn("Natural Language Processing", titles)

    def test_search_case_insensitive(self):
        results_lower = search_datasets("machine learning")["results"]
        results_upper = search_datasets("MACHINE LEARNING")["results"]
        self.assertEqual(len(results_lower), len(results_upper))

    def test_results_sorted_by_score_descending(self):
        results = search_datasets("machine")["results"]
        self.assertGreater(len(results), 1)

        for i in range(len(results) - 1):
            current_score = calculate_search_score(
                "machine",
                results[i]["title"],
                results[i]["description"]
            )
            next_score = calculate_search_score(
                "machine",
                results[i + 1]["title"],
                results[i + 1]["description"]
            )
            self.assertGreaterEqual(current_score, next_score)

    def test_score_excluded_from_results(self):
        results = search_datasets("machine")["results"]
        for result in results:
            self.assertNotIn("score", result)
            self.assertIn("id", result)
            self.assertIn("title", result)
            self.assertIn("description", result)

    def test_no_results_for_nonexistent_query(self):
        results = search_datasets("nonexistent query xyz")["results"]
        self.assertEqual(len(results), 0)

    def test_partial_word_matching(self):
        results = search_datasets("learn")["results"]
        self.assertGreater(len(results), 0)


class SearchIntegrationTests(TestCase):
    def setUp(self):
        Dataset.objects.create(
            title="Python Machine Learning",
            description="Learn machine learning with Python"
        )
        Dataset.objects.create(
            title="JavaScript Basics",
            description="Introduction to JavaScript programming"
        )
        Dataset.objects.create(
            title="Data Science with Python",
            description="Python for data science and machine learning"
        )

    def test_exact_title_match_ranks_highest(self):
        result = search_datasets("Python Machine Learning")
        self.assertGreater(len(result["results"]), 0)
        self.assertEqual(result["results"][0]["title"], "Python Machine Learning")

    def test_search_across_title_and_description(self):
        result = search_datasets("Python")
        self.assertGreaterEqual(len(result["results"]), 2)

        titles = [r["title"] for r in result["results"]]
        self.assertIn("Python Machine Learning", titles)
        self.assertIn("Data Science with Python", titles)

    def test_independent_search_results(self):
        result_python = search_datasets("Python")
        result_js = search_datasets("JavaScript")

        self.assertNotEqual(result_python["results"], result_js["results"])
        self.assertNotEqual(len(result_python["results"]), len(result_js["results"]))

from django.test import TestCase
from webscraper.models import Dataset
from webscraper.tasks import search_datasets, _perform_search_with_scoring
from webscraper.utils.search.scoring import (
    calculate_text_similarity_score,
    calculate_search_score,
    _calculate_exact_match_score,
    _calculate_substring_match_score,
    _calculate_partial_match_score,
    _find_partial_matches
)


class TextSimilarityScoreTests(TestCase):
    def test_exact_match(self):
        score = calculate_text_similarity_score("machine learning", "machine learning")
        expected_score = _calculate_exact_match_score(len("machine learning"))
        self.assertEqual(score, expected_score)

    def test_exact_match_case_insensitive(self):
        score = calculate_text_similarity_score("Machine Learning", "machine learning")
        expected_score = _calculate_exact_match_score(len("Machine Learning"))
        self.assertEqual(score, expected_score)

    def test_substring_match_at_start(self):
        score = calculate_text_similarity_score("machine", "machine learning dataset")
        self.assertGreater(score, 0)

    def test_substring_match_at_end(self):
        score = calculate_text_similarity_score("dataset", "machine learning dataset")
        self.assertGreater(score, 0)

    def test_substring_match_in_middle(self):
        score = calculate_text_similarity_score("learning", "machine learning dataset")
        self.assertGreater(score, 0)

    def test_multiple_occurrences(self):
        score_single = calculate_text_similarity_score("data", "data science")
        score_multiple = calculate_text_similarity_score("data", "data science data")
        self.assertGreater(score_multiple, score_single)

    def test_partial_match(self):
        score = calculate_text_similarity_score("ml", "machine learning")
        self.assertGreater(score, 0)

    def test_no_match(self):
        score = calculate_text_similarity_score("xyz", "machine learning")
        self.assertEqual(score, 0)

    def test_empty_query(self):
        score = calculate_text_similarity_score("", "machine learning")
        self.assertEqual(score, 0)

    def test_empty_text(self):
        score = calculate_text_similarity_score("machine", "")
        self.assertEqual(score, 0)

    def test_both_empty(self):
        score = calculate_text_similarity_score("", "")
        self.assertEqual(score, 0)


class PartialMatchTests(TestCase):
    def test_find_partial_matches_all_chars_present(self):
        match_count, positions = _find_partial_matches("ml", "machine learning")
        self.assertEqual(match_count, 2)
        self.assertEqual(len(positions), 2)

    def test_find_partial_matches_sequential(self):
        match_count, positions = _find_partial_matches("mac", "machine")
        self.assertEqual(match_count, 3)

    def test_find_partial_matches_no_match(self):
        match_count, positions = _find_partial_matches("xyz", "machine learning")
        self.assertEqual(match_count, 0)
        self.assertEqual(len(positions), 0)

    def test_partial_match_score_no_matches(self):
        score = _calculate_partial_match_score(0, [], 3)
        self.assertEqual(score, 0)

    def test_partial_match_score_with_positions(self):
        score = _calculate_partial_match_score(3, [0, 1, 5], 3)
        self.assertGreater(score, 0)


class SearchScoreTests(TestCase):
    def test_search_score_empty_query(self):
        score = calculate_search_score("", "Title", "Description")
        self.assertEqual(score, 0.0)

    def test_search_score_title_match(self):
        score = calculate_search_score("machine", "machine learning", "")
        self.assertGreater(score, 0)

    def test_search_score_description_match(self):
        score = calculate_search_score("machine", "", "machine learning dataset")
        self.assertGreater(score, 0)

    def test_search_score_both_match(self):
        score_title = calculate_search_score("machine", "machine learning", "")
        score_desc = calculate_search_score("machine", "", "machine learning")
        score_both = calculate_search_score("machine", "machine learning", "machine learning")
        self.assertGreater(score_both, score_title)
        self.assertGreater(score_both, score_desc)

    def test_search_score_title_weighted_higher(self):
        score_title = calculate_search_score("machine", "machine learning", "")
        score_desc = calculate_search_score("machine", "", "machine learning")
        self.assertGreater(score_title, score_desc)

    def test_search_score_returns_rounded_float(self):
        score = calculate_search_score("test", "test dataset", "test description")
        self.assertIsInstance(score, float)
        self.assertEqual(score, round(score, 2))


class PerformSearchWithScoringTests(TestCase):
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

    def test_search_returns_matching_results(self):
        results = _perform_search_with_scoring("machine learning")
        self.assertGreater(len(results), 0)

    def test_search_filters_by_title(self):
        results = _perform_search_with_scoring("Machine Learning")
        titles = [r["title"] for r in results]
        self.assertIn("Machine Learning Dataset", titles)

    def test_search_filters_by_description(self):
        results = _perform_search_with_scoring("machine learning")
        titles = [r["title"] for r in results]
        self.assertIn("Natural Language Processing", titles)

    def test_search_case_insensitive(self):
        results_lower = _perform_search_with_scoring("machine learning")
        results_upper = _perform_search_with_scoring("MACHINE LEARNING")
        self.assertEqual(len(results_lower), len(results_upper))

    def test_search_returns_sorted_by_score(self):
        results = _perform_search_with_scoring("machine")

        if len(results) > 1:
            for i in range(len(results) - 1):
                title_score_current = calculate_search_score(
                    "machine",
                    results[i]["title"],
                    results[i]["description"]
                )
                title_score_next = calculate_search_score(
                    "machine",
                    results[i + 1]["title"],
                    results[i + 1]["description"]
                )
                self.assertGreaterEqual(title_score_current, title_score_next)

    def test_search_excludes_score_from_results(self):
        results = _perform_search_with_scoring("machine")
        for result in results:
            self.assertNotIn("score", result)

    def test_search_includes_required_fields(self):
        results = _perform_search_with_scoring("machine")
        for result in results:
            self.assertIn("id", result)
            self.assertIn("title", result)
            self.assertIn("description", result)

    def test_search_no_results(self):
        results = _perform_search_with_scoring("nonexistent query xyz")
        self.assertEqual(len(results), 0)

    def test_search_partial_word_match(self):
        results = _perform_search_with_scoring("learn")
        self.assertGreater(len(results), 0)


class SearchDatasetsTaskTests(TestCase):
    def setUp(self):
        Dataset.objects.create(
            title="Machine Learning Dataset",
            description="A comprehensive dataset for machine learning"
        )
        Dataset.objects.create(
            title="Deep Learning Models",
            description="Collection of deep learning models"
        )

    def test_search_datasets_returns_dict(self):
        result = search_datasets("machine learning")
        self.assertIsInstance(result, dict)

    def test_search_datasets_has_results_field(self):
        result = search_datasets("machine learning")
        self.assertIn("results", result)
        self.assertIsInstance(result["results"], list)

    def test_search_datasets_with_matches(self):
        result = search_datasets("machine")
        self.assertGreater(len(result["results"]), 0)

    def test_search_datasets_no_matches(self):
        result = search_datasets("nonexistent xyz query")
        self.assertEqual(len(result["results"]), 0)

    def test_search_datasets_results_structure(self):
        result = search_datasets("machine")
        if len(result["results"]) > 0:
            first_result = result["results"][0]
            self.assertIn("id", first_result)
            self.assertIn("title", first_result)
            self.assertIn("description", first_result)
            self.assertNotIn("score", first_result)

    def test_search_datasets_returns_sorted_results(self):
        result = search_datasets("learning")

        if len(result["results"]) > 1:
            for i in range(len(result["results"]) - 1):
                current_score = calculate_search_score(
                    "learning",
                    result["results"][i]["title"],
                    result["results"][i]["description"]
                )
                next_score = calculate_search_score(
                    "learning",
                    result["results"][i + 1]["title"],
                    result["results"][i + 1]["description"]
                )
                self.assertGreaterEqual(current_score, next_score)


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

    def test_search_ranks_exact_title_match_highest(self):
        result = search_datasets("Python Machine Learning")
        self.assertGreater(len(result["results"]), 0)
        self.assertEqual(result["results"][0]["title"], "Python Machine Learning")

    def test_search_finds_results_in_title_and_description(self):
        result = search_datasets("Python")
        self.assertGreaterEqual(len(result["results"]), 2)
        titles = [r["title"] for r in result["results"]]
        self.assertIn("Python Machine Learning", titles)
        self.assertIn("Data Science with Python", titles)

    def test_search_filters_unrelated_results(self):
        result = search_datasets("Python")
        titles = [r["title"] for r in result["results"]]
        self.assertNotIn("JavaScript Basics", titles)

    def test_multiple_searches_independent(self):
        result1 = search_datasets("Python")
        result2 = search_datasets("JavaScript")

        self.assertNotEqual(len(result1["results"]), len(result2["results"]))
        self.assertNotEqual(result1["results"], result2["results"])

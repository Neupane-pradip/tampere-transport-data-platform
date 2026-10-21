import unittest
from unittest.mock import Mock, call, patch

import requests

from main import fetch_departures


class TestFetchDepartures(unittest.TestCase):
    def setUp(self):
        # Small fake response: no real API key or network needed.
        self.payload = {
            "data": {
                "stop": {
                    "gtfsId": "tampere:0835",
                    "name": "Hervannan kampus A",
                    "stoptimesWithoutPatterns": [],
                }
            }
        }

    def successful_response(self):
        response = Mock()
        response.json.return_value = self.payload
        return response

    @patch("main.time.sleep")
    @patch("main.requests.post")
    def test_timeout_then_success(self, post, sleep):
        # First request times out; the second succeeds.
        post.side_effect = [
            requests.exceptions.Timeout(),
            self.successful_response(),
        ]

        result = fetch_departures("test-key")

        self.assertEqual(result, self.payload)
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(2)

    @patch("main.time.sleep")
    @patch("main.requests.post")
    def test_stops_after_three_connection_failures(self, post, sleep):
        post.side_effect = requests.exceptions.ConnectionError()

        with self.assertRaisesRegex(RuntimeError, "after 3 attempts"):
            fetch_departures("test-key")

        self.assertEqual(post.call_count, 3)
        self.assertEqual(sleep.call_args_list, [call(2), call(4)])

    @patch("main.time.sleep")
    @patch("main.requests.post")
    def test_server_error_then_success(self, post, sleep):
        failed_response = Mock()
        failed_response.status_code = 503
        failed_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError(response=failed_response)
        )

        post.side_effect = [
            failed_response,
            self.successful_response(),
        ]

        self.assertEqual(fetch_departures("test-key"), self.payload)
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(2)

    @patch("main.time.sleep")
    @patch("main.requests.post")
    def test_authentication_and_rate_limit_errors_are_not_retried(
        self, post, sleep
    ):
        for status_code in (401, 403, 429):
            with self.subTest(status_code=status_code):
                post.reset_mock()
                sleep.reset_mock()

                response = Mock()
                response.status_code = status_code
                response.raise_for_status.side_effect = (
                    requests.exceptions.HTTPError(response=response)
                )
                post.return_value = response

                with self.assertRaises(requests.exceptions.HTTPError):
                    fetch_departures("test-key")

                post.assert_called_once()
                sleep.assert_not_called()

    @patch("main.time.sleep")
    @patch("main.requests.post")
    def test_graphql_errors_are_not_retried(self, post, sleep):
        response = Mock()
        response.json.return_value = {
            "errors": [{"message": "Invalid query"}]
        }
        post.return_value = response

        with self.assertRaisesRegex(RuntimeError, "GraphQL"):
            fetch_departures("test-key")

        post.assert_called_once()
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
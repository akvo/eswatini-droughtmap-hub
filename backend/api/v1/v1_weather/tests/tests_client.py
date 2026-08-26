from unittest.mock import MagicMock

from django.test import TestCase

from api.v1.v1_weather.client import Wis2Client, Wis2ClientError
from api.v1.v1_weather.tests.fixtures import MBABANE, MOTI, obs_feature


def mock_response(features):
    response = MagicMock()
    response.json.return_value = {"features": features}
    response.raise_for_status.return_value = None
    return response


class Wis2ClientTests(TestCase):
    def setUp(self):
        self.client_ = Wis2Client("http://wis2.test", "obs-collection")
        self.client_.PAGE_SIZE = 2  # small pages to exercise pagination

    def test_offset_pagination_resends_all_params(self):
        pages = [
            mock_response(
                [
                    obs_feature(feature_id="a"),
                    obs_feature(feature_id="b"),
                ]
            ),
            mock_response([obs_feature(feature_id="c")]),
        ]
        self.client_.session.get = MagicMock(side_effect=pages)
        features = self.client_.fetch_observations(
            "air_temperature", MBABANE
        )
        self.assertEqual(len(features), 3)
        self.assertEqual(self.client_.session.get.call_count, 2)
        for call_index, expected_offset in [(0, 0), (1, 2)]:
            params = self.client_.session.get.call_args_list[
                call_index
            ].kwargs["params"]
            keys = [key for key, _ in params]
            self.assertIn(("offset", expected_offset), params)
            # every page resends the property filters (next-link gotcha)
            self.assertIn(("name", "air_temperature"), params)
            self.assertIn(("wigos_station_identifier", MBABANE), params)
            # name MUST precede wigos_station_identifier (order gotcha)
            self.assertLess(
                keys.index("name"), keys.index("wigos_station_identifier")
            )

    def test_stray_feature_from_ignored_filter_raises(self):
        poisoned = mock_response(
            [obs_feature(wigos_id=MOTI, feature_id="stray")]
        )
        self.client_.session.get = MagicMock(return_value=poisoned)
        with self.assertRaises(Wis2ClientError):
            self.client_.fetch_observations("air_temperature", MBABANE)

    def test_duplicate_feature_ids_are_deduped(self):
        pages = [
            mock_response(
                [
                    obs_feature(feature_id="dup"),
                    obs_feature(feature_id="dup"),
                ]
            ),
            mock_response([]),  # full first page -> client asks for page 2
        ]
        self.client_.session.get = MagicMock(side_effect=pages)
        features = self.client_.fetch_observations(
            "air_temperature", MBABANE
        )
        self.assertEqual(len(features), 1)

    def test_datetime_range_is_sent(self):
        self.client_.session.get = MagicMock(
            return_value=mock_response([])
        )
        self.client_.fetch_observations(
            "air_temperature", MBABANE, start="2026-07-01T00:00:00Z"
        )
        params = self.client_.session.get.call_args.kwargs["params"]
        self.assertIn(("datetime", "2026-07-01T00:00:00Z/.."), params)

    def test_earliest_report_time(self):
        self.client_.session.get = MagicMock(
            return_value=mock_response(
                [obs_feature(end="2026-04-07T00:55:00Z")]
            )
        )
        self.assertEqual(
            self.client_.earliest_report_time(), "2026-04-07T00:55:00Z"
        )

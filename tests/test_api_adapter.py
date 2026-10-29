import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from rapidapi_sync import normalize, team_score, stats_from_entry, parse_fixture, choose_player, totals


class RapidApiSyncTests(unittest.TestCase):
    def test_names_and_teams(self):
        self.assertEqual(normalize("GÖZTEPE"), normalize("Goztepe"))
        self.assertGreaterEqual(team_score("Fenerbahçe", "Fenerbahçe SK"), .9)
        self.assertEqual(normalize("Yabancı"), "yabanci")

    def test_starting_player_stats(self):
        entry = {
            "player": {"id": 123, "name": "Dorgeles Nene"},
            "stats": {
                "minutes": 82, "rating": 7.2,
                "goals": 1, "assists": 0, "yellowCards": 1, "redCards": 0,
            },
        }
        pid, name, metrics = stats_from_entry(entry, "starting")
        self.assertEqual(pid, "123")
        self.assertEqual(name, "Dorgeles Nene")
        self.assertEqual(metrics, [82.0, 1, 1, 7.2, 1.0, 0.0, 1.0, 0.0])

    def test_missing_minutes_never_counts_as_appearance(self):
        entry = {"player":{"id":55,"name":"Unused"},"stats":{"rating":7}}
        self.assertIsNone(stats_from_entry(entry, "bench"))

    def test_aggregation_averages_ratings(self):
        p={"matches":[[80,1,1,7.0,0,0,0,0],[90,1,1,8.0,1,0,0,0]]}
        self.assertEqual(totals(p), [170,2,2,7.5,1,0,0,0])

    def test_fixture_rejects_empty_detail(self):
        with self.assertRaises(RuntimeError):
            parse_fixture({"data":{"id":10,"lineups":{"home":{"starting":[]}}}})

    def test_id_and_unique_name_team_matching(self):
        by_id={"12":{"name":"Dorgeles Nene","teams":{"Fenerbahçe SK"},"matches":[]}}
        self.assertEqual(choose_player("Dorgeles Nene","Fenerbahçe",by_id,""),"12")
        self.assertIsNone(choose_player("Dorgeles Nene","Trabzonspor",by_id,""))


if __name__=="__main__":
    unittest.main()

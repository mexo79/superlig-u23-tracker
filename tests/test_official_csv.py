import pathlib
import sys
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from goal_publish_csv import merge, match_player, club

class OfficialTotalsTests(unittest.TestCase):
    def test_merge_eligible_official_matches(self):
        league={"minutes":80,"games":1,"starts":1,"rating":7.0,"rating_sample":1,
                "goals":0,"assists":1,"yellow":1,"red":0,"null_fields":[]}
        extra={"minutes":70,"games":1,"starts":0,"rating":8.0,"rating_count":1,
               "goals":2,"assists":0,"yellow":0,"red":0,"unknown_fields":[]}
        values=merge({},league,[extra])
        self.assertEqual(values,[150,2,1,7.5,2,1,1,0])

    def test_unknown_stats_are_not_fake_zero(self):
        league={"minutes":80,"games":1,"starts":1,"rating":7.0,"rating_sample":1,
                "goals":0,"assists":0,"yellow":0,"red":0,"null_fields":[]}
        extra={"minutes":70,"games":1,"starts":0,"rating":None,"rating_count":0,
               "goals":0,"assists":0,"yellow":0,"red":0,"unknown_fields":["goals"]}
        values=merge({},league,[extra])
        self.assertEqual(values[0],150)
        self.assertEqual(values[4],"")


    def test_csv_scaled_rating_for_sheet_date_parser(self):
        from goal_apply_csv_to_sheet import numeric
        # 7.12 is exported as integer 712 to avoid IMPORTDATA treating 7.12 as a date.
        self.assertEqual(numeric("712") / 100, 7.12)
        self.assertEqual(numeric("N/A"), "")

    def test_matching_requires_exact_club_when_id_absent(self):
        byid={"123":{"api_id":"123"}}
        byname={("dorgelesnene",club("Fenerbahçe")):[{"api_id":"123"}]}
        self.assertEqual(match_player({"api_id":"123","name":"Dorgeles Nene","club":"Fenerbahçe"},byid,byname)["api_id"],"123")
        self.assertEqual(match_player({"api_id":"","name":"Dorgeles Nene","club":"Fenerbahçe"},byid,byname)["api_id"],"123")
        self.assertIsNone(match_player({"api_id":"","name":"Dorgeles Nene","club":"Galatasaray"},byid,byname))

if __name__=="__main__":
    unittest.main()

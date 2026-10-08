import unittest
from app.cleaning import clean_name, parse_age, clean_record

class TestCleaning(unittest.TestCase):
    
    def test_clean_name(self):
        # Initials and case
        self.assertEqual(clean_name("arun.k"), "arun k")
        self.assertEqual(clean_name("Arun Kumar"), "arun kumar")
        
        # Honorifics
        self.assertEqual(clean_name("Mr. Arun"), "arun")
        self.assertEqual(clean_name("Sri Karthik"), "karthik")
        
        # Tamil Transliteration (testing the flow, actual translit depends on sanscript)
        self.assertTrue(len(clean_name("ரவி")) > 0)
        
    def test_parse_age(self):
        self.assertEqual(parse_age("40"), (40, 40))
        self.assertEqual(parse_age("40-45"), (40, 45))
        self.assertEqual(parse_age("about 40"), (37, 43))
        self.assertEqual(parse_age("40s"), (40, 49))
        self.assertEqual(parse_age("unknown"), (None, None))
        self.assertEqual(parse_age(None), (None, None))
        
    def test_clean_record(self):
        record = {
            "name": "Arun.K",
            "age_raw": "~30",
            "gender": "Male"
        }
        cleaned = clean_record(record)
        self.assertEqual(cleaned["name_cleaned"], "arun k")
        self.assertEqual(cleaned["name_sorted"], "arun k")
        self.assertEqual(cleaned["age_min"], 27)
        self.assertEqual(cleaned["age_max"], 33)
        self.assertEqual(cleaned["gender"], "M")

if __name__ == '__main__':
    unittest.main()

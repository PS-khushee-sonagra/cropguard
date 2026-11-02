import unittest
from unittest.mock import patch
import lang

class TestTranslationSafety(unittest.TestCase):
    def test_number_mismatch_falls_back_to_english(self):
        source = "Spray 2 ml per litre of water."
        # Model returns 20 instead of 2
        with patch.object(lang, "_ask", return_value="प्रति लीटर पानी में 20 मिली का छिड़काव करें।"):
            res = lang.from_english(source, "hi")
        self.assertIn("अनुवाद उपलब्ध नहीं हो सका", res)
        self.assertIn(source, res)

    def test_gujarati_digits_changed_falls_back_to_english(self):
        source = "Spray 2 ml per litre of water."
        # Model returns Gujarati digit ૨૦ (20) instead of 2
        with patch.object(lang, "_ask", return_value="પ્રતિ લિટર પાણીમાં ૨૦ મિલી છાંટો."):
            res = lang.from_english(source, "gu")
        self.assertIn("અનુવાદ ઉપલબ્ધ થઈ શક્યો નથી", res)
        self.assertIn(source, res)

    def test_spray_to_do_not_spray_negation_parity_falls_back(self):
        source = "Spray the leaves in the morning."
        # English is affirmative, translation introduces negative 'मत'
        with patch.object(lang, "_ask", return_value="सुबह पत्तों पर छिड़काव मत करें।"):
            res = lang.from_english(source, "hi")
        self.assertIn("अनुवाद उपलब्ध नहीं हो सका", res)
        self.assertIn(source, res)

    def test_do_not_spray_dropped_negation_falls_back(self):
        source = "Do not spray the affected flowers."
        # English has negation 'not', translation is affirmative
        with patch.object(lang, "_ask", return_value="प्रभावित फूलों पर छिड़काव करें।"):
            res = lang.from_english(source, "hi")
        self.assertIn("अनुवाद उपलब्ध नहीं हो सका", res)
        self.assertIn(source, res)

    def test_dropped_warning_sentence_falls_back(self):
        source = "Early blight observed on leaves. Remove affected foliage immediately. Monitor weather."
        # Model drops sentences and only returns one short phrase
        with patch.object(lang, "_ask", return_value="पत्तियों पर अगेती झुलसा देखा गया।"):
            res = lang.from_english(source, "hi")
        self.assertIn("अनुवाद उपलब्ध नहीं हो सका", res)
        self.assertIn(source, res)

    def test_truncated_output_falls_back(self):
        source = "Early blight symptoms on tomato require careful monitoring of humidity and temperature. Contact your extension agent."
        # Truncated output (under 0.4x length)
        with patch.object(lang, "_ask", return_value="अगेती झुलसा।"):
            res = lang.from_english(source, "hi")
        self.assertIn("अनुवाद उपलब्ध नहीं हो सका", res)
        self.assertIn(source, res)

    def test_gujarati_output_for_hindi_request_falls_back(self):
        source = "Water the roots deeply."
        # Gujarati script returned for a Hindi request
        with patch.object(lang, "_ask", return_value="મૂળમાં ઊંડે સુધી પાણી આપો."):
            res = lang.from_english(source, "hi")
        self.assertIn("अनुवाद उपलब्ध नहीं हो सका", res)
        self.assertIn(source, res)

    def test_empty_output_falls_back(self):
        source = "Water the roots deeply."
        with patch.object(lang, "_ask", return_value=""):
            res = lang.from_english(source, "hi")
        self.assertIn("अनुवाद उपलब्ध नहीं हो सका", res)
        self.assertIn(source, res)

    def test_withheld_reply_uses_fixed_phrasebook_never_calls_model(self):
        source = "No verified entry. Contact your KVK."
        # Even if a malicious or hallucinating model wants to say "spray in the field"
        with patch.object(lang, "_ask", return_value="खेत में दवा का छिड़काव करें") as mock_ask:
            res_hi = lang.from_english(source, "hi")
            res_gu = lang.from_english(source, "gu")
        mock_ask.assert_not_called()
        self.assertIn("कोई सत्यापित प्रविष्टि नहीं। अपने KVK से संपर्क करें।", res_hi)
        self.assertIn("કોઈ ચકાસાયેલ નોંધ નથી. તમારા KVK નો સંપર્ક કરો.", res_gu)
        self.assertNotIn("छिड़काव करें", res_hi)

    def test_good_translation_with_allowed_latin_accepted(self):
        source = "Early blight noticed. Spray 2 ml per litre. Contact KVK if needed."
        # Translation includes allowed terms: Early blight, ml, KVK
        good_hindi = "अगेती झुलसा (Early blight) देखा गया। प्रति लीटर 2 ml छिड़कें। यदि आवश्यक हो तो KVK से संपर्क करें।"
        with patch.object(lang, "_ask", return_value=good_hindi):
            res = lang.from_english(source, "hi")
        self.assertNotIn("अनुवाद उपलब्ध नहीं हो सका", res)
        self.assertIn("अगेती झुलसा", res)
        self.assertIn("2 ml", res)

if __name__ == "__main__":
    unittest.main()


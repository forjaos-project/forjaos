#!/usr/bin/env python3
"""Unit checks for Piper phoneme alignment and viseme mapping."""

from types import SimpleNamespace
import unittest

from worker import viseme_events, viseme_for


class VisemeTests(unittest.TestCase):
    def test_portuguese_phonemes_cover_fifteen_mouth_shapes(self):
        phonemes = {
            "closed": "m",
            "labiodental": "f",
            "alveolar": "s",
            "velar": "k",
            "postalveolar": "ʃ",
            "nasal": "ɲ",
            "lateral": "ʎ",
            "rhotic": "ʁ",
            "open": "a",
            "mid": "ɛ",
            "wide": "i",
            "round": "ɔ",
            "narrow": "u",
            "glide": "j",
            "rest": "?",
        }
        self.assertEqual({viseme_for(phoneme) for phoneme in phonemes.values()}, set(phonemes))

    def test_alignment_offsets_use_sample_durations(self):
        alignments = [
            SimpleNamespace(phoneme="a", num_samples=1600),
            SimpleNamespace(phoneme="m", num_samples=800),
        ]
        events = viseme_events(alignments, sample_rate=16_000, sample_count=2_400)
        self.assertEqual(events[0]["start_ms"], 0)
        self.assertEqual(events[0]["end_ms"], 100)
        self.assertEqual(events[1]["start_ms"], 100)
        self.assertEqual(events[1]["end_ms"], 150)


if __name__ == "__main__":
    unittest.main()

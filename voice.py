
import openai
import os
from dotenv import load_dotenv
import re
from openai import OpenAI
from fuzzywuzzy import fuzz, process
import jellyfish  # For phonetic matching
from thefuzz import fuzz as thefuzz  # Additional fuzzy matching library
import numpy as np

class Voicee:
    def __init__(self):
        # Set up OpenAI client
        load_dotenv("/Users/swagatbhowmik/CS projects/CodeJam2024/bill_parser/.env")
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=openai.api_key)

    def normalize_name(self, name):
        """
        Normalizes a name by removing special characters and converting to lowercase.
        """
        return re.sub(r'[^a-zA-Z]', '', name).lower()

    def is_name_match(self, name1, name2, threshold=65):
        """
        Determines if two names match using multiple string similarity metrics.
        
        Args:
            name1 (str): First name to compare
            name2 (str): Second name to compare
            threshold (int): Minimum similarity score (0-100) to consider a match
            
        Returns:
            bool: True if names match according to any metric
        """
        # Normalize both names
        name1_norm = self.normalize_name(name1)
        name2_norm = self.normalize_name(name2)
        
        # Direct matching
        if name1_norm == name2_norm:
            return True
            
        # Calculate various similarity scores
        levenshtein_ratio = thefuzz.ratio(name1_norm, name2_norm)
        partial_ratio = thefuzz.partial_ratio(name1_norm, name2_norm)
        phonetic_match = jellyfish.soundex(name1_norm) == jellyfish.soundex(name2_norm)
        metaphone_match = jellyfish.metaphone(name1_norm) == jellyfish.metaphone(name2_norm)
        
        # Custom scoring for similar-sounding names
        jaro_winkler = jellyfish.jaro_winkler_similarity(name1_norm, name2_norm) * 100
        
        # Return True if any similarity metric exceeds the threshold
        return (levenshtein_ratio >= threshold or 
                partial_ratio >= threshold or 
                jaro_winkler >= threshold or 
                phonetic_match or 
                metaphone_match)

    def find_best_match(self, word, valid_names):
        """
        Finds the best matching name from the valid names list.
        
        Args:
            word (str): Word to match
            valid_names (list): List of valid names to match against
            
        Returns:
            tuple: (matched_name, confidence_score) or (None, 0) if no match found
        """
        best_match = None
        best_score = 0
        
        for valid_name in valid_names:
            # Calculate multiple similarity scores
            levenshtein_score = thefuzz.ratio(word.lower(), valid_name.lower())
            partial_score = thefuzz.partial_ratio(word.lower(), valid_name.lower())
            jaro_winkler = jellyfish.jaro_winkler_similarity(word.lower(), valid_name.lower()) * 100
            
            # Take the maximum of different similarity metrics
            max_score = max(levenshtein_score, partial_score, jaro_winkler)
            
            # Boost score if phonetic matching
            if (jellyfish.soundex(word) == jellyfish.soundex(valid_name) or 
                jellyfish.metaphone(word) == jellyfish.metaphone(valid_name)):
                max_score += 10
                
            if max_score > best_score:
                best_score = max_score
                best_match = valid_name
                
        return (best_match, best_score) if best_score >= 65 else (None, 0)

    def extract_names(self, sentence, names_list):
        """
        Extracts names from a sentence based on a list of valid names.
        
        Args:
            sentence (str): The sentence containing the names.
            names_list (list): The list of names to check for.
            
        Returns:
            list: A list of names found in the sentence.
        """
        try:
            # First try using GPT-4 for initial name extraction
            completion = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. You will receive a sentence and a list of valid names. "
                                 "Your task is to find which names from the valid names list appear in the sentence, "
                                 "including close matches and possible misspellings. Return ONLY a Python list containing "
                                 "the matching names. If no names match, return an empty list []."
                    },
                    {
                        "role": "user",
                        "content": f"Sentence: {sentence}\nValid names: {names_list}\n"
                                 f"Consider possible misspellings and similar-sounding names."
                    }
                ]
            )

            response = completion.choices[0].message.content.strip()
            
            # Try to find a list pattern in the response
            list_pattern = r'\[(.*?)\]'
            match = re.search(list_pattern, response)
            
            initial_names = []
            if match:
                # Extract the content inside brackets
                list_content = match.group(1)
                if list_content.strip():
                    # Split by comma and clean up each name
                    initial_names = [name.strip().strip('"\'') for name in list_content.split(',')]
                    initial_names = [name for name in initial_names if name]

            # Additional processing for more lenient matching
            found_names = set()  # Use set to avoid duplicates
            
            # Process words from the original sentence
            words = re.findall(r'\b\w+\b', sentence)
            for word in words:
                # Check each word against valid names with lenient matching
                best_match, score = self.find_best_match(word, names_list)
                if best_match:
                    found_names.add(best_match)
            
            # Combine results from GPT and fuzzy matching
            combined_names = set(initial_names) | found_names
            
            # Final verification pass
            verified_names = []
            for found_name in combined_names:
                # Find the closest match in the original names list
                best_match = process.extractOne(found_name, names_list)
                if best_match and best_match[1] >= 65:  # 65% similarity threshold
                    verified_names.append(best_match[0])
            
            return list(set(verified_names))  # Remove any duplicates

        except Exception as e:
            print(f"Error in extract_names: {str(e)}")
            return []

    def transcribe(self, audio_file, names):
        """
        Transcribes audio and extracts matching names.
        
        Args:
            audio_file: The audio file to transcribe
            names (list): List of valid names to check for
            
        Returns:
            list: List of found names
        """
        try:
            transcription = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en",
                response_format="text",
                prompt="The following audio is in English with possible accent variations and name pronunciations."
            )
            print("Transcribed text:", transcription)
            
            # Extract names from the transcribed text
            found_names = self.extract_names(transcription, names)
            return found_names

        except Exception as e:
            print(f"Error in transcribe: {str(e)}")
            return []
